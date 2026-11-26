/*
  esp32_ews.ino — Firmware ESP32 untuk Sistem EWS Gelombang Air
  Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 5.5 Kontrak Data:
  
  Tugas ESP32:
  - Membaca 4 sensor ultrasonik HC-SR04 BERGANTIAN (bukan serentak, hindari crosstalk)
  - Mencatat t_ms (millis()) saat tiap pembacaan sensor SELESAI
  - Membaca debit flowmeter YF-S201 via interrupt
  - Mengirim 1 pesan JSON per siklus via MQTT ke Raspberry Pi
  - Mengirim status "online" (retained) + Last Will "offline"
  
  ESP32 TIDAK menghitung tinggi, fuzzy, maupun kecepatan — semua itu dilakukan di Pi.
  
  Kontrak JSON (satu baris per pesan):
  {"seq":10240,"t_ms":[512000,512030,512060,512090],"us_cm":[32.8,32.9,32.7,32.6],"flow_lpm":8.6}
  
  Pustaka yang dibutuhkan (Install via Arduino IDE Library Manager):
  - PubSubClient by Nick O'Leary (MQTT)
  - ArduinoJson by Benoit Blanchon (JSON)
  - WiFi (bawaan ESP32)
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==========================================
// KONFIGURASI — SESUAIKAN DENGAN SETUP ANDA
// ==========================================

// WiFi (harus jaringan yang sama dengan Raspberry Pi)
const char* WIFI_SSID     = "ZONA KOS WIFI";       // Ganti dengan nama WiFi Anda
const char* WIFI_PASSWORD  = "Naurazonakos";   // Ganti dengan password WiFi Anda

// MQTT Broker (Raspberry Pi)
const char* MQTT_BROKER    = "192.168.110.137";      // Ganti dengan IP Raspberry Pi Anda
const int   MQTT_PORT      = 1883;
const char* MQTT_USER      = "ews";
const char* MQTT_PASSWORD  = "";                   // Kosongkan jika Mosquitto mode allow_anonymous true
const char* MQTT_CLIENT_ID = "esp32-ews";

// Topic MQTT (harus sama dengan config.py di Pi)
const char* TOPIC_TELEMETRY = "ews/wavetank/telemetry";
const char* TOPIC_STATUS    = "ews/wavetank/status";

// ==========================================
// PIN GPIO SENSOR (sesuai PROJECT_SPEC Fase 2)
// ==========================================
// Sensor Ultrasonik HC-SR04 (S1 = pembangkit, S4 = pesisir)
const int TRIG_PINS[4] = {16, 17, 18, 19};  // Output: TRIG S1, S2, S3, S4
const int ECHO_PINS[4] = {34, 35, 32, 33};  // Input:  ECHO S1, S2, S3, S4

// Flowmeter YF-S201
const int FLOW_PIN = 27;

// ==========================================
// PARAMETER PEMBACAAN SENSOR
// ==========================================
// Rentang jarak valid HC-SR04 (cm) — sesuai config.py
const float JARAK_MIN_CM = 2.0;    // Zona buta sensor
const float JARAK_MAKS_CM = 48.0;  // Tinggi pasang sensor dari dasar akuarium

// Jeda antar pembacaan sensor (ms) — mulai 30 ms, naikkan ke 40-50 ms jika crosstalk
const unsigned long JEDA_ANTAR_SENSOR_MS = 30;

// Timeout pulsa echo (mikrodetik) — 48 cm ≈ 2800 µs (pulang-pergi)
const unsigned long ECHO_TIMEOUT_US = 30000;  // 30 ms timeout

// Interval jendela hitung debit flowmeter (ms)
const unsigned long FLOW_WINDOW_MS = 1000;

// Faktor awal flowmeter YF-S201 (dari datasheet: freq / 7.5 = L/min)
const float FLOW_FACTOR = 7.5;

// Interval reconnect WiFi/MQTT (ms)
const unsigned long RECONNECT_INTERVAL_MS = 5000;

// ==========================================
// VARIABEL GLOBAL
// ==========================================
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long seqCounter = 0;
unsigned long lastReconnectAttempt = 0;

// Flowmeter interrupt counter
volatile unsigned long flowPulseCount = 0;
unsigned long lastFlowCalcTime = 0;
float currentFlowLPM = 0.0;

// ==========================================
// INTERRUPT SERVICE ROUTINE — Flowmeter
// ==========================================
void IRAM_ATTR flowPulseISR() {
  flowPulseCount++;
}

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(115200);
  Serial.println("\n==================================================");
  Serial.println("  EWS Gelombang Air — Firmware ESP32 (Sensor Fusion)");
  Serial.println("==================================================");

  // Inisialisasi pin sensor ultrasonik
  for (int i = 0; i < 4; i++) {
    pinMode(TRIG_PINS[i], OUTPUT);
    digitalWrite(TRIG_PINS[i], LOW);
    pinMode(ECHO_PINS[i], INPUT);
  }

  // Inisialisasi pin flowmeter dengan interrupt
  pinMode(FLOW_PIN, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(FLOW_PIN), flowPulseISR, RISING);
  lastFlowCalcTime = millis();

  // Koneksi WiFi
  setupWiFi();

  // Setup MQTT
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(512);  // Buffer cukup untuk JSON payload

  Serial.println("[*] Setup selesai. Memulai loop pembacaan sensor...\n");
}

// ==========================================
// LOOP UTAMA
// ==========================================
void loop() {
  // 1. Pastikan WiFi dan MQTT terhubung
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  // 2. Baca 4 sensor ultrasonik bergantian + catat t_ms per sensor
  float us_cm[4];
  bool us_valid[4];
  unsigned long t_ms[4];

  for (int i = 0; i < 4; i++) {
    // Jeda antar sensor untuk menghindari crosstalk
    if (i > 0) {
      delay(JEDA_ANTAR_SENSOR_MS);
    }

    float jarak = bacaSensorUltrasonik(i);
    t_ms[i] = millis();  // Cap waktu SAAT pembacaan sensor i selesai

    if (jarak >= JARAK_MIN_CM && jarak <= JARAK_MAKS_CM) {
      us_cm[i] = jarak;
      us_valid[i] = true;
    } else {
      us_cm[i] = 0.0;
      us_valid[i] = false;
    }
  }

  // 3. Hitung debit flowmeter (1 kali per jendela 1 detik)
  unsigned long now = millis();
  if (now - lastFlowCalcTime >= FLOW_WINDOW_MS) {
    noInterrupts();
    unsigned long pulses = flowPulseCount;
    flowPulseCount = 0;
    interrupts();

    float freq = (float)pulses * (1000.0 / (float)(now - lastFlowCalcTime));
    currentFlowLPM = freq / FLOW_FACTOR;
    lastFlowCalcTime = now;
  }

  // 4. Susun dan kirim payload JSON sesuai kontrak Bagian 5.5
  if (mqttClient.connected()) {
    kirimPayload(us_cm, us_valid, t_ms, currentFlowLPM);
  }

  // 5. Cetak ke Serial (untuk PLX-DAQ / debugging)
  cetakSerial(us_cm, us_valid, t_ms, currentFlowLPM);

  seqCounter++;

  // Jeda kecil agar total siklus ~200 ms (target >= 5 Hz)
  // Pembacaan 4 sensor ≈ 4 × 30 ms = 120 ms, sisa untuk proses lain
  delay(10);
}

// ==========================================
// FUNGSI BACA SENSOR ULTRASONIK
// ==========================================
float bacaSensorUltrasonik(int idx) {
  int trigPin = TRIG_PINS[idx];
  int echoPin = ECHO_PINS[idx];

  // Kirim pulsa trigger 10 µs
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Baca durasi pulsa echo (mikrodetik)
  unsigned long durasi = pulseIn(echoPin, HIGH, ECHO_TIMEOUT_US);

  if (durasi == 0) {
    // Timeout — sensor gagal baca
    return -1.0;
  }

  // Hitung jarak (cm): kecepatan suara ≈ 0.0343 cm/µs, pulang-pergi / 2
  float jarak = (durasi * 0.0343) / 2.0;
  return jarak;
}

// ==========================================
// FUNGSI KIRIM PAYLOAD MQTT
// ==========================================
void kirimPayload(float us_cm[], bool us_valid[], unsigned long t_ms[], float flow_lpm) {
  // Susun JSON sesuai kontrak:
  // {"seq":N,"t_ms":[t1,t2,t3,t4],"us_cm":[d1,d2,d3,d4],"flow_lpm":F}
  StaticJsonDocument<256> doc;
  doc["seq"] = seqCounter;

  JsonArray arrT = doc.createNestedArray("t_ms");
  JsonArray arrUS = doc.createNestedArray("us_cm");

  for (int i = 0; i < 4; i++) {
    arrT.add(t_ms[i]);
    if (us_valid[i]) {
      arrUS.add(round(us_cm[i] * 100.0) / 100.0);  // 2 desimal
    } else {
      arrUS.add((char*)NULL);  // null di JSON
    }
  }

  doc["flow_lpm"] = round(flow_lpm * 100.0) / 100.0;  // 2 desimal

  // Serialisasi ke buffer dan kirim
  char buffer[256];
  size_t len = serializeJson(doc, buffer, sizeof(buffer));

  bool published = mqttClient.publish(TOPIC_TELEMETRY, buffer);

  if (!published) {
    Serial.println("[!] Gagal mengirim pesan MQTT!");
  }
}

// ==========================================
// FUNGSI CETAK KE SERIAL (PLX-DAQ / Debug)
// ==========================================
void cetakSerial(float us_cm[], bool us_valid[], unsigned long t_ms[], float flow_lpm) {
  Serial.print("[");
  Serial.print(millis());
  Serial.print("] Seq:");
  Serial.print(seqCounter);
  Serial.print(" | ");

  for (int i = 0; i < 4; i++) {
    Serial.print("S");
    Serial.print(i + 1);
    Serial.print("=");
    if (us_valid[i]) {
      Serial.print(us_cm[i], 1);
    } else {
      Serial.print("NULL");
    }
    Serial.print(" ");
  }

  Serial.print("| Flow=");
  Serial.print(flow_lpm, 1);
  Serial.println(" L/m");
}

// ==========================================
// FUNGSI SETUP WIFI
// ==========================================
void setupWiFi() {
  Serial.print("[*] Menghubungkan ke WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" TERHUBUNG!");
    Serial.print("[*] IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println(" GAGAL! Restart ESP32...");
    ESP.restart();
  }
}

// ==========================================
// FUNGSI RECONNECT MQTT
// ==========================================
void reconnectMQTT() {
  unsigned long now = millis();
  if (now - lastReconnectAttempt < RECONNECT_INTERVAL_MS) {
    return;  // Jangan coba terlalu sering
  }
  lastReconnectAttempt = now;

  // Periksa WiFi dulu
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[!] WiFi terputus! Menghubungkan ulang...");
    setupWiFi();
  }

  Serial.print("[*] Menghubungkan ke MQTT Broker ");
  Serial.print(MQTT_BROKER);
  Serial.print("...");

  // Connect dengan Last Will Testament: jika ESP32 mati, broker kirim "offline"
  bool connected = false;
  if (strlen(MQTT_PASSWORD) > 0) {
    connected = mqttClient.connect(
      MQTT_CLIENT_ID,
      MQTT_USER,
      MQTT_PASSWORD,
      TOPIC_STATUS,   // Will Topic
      0,              // Will QoS
      true,           // Will Retain
      "offline"       // Will Message
    );
  } else {
    // Mode tanpa password (allow_anonymous true)
    connected = mqttClient.connect(
      MQTT_CLIENT_ID,
      TOPIC_STATUS,   // Will Topic
      0,              // Will QoS
      true,           // Will Retain
      "offline"       // Will Message
    );
  }

  if (connected) {
    Serial.println(" TERHUBUNG!");
    // Kirim pesan status "online" (retained)
    mqttClient.publish(TOPIC_STATUS, "online", true);
    Serial.println("[*] Status: online (retained)");
  } else {
    Serial.print(" GAGAL (rc=");
    Serial.print(mqttClient.state());
    Serial.println("). Coba lagi dalam 5 detik...");
  }
}
