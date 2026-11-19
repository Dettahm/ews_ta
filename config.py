"""
config.py — Konfigurasi Terpusat Sistem EWS Gelombang Air
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) dan Aturan AI Agent #6 & #17.
Semua konstanta dan angka penting terkunci hanya didefinisikan di sini.
"""

from pathlib import Path

# ==========================================
# 1. PENGATURAN UMUM & SUMBER DATA
# ==========================================
# Sumber data: "sim" (simulator lokal) atau "mqtt" (data nyata dari ESP32)
DATA_SOURCE = "sim"

# Skenario simulator aktif (Bagian 5.3):
# Pilihan: "tenang", "naik_perlahan", "surut_ekstrem", "luapan_ekstrem",
#          "gelombang_lewat", "gelombang_noise", "sensor_error", "kebocoran_pelan"
SIM_SCENARIO = "kebocoran_pelan"

# Interval siklus kerja worker (dalam detik)
WORKER_INTERVAL_S = 0.1  # Loop cepat untuk menangkap event gelombang

# Interval pencatatan reguler ke tabel logs_sensor (1 Hz = 1 baris/detik)
LOG_INTERVAL_S = 1.0

# Batas toleransi data dianggap basi / offline (dalam detik)
STALE_AFTER_S = 5.0

# Interval polling frontend di browser (dalam milidetik)
POLL_INTERVAL_MS = 2000

# Jumlah titik data maksimal untuk grafik deret waktu
HISTORY_MAX_POINTS = 120

# Jumlah titik data maksimal untuk grafik tren kecepatan gelombang
GELOMBANG_MAX_POINTS = 50

# ==========================================
# 2. PENGATURAN DATABASE
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "ews.db"

# ==========================================
# 3. KONSTANTA FISIK & SENSOR FUSION (TERKUNCI K1–K6)
# ==========================================
# Tinggi pemasangan seluruh sensor ultrasonik dari dasar akuarium (K4)
TINGGI_PASANG_CM = 48.0

# Jarak horizontal Sensor 1 (pembangkit) ke Sensor 4 (pesisir) (K6)
JARAK_S1_S4_CM = 75.0

# Ambang batas tinggi minimum untuk mendeteksi puncak gelombang (K3)
AMBANG_PUNCAK_CM = 20.0

# Indeks larik Sensor 4 pada payload sensor us_cm (0: S1, 1: S2, 2: S3, 3: S4) (K1)
INDEKS_S4 = 3

# Jumlah sampel median bergerak untuk penghalusan bacaan S4 di Pi
S4_MEDIAN_N = 3

# Metode agregasi tinggi global maket (K2): "median" atau "rata-rata"
AGREGASI_GLOBAL = "median"

# Syarat minimal sensor ultrasonik yang valid untuk menghitung tinggi global
MIN_SENSOR_VALID = 2

# Rentang fisik valid sensor ultrasonik HC-SR04 (cm)
# Jarak bacaan: 2 cm (zona buta) s/d 48 cm (dasar akuarium saat kosong)
SENSOR_MIN_CM = 2.0
SENSOR_MAX_CM = 48.0

# Rentang debit air valid flowmeter YF-S201 (Liter/menit)
FLOW_MIN_LPM = 0.0
FLOW_MAX_LPM = 30.0

# Parameter deteksi kecepatan gelombang (Bagian 5.5 Aturan 6)
DT_MAKS_S = 3.0       # Jendela pencocokan puncak gelombang maksimum (detik)
V_MIN_CMS = 15.0      # Batas bawah kecepatan gelombang valid (cm/s)
V_MAKS_CMS = 300.0    # Batas atas kecepatan gelombang valid (cm/s)

# Koreksi kalibrasi linear per sensor: y = a * x + b
CAL_A_US = [1.0, 1.0, 1.0, 1.0]  # S1, S2, S3, S4
CAL_B_US = [0.0, 0.0, 0.0, 0.0]

# Kalibrasi debit air
CAL_A_FLOW = 1.0
CAL_B_FLOW = 0.0

# ==========================================
# 4. PARAMETER LOGIKA FUZZY MAMDANI (TERKUNCI K7–K9, FASE 3)
# ==========================================
# Universe of Discourse (Rentang semesta pembicaraan)
HEIGHT_UNIVERSE_MIN = 0.0
HEIGHT_UNIVERSE_MAX = 40.0
HEIGHT_UNIVERSE_STEP = 0.1

FLOW_UNIVERSE_MIN = 0.0
FLOW_UNIVERSE_MAX = 30.0
FLOW_UNIVERSE_STEP = 0.1

DANGER_UNIVERSE_MIN = 0.0
DANGER_UNIVERSE_MAX = 100.0
DANGER_UNIVERSE_STEP = 1.0

# Input 1: Ketinggian S4 (cm) (K8)
# BAHAYA: Double trapezoid (surut ekstrem < 11 cm dan luapan ekstrem > 22 cm)
MF_HEIGHT_S4 = {
    "bahaya_kiri":  [0.0, 0.0, 11.0, 13.0],    # Surut ekstrem
    "aman":         [11.0, 13.0, 17.0, 19.0],  # Sekitar air tenang maket (+/- 15 cm)
    "waspada":      [17.0, 19.5, 22.0],        # Kenaikan air menuju luapan
    "bahaya_kanan": [20.0, 22.0, 40.0, 40.0],  # Luapan ekstrem
}

# Input 2: Debit Air (L/menit)
MF_FLOW = {
    "rendah": [0.0, 0.0, 5.0, 12.0],
    "sedang": [5.0, 12.0, 20.0],
    "tinggi": [12.0, 20.0, 30.0, 30.0],
}

# Output: Nilai Bahaya (0 s/d 100) (K7)
MF_DANGER = {
    "aman":    [0.0, 0.0, 30.0],
    "waspada": [15.0, 38.0, 60.0],
    "siaga":   [45.0, 65.0, 85.0],
    "bahaya":  [70.0, 100.0, 100.0],
}

# Ambang Batas Klasifikasi 4 Level Tegas
LEVEL_THRESHOLDS = {
    "AMAN":    (0.0, 25.0),
    "WASPADA": (25.0, 50.0),
    "SIAGA":   (50.0, 75.0),
    "BAHAYA":  (75.0, 100.1),
}

# ==========================================
# 5. TAMPILAN STATUS, WARNA, & LABEL (BAGIAN 6.4)
# ==========================================
LEVELS = {
    "AMAN": {
        "id": 0,
        "label": "AMAN",
        "bg_color": "#2E7D32",   # Hijau
        "text_color": "#FFFFFF",
    },
    "WASPADA": {
        "id": 1,
        "label": "WASPADA",
        "bg_color": "#F9A825",   # Kuning
        "text_color": "#212529",
    },
    "SIAGA": {
        "id": 2,
        "label": "SIAGA",
        "bg_color": "#EF6C00",   # Oranye
        "text_color": "#FFFFFF",
    },
    "BAHAYA": {
        "id": 3,
        "label": "BAHAYA",
        "bg_color": "#C62828",   # Merah
        "text_color": "#FFFFFF",
    },
    "TIDAK_VALID": {
        "id": None,
        "label": "DATA TIDAK VALID",
        "bg_color": "#757575",   # Abu-abu
        "text_color": "#FFFFFF",
    },
    "OFFLINE": {
        "id": None,
        "label": "OFFLINE",
        "bg_color": "#757575",   # Abu-abu
        "text_color": "#FFFFFF",
    },
}

# Ambang batas indikasi stabilitas tinggi global maket (Should)
GLOBAL_STABILITY_THRESHOLD_CM = 1.0

# ==========================================
# 6. PENGATURAN MQTT
# ==========================================
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_TELEMETRY = "ews/wavetank/telemetry"
MQTT_TOPIC_STATUS = "ews/wavetank/status"
MQTT_USER = "ews"
MQTT_PASSWORD = ""
