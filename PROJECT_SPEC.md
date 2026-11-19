# PROJECT_SPEC — Web Dashboard IoT untuk Sistem Peringatan Dini Gelombang Air

- **Judul TA:** Perancangan Sistem Fuzzy Logic untuk Klasifikasi Level Bahaya Kenaikan Gelombang Air pada Sistem Peringatan Dini Berbasis Raspberry Pi dan Web IoT
- **Penulis:** Deta Hata Maulana — Program Studi Rekayasa Instrumentasi dan Automasi, ITERA
- **Versi dokumen:** 1.0 — disusun 30 Oktober 2026
- **Jendela kerja:** 30 Okt – 31 Des 2026 (9 minggu)
- **Dibuat dari:** proposal Anda (termasuk Gambar 2.2), project-spec awal, Pedoman Penulisan TA Prodi IA, dan Tabel Komparasi Jurnal

> Dokumen ini adalah **pemandu kerja**: apa yang dibangun, dengan apa, dalam urutan apa, dan jebakan apa yang sering menimpa pemula. Dokumen ini **sengaja tidak berisi kode lengkap**. Kodenya Anda buat bersama AI agent (Antigravity / VS Code) dengan mengikuti dokumen ini, sehingga Anda tetap paham setiap bagiannya saat sidang.

## Daftar Isi

0. Cara Memakai File Ini
1. Gambaran Proyek
2. Temuan dari Berkas Anda dan Keputusan yang Perlu Dikunci
3. Aturan untuk AI Agent
4. Daftar Bahan (Stack)
5. Arsitektur Sistem
6. Spesifikasi Web Dashboard
7. Roadmap 5 Fase
8. Jebakan Lintas Fase
9. Bahan Penulisan BAB II dan BAB III
10. Demo dan Bukti
11. Kamus Mini
- Log Keputusan
- Lampiran A. Prompt Siap Tempel untuk Fase 1

---

## 0. Cara Memakai File Ini

1. Simpan file ini di folder paling atas proyek, misalnya `ews-gelombang/PROJECT_SPEC.md`.
2. Buka folder itu di Antigravity atau VS Code. Di awal **setiap** sesi chat dengan AI agent, tempel prompt pembuka ini:
   > Baca `PROJECT_SPEC.md` Bagian 3 (Aturan untuk AI Agent), Bagian 5–6 (arsitektur dan dashboard), dan fase yang sedang kita kerjakan di Bagian 7. Hari ini kita mengerjakan **Fase X, langkah Y**. Tulis rencana singkat dulu dan tunggu persetujuan saya sebelum membuat kode. Jelaskan setiap file dengan bahasa sederhana.
3. Opsional: buat file `AGENTS.md` **pendek** (3–5 baris) di folder yang sama, isinya kira-kira: "Proyek ini dipandu `PROJECT_SPEC.md`. Selalu patuhi Bagian 3 (Aturan untuk AI Agent) dan kerjakan hanya fase yang diminta." Menurut sumber komunitas yang saya periksa, Antigravity (v1.20.3 ke atas) membaca `AGENTS.md` dan `GEMINI.md` di root proyek secara otomatis; cek di menu Rules/Settings IDE Anda. Dengan cara ini agent tidak perlu memuat seluruh dokumen ini di setiap sesi. Bila ragu, tetap pakai prompt pembuka di atas.
4. Kerjakan **berurutan per fase**. Setiap fase punya daftar **Definition of Done (DoD)**; jangan pindah fase sebelum semua kotaknya tercentang.
5. Penanda di dalam dokumen:
   - **[PUTUSKAN]** = butuh keputusan Anda atau pembimbing.
   - **[JEBAKAN]** = kesalahan yang sering terjadi, beserta cara menghindarinya.
   - **[BUKTI]** = hasil yang harus Anda simpan (foto, screenshot, CSV) untuk BAB III–IV.
   - **[TULIS]** = bagian proposal/TA yang bisa ditulis pada fase itu.

---

## 1. Gambaran Proyek

Sistem membaca **ketinggian muka air** (4 sensor ultrasonik HC-SR04) dan **debit air** (flowmeter YF-S201) pada prototipe kanal gelombang (aquarium 100 × 40 × 40 cm). ESP32 mengumpulkan dan menyaring data. Raspberry Pi 4 menghitung **level bahaya dengan Fuzzy Mamdani**, menyimpannya di **SQLite**, lalu menampilkannya di **web dashboard** yang bisa dibuka dari laptop atau HP — termasuk dari luar jaringan lokal lewat **Cloudflare Tunnel**.

Batasan penelitian Anda yang **tidak boleh dilanggar** saat membuat fitur:

- Dashboard hanya untuk **monitoring** (data sensor, grafik, status level). **Tidak ada remote control.**
- Fuzzy hanya memakai **dua input**: ketinggian air dan debit air.
- Metode Mamdani, dijalankan terpusat di Raspberry Pi.
- Skala laboratorium; bukan pengganti peringatan resmi BMKG/BNPB → pasang *disclaimer* di footer dashboard.

---

## 2. Temuan dari Berkas Anda dan Keputusan yang Perlu Dikunci

Saya membaca proposal, project-spec awal, Pedoman, dan tabel jurnal Anda. Berikut hal-hal yang mengubah rancangan dibanding project-spec awal:

| # | Temuan | Dampak | Keputusan di dokumen ini |
|---|--------|--------|--------------------------|
| 1 | Gambar 2.2 proposal: sensor → **ESP32** → Wi-Fi/MQTT → Raspberry Pi (*Broker & Engine*) → Fuzzy Mamdani + **SQLite** + Flask → Cloudflare Tunnel → dashboard global. Project-spec awal mengasumsikan sensor langsung ke GPIO Pi. | Pi **tidak** membaca GPIO (paket `RPi.GPIO` tidak dipakai); Pi butuh **broker MQTT**; ada tahap firmware ESP32. | Ikuti Gambar 2.2. |
| 2 | Teks BAB II 2.1 menulis database **MySQL**, sedangkan Gambar 2.2 menulis **SQLite**. | Dua bagian proposal saling bertentangan. Di repositori Raspberry Pi OS, server yang lazim tersedia adalah MariaDB (kompatibel MySQL) yang butuh service server tersendiri. | **SQLite**. Ubah kata "MySQL" di 2.1. **[PUTUSKAN]** konfirmasi pembimbing. |
| 3 | Jumlah level: project-spec awal 4 (Aman/Waspada/Siaga/Bahaya); contoh evaluasi di proposal 3.12 hanya 3 (Aman/Waspada/Bahaya). | Mengubah himpunan output fuzzy, tabel aturan, warna, dan confusion matrix. | Default **4 level**, dibuat sebagai konfigurasi sehingga pindah ke 3 level murah. **[PUTUSKAN]** |
| 4 | Prompt Anda menulis mulai **30-10-2025**, padahal hari ini 30-10-2026. | Jadwal. | Jadwal memakai **2026**. Koreksi bila maksud Anda berbeda. |
| 5 | Project-spec awal menyimpan data tiap 5–10 detik. | Terlalu lambat untuk menangkap lonjakan gelombang (skenario demo "tuang air mendadak"). | Kirim dan simpan **1 detik sekali** (konfigurasi). |
| 6 | ESP32 punya dua keluaran: Serial → laptop (PLX-DAQ → Excel) dan Wi-Fi/MQTT → Pi. | Jalur Serial bukan bagian dashboard; ia dipakai untuk dataset dan kalibrasi. | Dipertahankan; dikerjakan di Fase 2. |
| 7 | Router lab/kampus bisa tanpa internet atau memisahkan perangkat satu sama lain. | Bootstrap/Chart.js dari CDN gagal dimuat; ESP32 tak bisa menjangkau Pi. | Semua file front-end disimpan **lokal**; pakai router/hotspot milik sendiri. |
| 8 | Cloudflare Quick Tunnel (dokumentasi resmi): tidak mendukung SSE, maksimal 200 permintaan bersamaan, URL acak berganti tiap dijalankan, tanpa jaminan uptime. | Memengaruhi cara dashboard memperbarui data dan rencana demo. | Dashboard memakai **polling 2 detik**; siapkan cadangan akses LAN. |
| 9 | Saya menguji scikit-fuzzy 0.5.0 (dengan numpy 2.5): `pip install scikit-fuzzy` **tidak** ikut memasang numpy, scipy, networkx, dan packaging; saat menghitung juga muncul *DeprecationWarning* dari numpy. | `import skfuzzy` langsung error pada instalasi baru; versi numpy yang jauh lebih baru kelak bisa merusak library. | Pasang semuanya eksplisit, **kunci versi lewat `requirements.txt`** (jangan upgrade numpy setelah semuanya jalan), dan siapkan rencana cadangan (Mamdani manual dengan NumPy). |

> Pengujian saya dilakukan di Linux x86 (Python 3.12, numpy 2.5): sistem Mamdani 2 input + centroid berjalan dan sangat cepat. Semua pustaka yang direkomendasikan murni-Python atau punya paket ARM64, tetapi **hardware Pi Anda belum saya uji** — karena itu Fase 1 memuat *smoke test* di Pi.

---

## 3. Aturan untuk AI Agent

Bagian ini ditujukan untuk AI agent di Antigravity/VS Code. Anda sebagai pemula juga sebaiknya membacanya: ini pagar pengaman supaya proyek tidak melebar.

1. Jawab dan beri komentar kode dalam **Bahasa Indonesia sederhana**. Istilah teknis diberi analogi singkat saat pertama muncul.
2. Mulai dengan **rencana 5–8 baris + daftar file** yang akan dibuat/diubah. **Tunggu persetujuan** sebelum menulis kode.
3. Kerjakan **satu fase, satu langkah kecil** per sesi. Jangan mengerjakan fase berikutnya.
4. Pakai **hanya stack di Bagian 4**. Menambah library/framework wajib bertanya dulu dan menjelaskan alasannya.
5. Ikuti **struktur folder flat** di Bagian 5.4. Dilarang: microservices, Docker/Kubernetes, ORM, framework frontend dengan build tools.
6. Semua angka penting (topik MQTT, interval, batas validasi, kalibrasi, parameter fuzzy, ambang level, warna) hanya ada di `config.py`, tidak ditulis ulang di tempat lain.
7. `fuzzy_engine.py` berisi **fungsi murni**: angka masuk → (nilai fuzzy, level) keluar. Tidak ada akses database atau MQTT di dalamnya, supaya mudah dites dan dibandingkan dengan hitungan manual.
8. Semua endpoint web **GET dan read-only**. Dilarang membuat endpoint atau tombol yang mengendalikan perangkat (Batasan Penelitian).
9. **Fail-safe:** data tidak valid atau terlambat **tidak boleh** tampil sebagai "AMAN". Tampilkan "DATA TIDAK VALID" atau "OFFLINE" (abu-abu).
10. **Validasi input sebelum fuzzy** (rentang, NaN, jumlah sensor valid), lalu batasi (*clamp*) ke rentang universe fuzzy.
11. Tidak ada rahasia (password MQTT, token Cloudflare) di kode atau Git. Pakai `.env` atau variabel lingkungan; `.env` masuk `.gitignore`.
12. Setelah menulis kode, berikan **perintah tes dan hasil yang diharapkan**, jalankan sendiri bila bisa, lalu laporkan hasil nyata. Jangan menulis "sudah berfungsi" tanpa menjalankannya.
13. Jangan merapikan atau mengubah file lain yang tidak diminta.
14. Target: Raspberry Pi 4 (ARM64), Python 3.11–3.13, dan laptop Windows. Hindari paket yang butuh kompilasi lama atau hanya jalan di satu OS.
15. Bila spesifikasi ambigu → **tanya**. Jangan menebak angka (rentang universe, ambang level); beri contoh dan tandai `# CONTOH — GANTI DENGAN DATA ANDA`.
16. Bila dokumen ini bertentangan dengan proposal → **laporkan**, jangan memilih diam-diam.

---

## 4. Daftar Bahan (Stack)

Dipilih berdasarkan tiga hal: **mudah dipelajari**, **dokumentasi dan komunitas luas** (mudah mencari solusi saat error), dan **ringan** untuk Raspberry Pi 4.

| Peran | Pilihan | Mengapa memilih ini? | Catatan Raspberry Pi / ARM |
|-------|---------|----------------------|----------------------------|
| Bahasa utama | **Python 3.11–3.13** | Satu bahasa untuk baca data, hitung fuzzy, simpan database, dan menjalankan web — seperti satu pegawai yang bisa jadi koki sekaligus kasir. | Sudah ada di Raspberry Pi OS. Wajib pakai *virtual environment* (venv): `pip` global diblokir (PEP 668). |
| Firmware ESP32 | **Arduino C++** (Arduino IDE 2.x) + pustaka **PubSubClient** | Sesuai Tabel 3.3 proposal; contoh dan forum paling banyak. | Berjalan di ESP32, bukan di Pi. Pi tidak memakai GPIO. |
| Broker MQTT | **Mosquitto** | "Kantor pos kecil": ESP32 menaruh surat (data) di kotak bernama *topic*, Python mengambilnya. Sangat ringan. | `sudo apt install mosquitto mosquitto-clients`. Mosquitto 2.x bawaannya hanya menerima koneksi dari Pi sendiri (lihat Fase 1). |
| Klien MQTT Python | **paho-mqtt 2.x** | "Kurir penerima surat" di sisi Python. | Murni Python. Versi 2.x mewajibkan argumen `callback_api_version` saat membuat Client — tutorial lama tanpa ini akan error. |
| Logika fuzzy | **scikit-fuzzy 0.5.0** (+ numpy, scipy, networkx, packaging) | "Kalkulator fuzzy": Anda mendefinisikan bentuk segitiga/trapesium dan aturan IF–THEN; ia menghitung inferensi Mamdani dan centroid. | Murni Python; numpy/scipy punya paket ARM64. Dependensi **harus dipasang manual** dan versinya **dikunci di `requirements.txt`** (Bagian 2 #9). |
| Backend web | **Flask 3.x** | "Lego": pasang hanya komponen yang dibutuhkan; jauh lebih ringan dari Django. | Murni Python. |
| Server web final | **waitress** (opsional, Fase 5) | Pengganti server bawaan Flask yang hanya untuk latihan; lebih tahan untuk uji 24 jam. | Murni Python. |
| Database | **SQLite** lewat modul `sqlite3` bawaan Python | "Buku catatan dalam satu file": tanpa server, tanpa password database; backup = salin file. | Sangat ringan. Aktifkan mode **WAL**. Alat bantu: `sudo apt install sqlite3`. |
| Frontend | **HTML5 + Bootstrap 5.3 + Chart.js 4 + JavaScript dasar** (`fetch`) | Bootstrap = rak dan kartu siap pakai; Chart.js = papan grafik. Tanpa build tools. | Berjalan di browser. **Simpan file-nya lokal** di `static/vendor/`. |
| Menjalankan otomatis | **systemd** | "Satpam": menyalakan program saat Pi hidup dan menyalakannya lagi bila mati. | Bawaan Raspberry Pi OS. |
| Akses dari internet | **cloudflared** (Cloudflare Tunnel) | "Terowongan keluar": Pi menyambung ke Cloudflare, jadi tidak perlu membuka port di router. | Tersedia untuk Linux arm64 (unduhan resmi Cloudflare). Quick Tunnel tanpa akun; URL tetap butuh akun + domain. |
| Alat bantu (laptop) | VS Code/Antigravity, Git, MQTT Explorer (atau `mosquitto_sub`), DB Browser for SQLite, PLX-DAQ + Excel | Masing-masing satu tugas: menulis kode, menyimpan versi, mengintip pesan MQTT, melihat isi database, merekam data Serial. | PLX-DAQ hanya Windows + Excel (sesuai laptop Anda). |

**Perintah instalasi** (bukan kode program; salin apa adanya):

```
# Laptop Windows (PowerShell), di folder proyek
py -m venv .venv
.venv\Scripts\activate
pip install flask paho-mqtt numpy scipy networkx packaging scikit-fuzzy waitress
pip freeze > requirements.txt

# Raspberry Pi (lewat SSH), di folder proyek
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y mosquitto mosquitto-clients sqlite3 git python3-venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Smoke test — harus mencetak OK di laptop DAN di Pi
python -c "import flask, paho.mqtt, numpy, scipy, networkx, skfuzzy; print('OK')"
```

**Sengaja TIDAK dipakai** (dan alasannya):

- **Django** — terlalu besar untuk satu halaman dan dua endpoint.
- **MySQL/MariaDB** — butuh service server; tidak ada manfaatnya untuk satu tabel dan satu penulis.
- **Docker, Kubernetes, microservices** — berlebihan untuk skala skripsi.
- **React/Vue/Node.js** — butuh build tools dan menambah kurva belajar.
- **WebSocket / Flask-SocketIO / SSE** — lebih rumit; SSE tidak didukung Cloudflare Quick Tunnel. Polling 2 detik sudah cukup.
- **Grafana / InfluxDB / Node-RED** — bagus, tetapi dashboard buatan sendiri adalah bagian penelitian Anda (3.8 Perancangan Dashboard).
- **RPi.GPIO** — sensor ada di ESP32, bukan di Pi.
- **OpenCV / TensorFlow** — tidak relevan (sisa templat proyek *computer vision*).

---

## 5. Arsitektur Sistem

### 5.1 Diagram (selaras dengan Gambar 2.2 proposal)

```
 [4x HC-SR04] --\
                 +--> [ESP32] --(1) Serial/kabel--> [Laptop: PLX-DAQ -> Excel]
 [YF-S201] -----/        |                          (dataset & kalibrasi)
                         | (2) Wi-Fi 2,4 GHz + MQTT, 1x/detik
                         v
 +--------------------- Raspberry Pi 4 Model B ----------------------+
 |  Mosquitto (broker)                                               |
 |      | subscribe                                                  |
 |      v                                                            |
 |  worker.py : validasi -> kalibrasi -> Fuzzy Mamdani -> INSERT     |
 |                                                  |                |
 |                                                  v                |
 |                                   SQLite (data/ews.db, mode WAL)  |
 |                                                  ^ SELECT         |
 |  app.py (Flask) : halaman HTML + API JSON (GET) -+   port 5000    |
 +---------+-------------------------------+-------------------------+
           | LAN                           | cloudflared (tunnel keluar)
           v                               v
   Browser di jaringan sama        https://xxxx.trycloudflare.com
   http://<IP-Pi>:5000             -> browser dari internet
```

### 5.2 Peran Tiap Blok (analogi)

- **Sensor (HC-SR04, YF-S201)** = mata dan meteran: mengukur jarak ke permukaan air dan aliran air.
- **ESP32** = kurir: mengumpulkan hasil ukur, menyaring yang aneh, lalu mengirimkannya.
- **Mosquitto** = kantor pos: menerima kiriman dan meneruskannya ke yang berlangganan.
- **worker.py** = juru hitung: memeriksa data, menghitung fuzzy, mencatat ke buku.
- **SQLite** = buku besar: seluruh riwayat tersimpan rapi.
- **app.py (Flask)** = pelayan/etalase: menyajikan halaman dan data kepada pengunjung.
- **Browser** = pelanggan.
- **Cloudflare Tunnel** = pintu belakang yang aman: pelanggan dari luar bisa masuk tanpa membuka pintu depan (port) rumah Anda.

### 5.3 Dua Proses dan Mode Simulasi

- **Dua proses terpisah** di Pi: `worker.py` (menulis data) dan `app.py` (menyajikan web). Keduanya hanya "bertemu" lewat file SQLite. Analogi: dapur dan pelayan — pelayan boleh ganti shift tanpa dapur berhenti memasak. Jika web error, pencatatan data tetap jalan (penting untuk uji 24 jam).
- **Mode simulasi** adalah kunci kecepatan pengerjaan. Di `config.py` ada pilihan sumber data: `sim` (data palsu buatan program) atau `mqtt` (data nyata dari ESP32). Dengan `sim`, dashboard dan fuzzy bisa dikerjakan di laptop **tanpa menunggu hardware**.
- Simulator minimal punya 5 skenario:

| Skenario | Perilaku | Hasil yang diharapkan |
|----------|----------|-----------------------|
| `tenang` | ketinggian rendah, debit kecil, noise kecil | AMAN |
| `naik_perlahan` | ketinggian dan debit naik bertahap | AMAN → WASPADA → SIAGA |
| `lonjakan` | ketinggian dan debit melonjak dalam < 3 detik | naik sampai BAHAYA |
| `gelombang_noise` | ketinggian berosilasi + noise | level tidak berkedip liar di batas kategori |
| `sensor_error` | 1–4 sensor bernilai `null` secara acak | DATA TIDAK VALID bila < 2 sensor valid |

### 5.4 Struktur Folder (flat, sengaja sederhana)

```
ews-gelombang/
├── PROJECT_SPEC.md          <- file ini
├── AGENTS.md                <- (opsional) 3-5 baris yang menunjuk ke file ini
├── requirements.txt
├── .gitignore               <- .venv/, data/*.db, .env
├── .env                     <- rahasia (password MQTT); JANGAN di-commit
├── config.py                <- SEMUA angka & nama penting
├── fuzzy_engine.py          <- fuzzy Mamdani: fungsi murni
├── db.py                    <- fungsi SQLite (dipakai worker & app)
├── sources.py               <- sumber data: simulator, MQTT
├── worker.py                <- PROSES 1: ambil -> validasi -> kalibrasi -> fuzzy -> simpan
├── app.py                   <- PROSES 2: Flask (halaman + API GET)
├── templates/index.html     <- halaman dashboard
├── static/
│   ├── css/app.css
│   ├── js/app.js
│   └── vendor/              <- bootstrap & chart.js (unduh sekali, simpan lokal)
├── firmware/esp32_ews/      <- sketch Arduino (.ino)
├── deploy/                  <- contoh service systemd, catatan mosquitto & cloudflared
├── tests/                   <- tes kecil (fuzzy vs hitungan manual, validasi payload)
├── data/                    <- ews.db, hasil ekspor, backup (tidak di-commit)
└── docs/                    <- screenshot, foto, tabel uji (bukti BAB III–IV)
```

### 5.5 Kontrak Data ESP32 → Raspberry Pi (MQTT)

"Kontrak" = kesepakatan format data supaya sisi ESP32 dan sisi Pi bisa dikerjakan terpisah tanpa saling menebak. **Jangan diubah sepihak.**

- **Broker:** `<IP atau hostname Pi>:1883` (Mosquitto, memakai user dan password).
- **Topic telemetri:** `ews/wavetank/telemetry` — QoS 0, dikirim **1× per detik**.
- **Topic status:** `ews/wavetank/status` — berisi `online` (retained) saat ESP32 tersambung. *Last Will* ("pesan wasiat" yang dikirim broker atas nama ESP32) otomatis mengubahnya jadi `offline` bila ESP32 mati mendadak.
- **Payload telemetri** (JSON satu baris, contoh):

```
{"seq":1024,"up_ms":512340,"us_cm":[22.4,22.1,22.9,null],"flow_lpm":8.6}
```

| Field | Arti | Aturan |
|-------|------|--------|
| `seq` | Nomor urut pesan, naik 1 tiap kirim | Dipakai Pi untuk mendeteksi pesan hilang |
| `up_ms` | Lama ESP32 menyala (milidetik) | Bukan jam dinding; jam dinding dipasang Pi saat pesan diterima |
| `us_cm` | 4 jarak sensor → permukaan air (cm), sudah disaring di ESP32 | `null` bila sensor gagal baca |
| `flow_lpm` | Debit (L/menit) dengan faktor awal datasheet | Dikalibrasi lagi di Pi |

**Pembagian tugas:**

- **ESP32:** membaca sensor, menyaring (median per sensor, membuang bacaan di luar 2–400 cm), mengirim. **Tidak** menghitung level bahaya.
- **Raspberry Pi:** validasi → ubah jarak jadi ketinggian → kalibrasi → fuzzy → simpan. Konstanta kalibrasi ada di `config.py` sehingga **tidak perlu flash ulang ESP32** setiap kali kalibrasi.

**Aturan validasi di Pi** (angkanya di `config.py`):

1. Payload bukan JSON atau field hilang → buang dan catat di log.
2. Jarak sensor dianggap valid hanya bila berada di rentang yang mungkin secara fisik pada aquarium Anda.
3. Perlu minimal **2 dari 4** sensor valid (`MIN_SENSOR_VALID`); kurang dari itu → `sensor_ok = 0`.
4. `ketinggian_cm = TINGGI_PASANG_CM − median(jarak valid)`, lalu koreksi kalibrasi (a·x + b), lalu dibatasi ke 0–`TINGGI_MAKS_CM`. **[PUTUSKAN]** median atau rata-rata; default median karena tahan terhadap satu sensor yang meleset. Tulis pilihan Anda di BAB III.
5. Debit negatif atau di atas batas sensor → tidak valid.
6. Tidak ada pesan baru lebih dari `STALE_AFTER_S` (default 5 detik) → dashboard menampilkan OFFLINE.

### 5.6 Skema Database

Satu tabel utama, `logs_sensor`:

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id` | INTEGER, primary key | otomatis |
| `ts_ms` | INTEGER | waktu terima di Pi (epoch UTC, milidetik). **Beri index.** |
| `seq` | INTEGER | nomor urut dari ESP32 |
| `us1_cm` … `us4_cm` | REAL | jarak tersaring per sensor; boleh NULL |
| `n_valid` | INTEGER | jumlah sensor valid |
| `ketinggian_cm` | REAL | hasil agregasi + kalibrasi; NULL bila tidak valid |
| `debit_lpm` | REAL | hasil kalibrasi |
| `nilai_fuzzy` | REAL | 0–100; NULL bila tidak valid |
| `level` | TEXT | AMAN / WASPADA / SIAGA / BAHAYA / TIDAK_VALID |
| `level_id` | INTEGER | 0–3; NULL bila tidak valid |
| `sensor_ok` | INTEGER | 1 atau 0 |
| `sumber` | TEXT | `sim` atau `mqtt` |

- Jarak mentah per sensor **sengaja ikut disimpan**: itu bukti untuk validasi sensor dan perhitungan MAE/RMSE (3.10.6, 3.12).
- Tabel opsional `events` (*Should*): satu baris tiap level berubah (`id, ts_ms, level_dari, level_ke, nilai_fuzzy`) untuk panel riwayat dan ukuran waktu-tanggap.
- Aktifkan **mode WAL** (`PRAGMA journal_mode=WAL`): pembaca (web) dan penulis (worker) tidak saling memblokir. Hanya **satu penulis** (worker).
- Simpan waktu dalam UTC; tampilkan WIB (UTC+7) di dashboard.
- Perkiraan kasar: 1 baris/detik ≈ 86.400 baris/hari ≈ 10 MB/hari — cukup untuk uji 24 jam.

### 5.7 Endpoint API (semua GET, read-only)

| Endpoint | Isi |
|----------|-----|
| `/` | halaman dashboard |
| `/api/now` | data terbaru + `age_s` (umur data) + status `online` |
| `/api/history?limit=120` | N titik terakhir, urut waktu naik; server membatasi `limit` maksimum |
| `/api/history?minutes=30` | rentang waktu; diperkecil (*downsample*) di server bila terlalu banyak titik |
| `/api/events?limit=10` | perubahan level terakhir |
| `/api/export.csv?from=…&to=…` | unduh CSV (epoch ms) untuk dihitung di Excel (MAE, RMSE, confusion matrix) |
| `/health` | `ok` + umur data terakhir + ukuran database (berguna untuk uji 24 jam) |

Tidak ada POST/PUT/DELETE dari browser.

---

## 6. Spesifikasi Web Dashboard

### 6.1 Sketsa Tata Letak

```
+----------------------------------------------------------------------+
| EWS Gelombang Air - Kanal Gelombang Lab       [ONLINE]  12:03:41 WIB |
|                                           data terakhir 1 detik lalu |
+----------------+----------------+----------------+-------------------+
| KETINGGIAN     | DEBIT          | NILAI FUZZY    | STATUS BAHAYA     |
| 18,4 cm        | 9,2 L/mnt      | 62 / 100       | SIAGA             |
| maks: 19,1     | maks: 10,4     | [######----]   | (kartu oranye)    |
+----------------+----------------+----------------+-------------------+
| GRAFIK UTAMA: ketinggian (cm) dan debit (L/mnt), 120 titik terakhir  |
| (dua sumbu Y: garis ketinggian + garis debit)                        |
+----------------------------------+-----------------------------------+
| Grafik nilai fuzzy (0-100)       | Riwayat perubahan level (10)      |
+----------------------------------+-----------------------------------+
| [Jeda]  Rentang: [2 mnt] [30 mnt] [2 jam]  [Unduh CSV]               |
| Prototipe skala laboratorium - bukan pengganti peringatan BMKG/BNPB  |
+----------------------------------------------------------------------+
```

### 6.2 Perilaku yang Harus Ada

- **Pembaruan data:** browser memanggil `/api/now` setiap **2 detik** (*polling*: seperti menelepon tiap 2 detik untuk bertanya "ada kabar baru?"). Riwayat grafik dimuat **sekali** dari `/api/history` saat halaman dibuka, lalu tiap titik baru ditambahkan. Simpan maksimal 120 titik (yang tertua dibuang) agar browser tidak membengkak.
- **Kartu Status:** tampilkan **teks + ikon + warna** — jangan hanya warna, agar tetap terbaca oleh pengguna dengan gangguan penglihatan warna dan saat dicetak hitam-putih.
- **Offline / terlambat:** jika `age_s` lebih besar dari `STALE_AFTER_S` atau `fetch` gagal → semua kartu abu-abu, status "OFFLINE — data terlambat", dan level terakhir **tidak** dipajang sebagai kondisi saat ini.
- **Data tidak valid:** status "DATA TIDAK VALID" (abu-abu) beserta alasan singkat (mis. "sensor valid: 1 dari 4").
- **Responsif:** HP portrait 1 kolom, tablet 2 × 2, laptop 1 × 4 (kelas grid Bootstrap).
- **Waktu:** tampil WIB (UTC+7); database tetap UTC.
- **Footer:** disclaimer penelitian (Bagian 1).

### 6.3 Prioritas Fitur

| Prioritas | Fitur |
|-----------|-------|
| **Must** (wajib) | 4 kartu metrik; grafik real-time ketinggian + debit; status berwarna; indikator online/offline + umur data; responsif; **bekerja tanpa internet** (aset lokal); `/api/now`, `/api/history`, `/health` |
| **Should** | Ekspor CSV; panel riwayat perubahan level; pilihan rentang waktu; kartu berkedip halus saat ≥ SIAGA; grafik nilai fuzzy |
| **Could** (hanya bila waktu sisa) | Mode gelap; bunyi alarm di browser; notifikasi Telegram saat BAHAYA (di luar Batasan Penelitian dan butuh internet — konsultasikan dulu) |
| **Won't** | Remote control/aktuator; login multi-pengguna; aplikasi mobile; database cloud; prediksi/machine learning |

### 6.4 Warna dan Status

| Level | `level_id` | Warna kartu | Catatan |
|-------|-----------|-------------|---------|
| AMAN | 0 | hijau `#2E7D32` | teks putih |
| WASPADA | 1 | kuning `#F9A825` | teks gelap |
| SIAGA | 2 | oranye `#EF6C00` | teks putih |
| BAHAYA | 3 | merah `#C62828` | teks putih |
| DATA TIDAK VALID / OFFLINE | — | abu-abu `#757575` | teks putih; **tidak pernah** tampil sebagai AMAN |

Warna dan nama level disimpan di `config.py` (bila pindah ke 3 level, cukup mengubah di sana).

### 6.5 Aturan Teknis Front-end

- Bootstrap dan Chart.js diunduh sekali ke `static/vendor/`; HTML memanggil file lokal, **bukan** link CDN. Alasan: Pi/lab sering tanpa internet.
- Label sumbu waktu berupa teks `HH:MM:SS`; hindari *time scale* Chart.js karena butuh adapter tambahan.
- Setiap `fetch` dibungkus penanganan error; saat gagal → tampilkan badge "Terputus dari Pi".
- Tidak ada token atau rahasia di JavaScript.
- Jalankan produksi dengan mode `debug` mati.

---

## 7. Roadmap 5 Fase (30 Okt – 31 Des 2026)

**Prinsip utama: *walking skeleton* dulu, baru ditebalkan.** Pada Fase 1 Anda sudah membuat jalur lengkap dari data simulasi sampai dashboard yang hidup. Fase 2–5 mengganti bagian palsu dengan yang asli satu per satu. Jika hardware terlambat, Anda tetap punya sistem yang bisa didemokan.

| Fase | Minggu | Tanggal | Fokus | Hasil utama |
|------|--------|---------|-------|-------------|
| 1 | 1 | 30 Okt – 5 Nov | Fondasi + kerangka dashboard (data simulasi) | Dashboard hidup di laptop dan di Pi |
| 2 | 2–3 | 6 – 19 Nov | Hardware dan sensor (ESP32), kalibrasi | Data nyata terkalibrasi masuk ke MQTT |
| 3 | 4–5 | 20 Nov – 3 Des | Fuzzy Mamdani | FIS tervalidasi + dataset uji |
| 4 | 6 | 4 – 10 Des | Backend dan database (data nyata) | Pipeline otomatis dan tahan banting |
| 5 | 7–8 | 11 – 24 Des | Dashboard final, tunnel, uji 24 jam, demo | Sistem siap sidang |
| — | 9 | 25 – 31 Des | Penyangga (*buffer*) | Perbaikan, penulisan, latihan |

Jalur paralel di luar dokumen ini:

- **Mekanik** (frame, wave maker, motor gearbox, aquarium): harus siap paling lambat **akhir Minggu 5** agar uji skenario Fase 3 dan 5 bisa berjalan.
- **Penulisan:** tiap fase punya butir **[TULIS]**. Menulis sambil jalan jauh lebih ringan daripada menumpuk di Desember.

---

### Fase 1 — Fondasi dan Kerangka Dashboard (Minggu 1: 30 Okt – 5 Nov)

**Target:** laptop dan Raspberry Pi siap kerja; dashboard berdata simulasi sudah tampil di keduanya.

**Langkah:**

1. **Laptop (Windows):** pasang Python 3.11+ (python.org, centang *Add python.exe to PATH*), VS Code/Antigravity, dan Git. Buat folder `ews-gelombang`, buat dan aktifkan venv, pasang paket (Bagian 4), jalankan **smoke test**.
2. **Raspberry Pi:** pakai Raspberry Pi Imager → *Raspberry Pi OS (64-bit)*. Di *OS customisation* isi: hostname `ews-pi`, user + password, Wi-Fi, **SSH aktif**, zona waktu `Asia/Jakarta`. Pilih versi **Desktop** bila Anda memakai HDMI capture (Tabel 3.2); selain itu versi **Lite** + SSH lebih ringan.
3. Dari laptop: `ssh <user>@ews-pi.local` (atau pakai IP). Pasang paket sistem + venv + dependensi (Bagian 4) dan jalankan smoke test di Pi. Cek jam (`timedatectl`) dan suhu (`vcgencmd measure_temp`).
4. **Mosquitto:** tes lokal dulu (terminal A: `mosquitto_sub -t test -v`; terminal B: `mosquitto_pub -t test -m halo`). Lalu buka akses jaringan lokal dengan konfigurasi di bawah, buat user, restart, dan tes dari laptop (MQTT Explorer atau `mosquitto_pub` ke IP Pi).
5. **Minta agent membuat kerangka** memakai prompt di Lampiran A: `config.py`, `db.py`, `sources.py` (simulator), `fuzzy_engine.py` (parameter *contoh*), `worker.py`, `app.py`, `templates/index.html`, `static/`. Unduh Bootstrap dan Chart.js ke `static/vendor/`.
6. **Jalankan di laptop:** terminal A `python worker.py`, terminal B `python app.py`, buka `http://127.0.0.1:5000`. Kartu dan grafik harus bergerak; ganti skenario simulator dan lihat level serta warna berubah.
7. **Salin ke Pi** (Git atau `scp -r`), jalankan dengan cara yang sama, buka dari browser laptop: `http://ews-pi.local:5000` (atau `http://<IP-Pi>:5000`).
8. `git init`, buat `.gitignore`, commit pertama, beri tag `fase1-ok`.

**Konfigurasi Mosquitto untuk langkah 4** — file `/etc/mosquitto/conf.d/ews.conf`:

```
listener 1883
allow_anonymous false
password_file /etc/mosquitto/passwd
```

Lalu: `sudo mosquitto_passwd -c /etc/mosquitto/passwd ews` dan `sudo systemctl restart mosquitto`.

**DoD Fase 1:**

- [ ] Smoke test mencetak `OK` di laptop **dan** di Pi.
- [ ] `requirements.txt` dibuat dari `pip freeze` setelah smoke test di laptop sukses, lalu dipakai untuk instalasi di Pi (versi yang sama di kedua tempat).
- [ ] Pesan MQTT dari laptop sampai ke Pi dan terbaca (tes pub/sub dengan user + password).
- [ ] Dashboard data simulasi tampil di laptop dan di Pi (dibuka dari browser laptop).
- [ ] Kelima skenario simulator menghasilkan perubahan level yang masuk akal; `sensor_error` menghasilkan DATA TIDAK VALID (bukan AMAN).
- [ ] Jam Pi benar (WIB).

**[BUKTI]:** screenshot dashboard, foto Pi + wiring awal, output smoke test, diagram arsitektur final.

**[JEBAKAN]:**

- PowerShell menolak `activate` ("running scripts is disabled") → jalankan sekali: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- `pip` di Pi menolak ("externally-managed-environment") → Anda lupa mengaktifkan venv.
- Mosquitto 2.x tanpa konfigurasi **hanya menerima koneksi dari Pi sendiri** → ESP32/laptop tak bisa terhubung sampai `listener 1883` dibuat.
- Wi-Fi kampus sering memisahkan perangkat (*client isolation*) atau memakai halaman login → pakai router/hotspot sendiri untuk laptop + Pi + ESP32; beri Pi **IP tetap** (reservasi DHCP di router).
- `ews-pi.local` kadang tidak terbaca di Windows → pakai alamat IP.

**[TULIS]:** BAB II 2.1.2 Web Dashboard, 2.1.3 Database, 2.1.4 Komunikasi Data IoT (lihat Bagian 9); perbaiki Tabel 3.2 dan 3.3; buat gambar arsitektur untuk 3.6.1.

---

### Fase 2 — Hardware dan Sensor (Minggu 2–3: 6 – 19 Nov)

**Target:** ESP32 membaca 4 sensor ultrasonik dan 1 flowmeter dengan stabil; hasilnya terkalibrasi dan masuk ke MQTT di Pi tiap detik.

**Usulan pin ESP32** (cek ulang pinout board Anda sebelum menyolder):

| Fungsi | GPIO ESP32 | Catatan |
|--------|-----------|---------|
| TRIG 1–4 | 16, 17, 18, 19 | keluaran |
| ECHO 1–4 | 34, 35, 32, 33 | masukan — **lewat pembagi tegangan** (1 kΩ seri, 2 kΩ ke GND ≈ 3,3 V) |
| Sinyal YF-S201 | 27 | masukan interrupt; pastikan sinyal ≤ 3,3 V |
| VCC HC-SR04 | pin 5 V (VIN/USB) | semua GND dihubungkan bersama |

**Langkah:**

1. Siapkan: ESP32 DevKit + kabel USB data, 4× HC-SR04, 1× YF-S201, resistor 1 kΩ dan 2 kΩ (pembagi tegangan; siapkan 5 pasang), breadboard, jumper, catu 5 V.
2. **Pengkabelan bertahap** — satu sensor dulu, tes, baru tambah.
3. **Firmware bertahap** (Arduino IDE), tiap langkah dites sendiri:
   - a. 1 sensor → Serial Monitor.
   - b. 4 sensor **bergantian**, jeda ≥ 60 ms antar sensor.
   - c. Filter: median 5 sampel per sensor; buang bacaan di luar 2–400 cm (tandai `null`).
   - d. Flowmeter: hitung pulsa dengan interrupt, jendela 1 detik; L/menit = frekuensi ÷ 7,5 sebagai **faktor awal** (nilai umum di datasheet; wajib dikalibrasi).
   - e. Keluaran Serial berformat PLX-DAQ → laptop → Excel.
   - f. Wi-Fi + MQTT: kirim JSON sesuai kontrak (Bagian 5.5) 1× per detik, plus topic status dan *Last Will*.
4. **Kalibrasi ketinggian** (3.10.1, 3.10.3, 3.10.4): minimal 6 titik ketinggian (mis. 5–30 cm) × 30 sampel, dibandingkan dengan penggaris/meteran. Regresi linear → konstanta a dan b → hitung MAE, RMSE, %error → simpan di `config.py`.
5. **Kalibrasi debit** (3.10.2, 3.10.5): tuang ke wadah ukur (1–2 liter) dengan 3 kecepatan pompa × 5 pengulangan → faktor koreksi → MAE dan %error.
6. **Verifikasi di Pi:** `mosquitto_sub -h localhost -u ews -P <password> -t "ews/#" -v` menampilkan JSON tiap detik selama 30 menit tanpa putus.
7. Kumpulkan **dataset awal** lewat PLX-DAQ (Excel) untuk skenario uji — bahan menentukan rentang fungsi keanggotaan di Fase 3.

**DoD Fase 2:**

- [ ] Setiap sensor sudah dites sendiri-sendiri; bacaan air diam stabil (catat simpangan baku).
- [ ] Tegangan pin Echo dan sinyal flowmeter diukur dengan multimeter: **≤ 3,3 V**.
- [ ] Tabel kalibrasi (titik uji, MAE, RMSE, %error) tersimpan untuk ketinggian dan debit.
- [ ] JSON tiba di Pi tiap detik selama 30 menit tanpa putus; `seq` berurutan.
- [ ] Jalur Serial → PLX-DAQ → Excel menghasilkan file data.

**[BUKTI]:** foto rangkaian, tabel kalibrasi, grafik regresi, screenshot Serial Monitor + `mosquitto_sub`, file Excel PLX-DAQ.

**[JEBAKAN]:**

- GPIO ESP32 **hanya 3,3 V** (tidak toleran 5 V). Echo HC-SR04 berkeluaran 5 V → wajib pembagi tegangan atau *level shifter*; atau pakai varian HC-SR04 yang 3,3 V.
- Jangan memicu 4 HC-SR04 serentak — suaranya saling mengganggu (*crosstalk*) dan bacaan kacau.
- Bacaan 0 atau > 400 cm = gagal baca, **bukan** jarak 0 cm.
- Zona buta HC-SR04 ± 2 cm: pasang sensor **minimal 2–3 cm di atas** permukaan air tertinggi.
- Gelombang memantulkan suara menyamping sehingga echo hilang → pasang sensor tegak lurus, pakai median, dan catat persentase bacaan gagal.
- HC-SR04 bukan *waterproof*: lindungi dari percikan; jauhkan breadboard dan kabel dari air.
- ESP32 klasik hanya mendukung Wi-Fi **2,4 GHz**.
- PubSubClient: ukuran paket bawaan 256 byte → pesan lebih besar dibuang diam-diam; naikkan dengan `setBufferSize(512)`.
- Hindari pin *strapping* (GPIO 0, 2, 5, 12, 15) dan pin flash (6–11) untuk sensor; GPIO 34–39 hanya bisa input dan tanpa pull-up internal.

**[TULIS]:** BAB II 2.2.x (sensor) dan 2.3 (wave flume); BAB III 3.5, 3.7.1 (program ESP32), 3.10.x (kalibrasi).

---

### Fase 3 — Logika Fuzzy Mamdani (Minggu 4–5: 20 Nov – 3 Des)

**Target:** FIS Mamdani yang parameternya punya alasan jelas, hasilnya cocok dengan hitungan manual, dan akurasinya terukur.

**Basis aturan awal 3 × 3** (usulan — ganti sesuai pembimbing):

| Ketinggian \ Debit | Lambat | Sedang | Cepat |
|--------------------|--------|--------|-------|
| **Rendah** | Aman | Aman | Waspada |
| **Sedang** | Waspada | Siaga | Siaga |
| **Tinggi** | Siaga | Bahaya | Bahaya |

**Langkah:**

1. **Variabel.** Input 1: Ketinggian (cm) — Rendah / Sedang / Tinggi. Input 2: Debit (L/menit) — Lambat / Sedang / Cepat. Output: Nilai Bahaya 0–100 — Aman / Waspada / Siaga / Bahaya. **[PUTUSKAN]** 3 atau 4 level.
2. **Rentang (universe) dan titik fungsi keanggotaan** ditentukan dari: tinggi aquarium dan hasil kalibrasi, rentang kerja flowmeter (umumnya 1–30 L/menit), literatur/pembimbing, dan dataset Fase 2. **Tulis alasan tiap angka** — ini bahan BAB III 3.11. Angka dari agent selalu berstatus *contoh*.
3. **Metode:** Mamdani; AND = min; implikasi = min; agregasi = max; defuzzifikasi = **centroid**.
4. Implementasi di `fuzzy_engine.py`: sistem **dibangun sekali** saat program mulai, lalu dipakai berulang lewat satu fungsi `hitung(ketinggian, debit)`. Input dibatasi (*clamp*) ke universe.
5. **Pemetaan nilai → level:** ambang di `config.py` (contoh: < 25 Aman; 25–50 Waspada; 50–75 Siaga; ≥ 75 Bahaya) atau himpunan dengan keanggotaan tertinggi. **[PUTUSKAN]**
6. **Validasi manual:** pilih ≥ 8 titik uji (termasuk 3 titik di perbatasan kategori). Hitung di Excel langkah demi langkah (fuzzifikasi → kekuatan aturan → agregasi → centroid), dengan resolusi universe yang sama dengan program. Selisih hanya boleh sebatas pembulatan.
7. **Uji skenario data nyata:** rancang 12–20 skenario (kombinasi ketinggian × debit), ulangi beberapa kali. **Label *ground truth* ditetapkan sebelum melihat keluaran fuzzy** (mis. dari kriteria fisik yang disepakati pembimbing) supaya evaluasi tidak berputar-putar. Hitung akurasi dan *confusion matrix*.
8. Opsional anti-berkedip: rata-rata bergerak 3–5 detik atau *hysteresis*. Jika dipakai, tulis di BAB III.

**DoD Fase 3:**

- [ ] Tabel validasi manual vs program (≥ 8 titik) cocok.
- [ ] Semua parameter fungsi keanggotaan, aturan, dan ambang ada di `config.py` dan **sama persis** dengan yang ditulis di BAB III.
- [ ] Ada tes otomatis kecil di `tests/` untuk titik "pasti aman", "pasti bahaya", dan titik perbatasan.
- [ ] *Confusion matrix* + akurasi dari skenario uji tersimpan.

**[BUKTI]:** grafik fungsi keanggotaan (dicetak dari program), tabel aturan, tabel validasi manual, *confusion matrix*.

**[JEBAKAN]:**

- Celah pada universe (ada nilai input yang tidak "ditangkap" fungsi keanggotaan mana pun, sehingga tidak ada aturan yang aktif): pada scikit-fuzzy 0.5.0 `compute()` selesai **tanpa error**, tetapi hasilnya kosong sehingga `KeyError` baru muncul saat membaca output. Pastikan himpunan saling menutupi seluruh rentang, dan bungkus pembacaan hasil dengan penanganan error (→ level TIDAK_VALID).
- Pada uji saya, input di luar universe **diam-diam dibatasi** ke tepi dan **tidak** error — sensor rusak (mis. 999 cm) bisa menghasilkan level yang tampak valid. Karena itu validasi sensor dilakukan **sebelum** fuzzy (Aturan Agent #10).
- Centroid hampir tak pernah mencapai tepat 0 atau 100. Pada uji saya, himpunan output segitiga `[70, 100, 100]` menghasilkan maksimum ≈ 90 (bentuk trapesium malah sedikit lebih rendah, ≈ 89). Bila ingin angka mendekati 100, **geser awal himpunan ujung mendekati tepi** (mis. `[85, 100, 100]` → ≈ 95). Apa pun pilihannya, jadikan **level (kategori)** sebagai informasi utama dan angka sebagai pendukung.
- Jangan membuat ulang sistem fuzzy tiap detik; buat sekali, pakai berulang.
- scikit-fuzzy 0.5.0 sudah memunculkan *DeprecationWarning* dari numpy 2.5. Kunci versi lewat `requirements.txt` dan **jangan upgrade numpy** setelah semuanya jalan. **Rencana cadangan:** Mamdani (min–max–centroid) bisa ditulis manual dengan NumPy; minta agent membuatnya hanya sebagai pembanding/cadangan, sekaligus berguna untuk validasi hitungan manual.
- Satuan tertukar (cm vs mm, L/menit vs L/detik) adalah sumber error klasik — tulis satuan di nama variabel.

**[TULIS]:** BAB II 2.4.x; BAB III 3.11 (Pengujian Fuzzy), kerangka 3.12, dan **3.13 Parameter Keberhasilan** — isi X, Y, Z dengan angka setelah uji pendahuluan dan disepakati pembimbing (bentuk: error ketinggian ≤ …%, error debit ≤ …%, akurasi ≥ …%, latensi ≤ … detik).

---

### Fase 4 — Backend dan Database dengan Data Nyata (Minggu 6: 4 – 10 Des)

**Target:** dari ESP32 sampai database berjalan **otomatis**, pulih sendiri saat ada gangguan, dan bisa diekspor.

**Langkah:**

1. Ubah sumber data jadi `mqtt` di Pi. `worker.py`: berlangganan topic, validasi, kalibrasi (sisi Pi), fuzzy, simpan. Callback MQTT hanya menaruh pesan ke antrean; perhitungan dilakukan di luar callback supaya koneksi tidak tertahan.
2. Database: mode WAL, index `ts_ms`, tabel `events`; satu penulis (worker), banyak pembaca (web). Commit tiap ±1 detik, bukan tiap baris di loop cepat.
3. **Ketahanan:** sambung ulang MQTT otomatis; `subscribe` dilakukan **di dalam** `on_connect` (agar langganan pulih setelah putus); bila ESP32 mati → catat status offline dan **jangan menulis nilai palsu**; hitung pesan yang hilang dari `seq`.
4. Selesaikan API final dan ekspor CSV (Bagian 5.7).
5. **systemd:** dua service (`worker` dan `web`) dengan `Restart=always`, berjalan setelah jaringan dan Mosquitto siap, aktif saat boot. Minta agent membuat file service dan **jelaskan tiap barisnya**.
6. **Backup:** salin `data/ews.db` berkala dengan perintah `.backup` milik `sqlite3` (aman walau file sedang ditulis) ke laptop atau flashdisk.
7. Log: `journalctl -u <nama-service> -f`.

**DoD Fase 4:**

- [ ] Cabut dan colok listrik Pi → semua service hidup sendiri, data masuk lagi tanpa perintah manual.
- [ ] Matikan ESP32 → dashboard OFFLINE dalam ≤ 5 detik; nyalakan lagi → pulih sendiri.
- [ ] Matikan lalu hidupkan Mosquitto → `worker` tersambung lagi sendiri.
- [ ] Hentikan paksa proses web atau worker → systemd menghidupkannya kembali.
- [ ] CSV hasil ekspor terbuka di Excel dengan kolom yang benar.
- [ ] 30 menit data nyata terekam tanpa lubang (cek `seq`).

**[BUKTI]:** screenshot `systemctl status`, potongan log saat ESP32 dimatikan/dihidupkan, contoh CSV, ukuran dan jumlah baris database.

**[JEBAKAN]:**

- *"database is locked"* → pastikan hanya satu penulis, mode WAL aktif, dan koneksi tidak dibiarkan terbuka lama.
- **Pi tidak punya baterai jam (RTC).** Tanpa internet, jam bisa salah setelah reboot dan semua `ts_ms` ikut salah. Cek `date` sebelum setiap sesi pengambilan data; sambungkan ke internet atau set jam manual.
- paho-mqtt 2.x: lupa `callback_api_version` → error saat membuat Client.
- Password Mosquitto salah → koneksi ditolak; periksa log (`journalctl -u mosquitto`).

**[TULIS]:** BAB III 3.7.2 (program Raspberry Pi), 3.7.3–3.7.4 (pengolahan data dan alur komunikasi Python), 3.9 (Perancangan Database: skema dari Bagian 5.6).

---

### Fase 5 — Dashboard Final, Tunnel, Uji 24 Jam, dan Demo (Minggu 7–8: 11 – 24 Des)

**Target:** dashboard rapi dan tahan uji, bisa dibuka dari internet, lolos uji 24 jam, dan skenario demo sudah dilatih.

**Langkah:**

1. Poles dashboard sesuai Bagian 6 (selesaikan semua *Must*, lalu *Should*).
2. Uji di HP (portrait) dan laptop. **Putuskan internet** dari router: dashboard harus tetap tampil (bukti aset lokal bekerja).
3. Jalankan dengan **waitress** (bukan server bawaan Flask) dan `debug` mati; jadikan service systemd.
4. **Cloudflare Tunnel:**
   - a. Pasang `cloudflared` untuk Linux **arm64** mengikuti dokumentasi resmi Cloudflare.
   - b. **Quick Tunnel** untuk demo: `cloudflared tunnel --url http://localhost:5000` → muncul URL acak `https://….trycloudflare.com`. Uji dari HP memakai **data seluler** (bukan Wi-Fi yang sama).
   - c. Butuh URL tetap? Buat akun Cloudflare + domain, lalu *remotely-managed tunnel* (berjalan sebagai service).
   - d. Opsional: dokumentasi Cloudflare terbaru menyebut opsi `--allowed-mail` untuk membatasi pengunjung lewat kode OTP email — baca dokumentasinya sebelum memakai.
   - e. **Hanya** port web (5000) yang di-tunnel. Jangan pernah mengekspos 1883 (MQTT) atau 22 (SSH) ke internet.
5. **Uji 24 jam nonstop** — catat: suhu (`vcgencmd measure_temp`), status throttling (`vcgencmd get_throttled` → harus `0x0`), RAM (`free -h`), ukuran database, jumlah baris vs target (1 Hz × 86.400 detik = 86.400 baris), dan jumlah putus-sambung MQTT.
6. **Ukur parameter keberhasilan 3.13:** error ketinggian dan debit (dari kalibrasi), akurasi klasifikasi, latensi (rekam layar + kejadian fisik, lalu hitung selisih waktu; latensi ≈ interval kirim + proses + interval polling), dan kelengkapan data Web IoT.
7. Latih **skrip demo** (Bagian 10) minimal dua kali dan rekam **video cadangan**.

**DoD Fase 5:**

- [ ] Semua fitur *Must* dan *Should* di Bagian 6.3 berfungsi.
- [ ] Dashboard terbuka lewat URL tunnel dari HP berdata seluler.
- [ ] Uji 24 jam selesai: tidak ada crash, `get_throttled` = `0x0`, kelengkapan data ≥ target yang Anda tetapkan.
- [ ] Tabel pengukuran parameter keberhasilan 3.13 terisi.
- [ ] Skrip demo berhasil dua kali berturut-turut; video cadangan tersimpan.

**[BUKTI]:** log uji 24 jam + grafik suhu, screenshot dashboard tiap level, foto/video skenario demo, tabel parameter keberhasilan.

**[JEBAKAN]:**

- Quick Tunnel: URL berganti tiap dijalankan, tanpa jaminan uptime, tanpa SSE, maksimal 200 permintaan bersamaan. Nyalakan 30 menit sebelum sidang dan uji; siapkan akses LAN sebagai cadangan.
- Raspberry Pi 4 yang berjalan 24 jam butuh **pendingin** (heatsink/kipas) dan adaptor **5 V / 3 A** asli. Ikon petir atau `get_throttled` ≠ `0x0` berarti kekurangan daya atau terlalu panas.
- Mematikan Pi dengan mencabut listrik bisa merusak kartu SD → pakai `sudo shutdown -h now`; **backup database sebelum sidang**.

**[TULIS]:** BAB III 3.8 (Perancangan Dashboard: wireframe dari Bagian 6), 3.12 (evaluasi), BAB IV (hasil dan pembahasan), BAB V.

---

### Minggu 9 — Penyangga (25 – 31 Des)

- Bekukan kode (`git tag final`); simpan salinan seluruh proyek + database + dokumen di dua tempat.
- Perbaiki temuan terakhir, selesaikan penulisan, cetak/jilid, latihan presentasi penuh (waktu dan tanya-jawab).
- **Jangan menambah fitur baru** di minggu ini.

---

## 8. Jebakan Lintas Fase

- **Ubah satu hal pada satu waktu.** Commit Git sebelum setiap eksperimen; bila rusak, kembali ke commit terakhir yang jalan.
- **Jangan melompat fase.** Hardware yang belum stabil membuat debugging fuzzy dan dashboard menyesatkan.
- **Daya Pi:** adaptor 5 V / 3 A. Daya kurang → crash acak dan data korup.
- **Kartu SD:** matikan dengan `sudo shutdown -h now`, jangan cabut listrik; backup `data/ews.db` rutin.
- **Waktu Pi:** tanpa RTC dan tanpa internet, jam bisa melenceng. Cek `date` sebelum merekam data.
- **Jaringan:** satu router/hotspot untuk laptop + Pi + ESP32; Wi-Fi 2,4 GHz; IP Pi tetap.
- **Keamanan:** hanya web (5000) yang boleh di-tunnel; MQTT dan SSH tetap di jaringan lokal; password MQTT di `.env`; jangan commit `.env`.
- **Satuan:** tulis satuan di nama variabel (`ketinggian_cm`, `debit_lpm`).
- **Percaya AI secukupnya:** jalankan dan baca error sendiri; minta agent "jelaskan baris ini" untuk bagian yang tidak Anda pahami — Anda yang akan ditanya penguji, bukan agent.

---

## 9. Bahan Penulisan BAB II dan BAB III

Bagian ini memakai berkas yang Anda unggah untuk mengisi subbab yang masih kosong: **2.1.2 Web Dashboard**, **2.1.3 Database**, **2.1.4 Komunikasi Data IoT** (melengkapi), serta kerangka **3.8** dan **3.9**. Ini **kerangka dan peta sumber**, bukan naskah jadi. Naskah akhir ditulis dengan kata-kata Anda sendiri.

> Nomor `[n]` di bagian ini mengacu ke **Daftar Pustaka di file Tabel Komparasi** (31 entri), bukan ke 11 entri di proposal. Nomor akhir akan berubah mengikuti urutan sitasi di naskah.

### 9.1 Aturan Pedoman yang Paling Sering Terlewat

- Times New Roman 12 pt, spasi 1,5, rata kiri-kanan; margin kiri 4 cm, kanan/atas/bawah 3 cm.
- Subbab maksimal 3 tingkat.
- **Tabel:** nomor + nama di **atas**, rata tengah, huruf awal tiap kata kapital. **Gambar:** nomor + nama di **bawah**. Nomor memuat nomor bab (Tabel 3.5, Gambar 2.2). Sumber (bila bukan olahan sendiri) ditulis di bawahnya, Times New Roman 10 pt; tambahkan "telah diolah kembali" bila diolah.
- Dalam narasi, kata Tabel/Gambar diawali huruf besar: "dapat dilihat pada Gambar 3.1".
- Huruf di dalam gambar/tabel **tidak boleh lebih kecil dari 10 pt** (ukuran sebenarnya) → screenshot dashboard harus terbaca saat dicetak.
- Sitasi IEEE: angka dalam kurung siku, penulis **bukan** bagian kalimat: "…dikembangkan [1]."
- Daftar pustaka: semua yang tercantum harus dirujuk di teks; nama penulis **lengkap** (tanpa "dkk."/"et al."); disarankan ≥ 70% terbit lima tahun terakhir.
- Persamaan: satu baris, indentasi 1,5 cm, nomor di kanan, mis. (3.1).

### 9.2 Kerangka Isi per Subbab

**2.1.2 Web Dashboard** (±1–1,5 halaman)

1. Definisi: dashboard = antarmuka visual yang merangkum data penting (angka, grafik, status) agar kondisi sistem terbaca sekilas; di penelitian ini menampilkan ketinggian, debit, nilai fuzzy, dan level bahaya.
2. Arsitektur web klien–server: browser (klien) meminta ke server (Flask di Raspberry Pi) lewat HTTP; server membalas halaman HTML dan data JSON lewat API.
3. Cara data diperbarui: *polling* (browser bertanya berkala) vs *push* (WebSocket/SSE) → alasan memilih polling: sederhana, andal, dan kompatibel dengan Cloudflare Quick Tunnel.
4. Pustaka: Flask (backend), Bootstrap (tata letak responsif), Chart.js (grafik) — satu kalimat fungsi masing-masing.
5. Batasan peran: hanya monitoring, tanpa remote control (sesuai Batasan Penelitian).
6. Gambar: diagram arsitektur klien–server (buat sendiri); wireframe dan screenshot menyusul di BAB III 3.8 dan BAB IV.

- *Rujukan dari daftar Anda:* [28] (sistem pemantauan debit + penyimpanan; tabel Anda mencatat "monitoring real-time dan penyimpanan data berjalan"), [14] (monitoring energi IoT berbasis web), [12] (pemantauan IoT laboratorium), [5]/[24] (stasiun cuaca IoT + MQTT + fuzzy). **Buka dan cek tiap paper:** kutip hanya bagian yang benar-benar membahas dashboard/web/penyimpanan.
- *Tambahan sumber resmi:* dokumentasi Flask, Chart.js, dan Bootstrap (kategori *online* di IEEE).

**2.1.3 Database** (±1–1,5 halaman)

1. Definisi basis data dan DBMS; model relasional (tabel, baris, kolom, kunci utama) dengan contoh `logs_sensor`.
2. Mengapa data sensor disimpan: riwayat untuk grafik, bahan evaluasi (MAE, RMSE, akurasi), dan bukti pengujian.
3. SQLite: basis data tertanam (*embedded*, tanpa server), satu file, tanpa konfigurasi, mendukung transaksi (ACID); mode WAL memungkinkan membaca saat sedang menulis.
4. Perbandingan singkat SQLite vs MySQL/MariaDB (tabel kecil: arsitektur, instalasi, sumber daya, penulis serentak) → alasan memilih SQLite: satu Pi, satu tabel, satu penulis, pengguna sedikit. Sebutkan keterbatasannya (satu penulis pada satu waktu).
5. Skema tabel (Tabel 3.x) dan perkiraan volume data (≈ 86.400 baris/hari pada 1 Hz).

- *Rujukan dari daftar Anda:* [28]; dan [23] — **hati-hati:** di proposal, Nasir & Jalil dikutip untuk kalimat "Database (MYSQL)". Cek apakah paper itu memang memakai MySQL; jika tidak, jangan dipakai untuk klaim tersebut.
- *Tambahan sumber resmi:* sqlite.org — "About SQLite" (`https://www.sqlite.org/about.html`), "Appropriate Uses For SQLite" (`https://www.sqlite.org/whentouse.html`), "Write-Ahead Logging" (`https://www.sqlite.org/wal.html`). Verifikasi alamat dan catat tanggal akses Anda sendiri.

**2.1.4 Komunikasi Data IoT** (melengkapi paragraf "Hybrid Dual-Output" yang sudah ada)

1. Dua jalur keluaran ESP32: Serial UART (kabel) → laptop (PLX-DAQ → Excel) untuk akuisisi dan dokumentasi data tanpa jaringan; Wi-Fi/MQTT → Raspberry Pi untuk pemrosesan real-time dan web.
2. MQTT: protokol *publish/subscribe* ringan; jelaskan broker, topic, payload, QoS dengan contoh dari penelitian Anda (`ews/wavetank/telemetry`).
3. Mosquitto sebagai broker di Pi; format data JSON (kontrak data → Tabel 3.x).
4. Cloudflare Tunnel: koneksi keluar dari Pi ke Cloudflare sehingga dashboard dapat diakses dari internet tanpa membuka port di router.
5. Gambar 2.2: perbaiki tulisan "Flash" → "Flask" dan samakan penyebutan database dengan teks.

- *Rujukan dari daftar Anda:* [5]/[24] (MQTT + fuzzy), [6] (monitoring IoT), [18] (konsep IoT; di proposal tercatat sebagai [9]).
- *Tambahan sumber resmi:* spesifikasi MQTT (mqtt.org / OASIS), dokumentasi Eclipse Mosquitto, dan dokumentasi Cloudflare Tunnel (halaman *Quick Tunnels*: `https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/`).

**3.8 Perancangan Dashboard dan 3.9 Perancangan Database:** ambil dari Bagian 6 (wireframe, perilaku, warna) dan Bagian 5.5–5.7 (kontrak data, skema, endpoint). Sajikan sebagai tabel "Daftar API" dan "Skema `logs_sensor`".

Contoh format IEEE untuk sumber online (ganti tanggal dengan tanggal akses Anda):

```
[n] Cloudflare, "Quick Tunnels," Cloudflare Docs. Accessed: <tanggal akses>. [Online]. Available: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
```

### 9.3 Temuan di Proposal yang Perlu Diperbaiki

1. **Abstract (Inggris)** masih berisi "Keywords: Rice," (sisa templat lama); abstrak dan kata kunci bahasa Indonesia masih kosong.
2. **Tabel 3.2:** baris HC-SR04 menulis "mempermudah segmentasi objek beras" → ganti: mengukur jarak ke permukaan air untuk menghitung ketinggian muka air. "Micro HMI to HMI" → "Micro HDMI to HDMI".
3. **Tabel 3.3:** "Arduino IDE — Model untuk deteksi objek beras" dan "Raspberry Pi OS — Melakukan pelabelan dataset (*bounding box*)" adalah sisa templat; "Pythone" → "Python"; fungsi "Web Dashboard" masih kosong. Tambahkan Mosquitto, SQLite, Flask, scikit-fuzzy, Bootstrap/Chart.js, dan cloudflared.
4. **MySQL vs SQLite** di 2.1 dan "Flash" di Gambar 2.2 (lihat Bagian 2, butir 2).
5. **Daftar Pustaka:** muncul kata berbahasa Catalan (*núm.*, *i*, *Accedit*, *En línia*, *Disponible a*) — kemungkinan dari pengaturan bahasa (*locale*) gaya sitasi di aplikasi referensi Anda; ubah ke English (US) atau Indonesia. Beberapa entri terbaca salah: [17] penulis tertulis "S. Siaga" (itu kata dari judul), [27] "M. L. C. D. Lml", [28] "J. Tera" (nama jurnal, bukan penulis) dengan judul terpotong, [30] teks abstrak ikut masuk judul, [21] dan [31] hanya nama berkas `.pdf`, serta [5] dan [24] adalah artikel yang sama. Pedoman melarang "et al."/"dkk." (ada di [16] dan [18]).
6. **Proporsi referensi lima tahun terakhir:** hitungan kasar saya ±16 dari 30 (≈ 53%) terbit 2021–2026, sedangkan Pedoman menyarankan 70%. Saat menambah rujukan untuk Dashboard/Database/MQTT, utamakan jurnal 2021–2026.
7. **Urutan daftar pustaka:** Pedoman menyebut "alfabetik" sekaligus format IEEE bernomor (urut kemunculan). Tanyakan pembimbing; defaultnya IEEE = urut kemunculan.
8. **Jadwal (Tabel 3.0.1):** teks menulis Januari–November 2026, sedangkan rencana kerja ini sampai 31 Desember 2026 → sesuaikan. Daftar Tabel masih berisi hyperlink ke jalur berkas lokal, dan nama berkas proposal masih memakai judul proyek lain → ganti nama dan hapus hyperlink.

---

## 10. Demo dan Bukti

### 10.1 Skrip Demo (±5–7 menit)

1. Tunjukkan diagram arsitektur (30 detik): sensor → ESP32 → MQTT → Pi (Fuzzy, SQLite, Flask) → Cloudflare → dashboard.
2. Buka dashboard di laptop (LAN) dan di HP lewat **data seluler** (URL tunnel) — bukti akses dari luar.
3. Kondisi awal air tenang → **AMAN** (hijau).
4. Naikkan debit pompa → ketinggian dan debit naik → **WASPADA / SIAGA**.
5. Nyalakan wave maker atau tuang air mendadak → grafik melonjak → **BAHAYA** (merah) dalam ≤ 2–3 detik.
6. Cabut ESP32 → muncul **OFFLINE / DATA TIDAK VALID** (bukan AMAN) → tunjukkan sifat *fail-safe*.
7. Buka tabel `logs_sensor` atau ekspor CSV → riwayat tercatat; sebut hasil uji 24 jam dan tabel akurasi.

### 10.2 Daftar Periksa Sebelum Sidang

- [ ] Adaptor 5 V / 3 A, kabel cadangan, power strip; Pi tidak panas; kartu SD sudah di-backup.
- [ ] Router/hotspot sendiri menyala; Pi berIP tetap; ESP32 tersambung.
- [ ] `cloudflared` dinyalakan 30 menit sebelumnya; URL dicatat; dicoba dari HP berdata seluler.
- [ ] Salinan `ews.db`, CSV, dan video cadangan ada di laptop **dan** flashdisk.
- [ ] Perlengkapan skenario fisik siap: air, pompa, wave maker, wadah ukur.
- [ ] Akses cadangan siap: `http://<IP-Pi>:5000` lewat LAN.

### 10.3 Pertanyaan Penguji yang Mungkin dan Jawaban Singkat

- **Kenapa fuzzy Mamdani?** Aturan IF–THEN mudah dibaca dan divalidasi dengan hitungan manual; cocok untuk mengklasifikasi level dari dua variabel fisik.
- **Kenapa centroid?** Menghasilkan satu nilai tegas yang memperhitungkan seluruh bentuk himpunan output; defuzzifikasi yang umum pada Mamdani.
- **Kenapa SQLite, bukan MySQL?** Satu Pi, satu tabel, satu penulis; tanpa service server sehingga lebih ringan dan mudah di-backup.
- **Kenapa MQTT?** Ringan, dan memisahkan ESP32 dari Pi — ESP32 cukup mengirim ke sebuah topic.
- **Kenapa polling, bukan WebSocket?** Cukup untuk pembaruan 2 detik, lebih sederhana, dan berjalan di Cloudflare Quick Tunnel.
- **Bagaimana jika sensor mati?** Data divalidasi; < 2 sensor valid → "DATA TIDAK VALID"; > 5 detik tanpa data → "OFFLINE"; sistem tidak pernah menampilkan AMAN.
- **Bagaimana akurasi dan latensinya?** Jawab dengan tabel hasil Fase 5 (parameter keberhasilan 3.13).
- **Apa keterbatasannya?** Skala laboratorium, dua parameter, bukan pengganti sistem resmi BMKG/BNPB (Batasan Penelitian).
- **Apakah aman diakses dari internet?** Hanya port web yang lewat tunnel; dashboard read-only; MQTT dan SSH tidak diekspos.

---

## 11. Kamus Mini

- **Broker MQTT** — kantor pos yang menerima dan meneruskan pesan.
- **Topic** — nama "kotak surat" tempat pesan ditaruh (mis. `ews/wavetank/telemetry`).
- **Payload** — isi surat: datanya sendiri (di sini berformat JSON).
- **JSON** — format teks untuk data terstruktur berupa pasangan nama–nilai.
- **Endpoint / API** — "loket" di server yang melayani satu jenis permintaan (mis. `/api/now`).
- **Polling** — browser bertanya berkala: "ada kabar baru?"
- **venv** — ruang kerja Python terpisah agar paket proyek tidak bentrok dengan sistem.
- **WAL** — mode SQLite yang membuat pembaca dan penulis tidak saling menunggu.
- **Service systemd** — program yang dijaga sistem: hidup saat boot, dihidupkan lagi saat mati.
- **Tunnel** — terowongan keluar dari Pi ke Cloudflare agar bisa diakses dari internet tanpa membuka port.
- **Universe (fuzzy)** — rentang nilai yang mungkin untuk satu variabel (mis. 0–40 cm).
- **Fungsi keanggotaan** — kurva (segitiga/trapesium) yang menyatakan seberapa "tinggi" atau "cepat" suatu nilai.
- **Centroid** — titik berat area gabungan output fuzzy; hasilnya satu angka tegas (*crisp*).
- **Walking skeleton** — versi tipis seluruh sistem yang sudah berjalan ujung ke ujung, lalu ditebalkan bertahap.
- **Fail-safe** — bila ada yang rusak, sistem jatuh ke kondisi yang jujur ("tidak valid"), bukan kondisi yang menyesatkan ("aman").
- **Smoke test** — tes cepat untuk memastikan tidak ada yang "berasap" setelah instalasi.

---

## Log Keputusan

Isi saat keputusan diambil; bahan penjelasan di BAB III.

| Tanggal | Keputusan | Hasil | Disetujui oleh |
|---------|-----------|-------|----------------|
| | Database: SQLite (bukan MySQL) | | |
| | Jumlah level: 3 atau 4 | | |
| | Agregasi 4 sensor: median atau rata-rata | | |
| | Pemetaan nilai fuzzy → level (ambang / keanggotaan tertinggi) | | |
| | Sumber *ground truth* untuk evaluasi 3.12 | | |

---

## Lampiran A. Prompt Siap Tempel untuk Fase 1

> **Konteks:** Baca `PROJECT_SPEC.md` (Bagian 3, 5, 6, dan Fase 1 di Bagian 7). Kita mengerjakan **Fase 1 langkah 5: kerangka mode simulasi**.
>
> **Tugas:** buat kerangka proyek yang berjalan di laptop Windows dan Raspberry Pi **tanpa MQTT dan tanpa hardware**: `config.py`, `db.py`, `sources.py` (simulator dengan 5 skenario di Bagian 5.3), `fuzzy_engine.py` (parameter *contoh*, ditandai jelas), `worker.py`, `app.py` (endpoint GET: `/`, `/api/now`, `/api/history`, `/health`), `templates/index.html`, dan `static/` (Bootstrap + Chart.js disimpan lokal di `static/vendor/`).
>
> **Batasan:** struktur flat Bagian 5.4; tanpa library di luar Bagian 4; semua angka di `config.py`; data tidak valid atau terlambat tidak boleh tampil "AMAN"; semua endpoint read-only.
>
> **Cara kerja:** (1) tulis rencana 5–8 baris dan daftar file, tunggu persetujuan saya; (2) buat file satu per satu dan jelaskan tiap file dalam 2–3 kalimat sederhana; (3) beri perintah menjalankan beserta hasil yang diharapkan; (4) jalankan sendiri dan laporkan hasil nyata.
>
> **Selesai bila:** butir dashboard di DoD Fase 1 terpenuhi.

Untuk fase lain, ganti "Fase 1 langkah 5: kerangka mode simulasi" dengan fase dan langkah yang sedang dikerjakan, misalnya "Fase 3 langkah 4–5: `fuzzy_engine.py` dengan parameter dari `config.py`".

*— Akhir dokumen —*
