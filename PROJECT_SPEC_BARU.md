# PROJECT_SPEC — Web Dashboard IoT untuk Sistem Peringatan Dini Gelombang Air

- **Judul TA:** Perancangan Sistem Fuzzy Logic untuk Klasifikasi Level Bahaya Kenaikan Gelombang Air pada Sistem Peringatan Dini Berbasis Raspberry Pi dan Web IoT
- **Penulis:** Deta Hata Maulana — Program Studi Rekayasa Instrumentasi dan Automasi, ITERA
- **Versi dokumen:** 1.1 — direvisi 4 November 2026 (Sensor Fusion)
- **Jendela kerja:** 30 Okt – 31 Des 2026 (9 minggu)
- **Dibuat dari:** proposal Anda (termasuk Gambar 2.2), project-spec awal, Pedoman Penulisan TA Prodi IA, Tabel Komparasi Jurnal, dan keputusan riset terbaru (Sensor Fusion)
- **Riwayat revisi:**
  - 1.0 — 30 Okt 2026: versi awal.
  - 1.1 — 4 Nov 2026: Sensor Fusion 4 sensor ultrasonik (input fuzzy dari Sensor 4, tinggi global, kecepatan gelombang); tinggi pasang 48,0 cm; himpunan BAHAYA *double trapezoid*; 9 aturan mitigasi tsunami; kontrak data dan skema database baru; laju baca ESP32 naik (≥ 5 Hz).

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
- Lampiran B. Prompt Migrasi ke Sensor Fusion

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

Sistem membaca **ketinggian muka air di empat titik** pada prototipe kanal gelombang (aquarium 100 × 40 × 40 cm) memakai 4 sensor ultrasonik HC-SR04, serta **debit air** memakai flowmeter YF-S201. **Sensor 1 (S1)** berada di sisi pembangkit gelombang dan **Sensor 4 (S4)** di sisi pesisir. Semua sensor dipasang **tepat 48,0 cm di atas dasar akuarium**, dan jarak S1 ke S4 adalah **75 cm**.

ESP32 mengumpulkan data. Raspberry Pi 4 mengolahnya, menghitung **level bahaya dengan Fuzzy Mamdani**, menyimpannya di **SQLite**, lalu menampilkannya di **web dashboard** yang bisa dibuka dari laptop atau HP — termasuk dari luar jaringan lokal lewat **Cloudflare Tunnel**.

### Sensor Fusion: tiga informasi dari empat sensor

Keempat sensor diolah **bersamaan** untuk menghasilkan tiga informasi yang berbeda:

| | Informasi | Sumber | Dipakai untuk | Disimpan dan ditampilkan |
|---|-----------|--------|---------------|--------------------------|
| **A** | **Tinggi pesisir** `tinggi_s4_cm` — input utama fuzzy | **Hanya Sensor 4** | Input tunggal variabel "Ketinggian Air" pada Fuzzy Engine. Alasan ilmiah: pantai adalah titik kritis efek *run-up* dan surut ekstrem tsunami. | Tabel `logs_sensor`; kartu dan grafik utama |
| **B** | **Tinggi global maket** `tinggi_global_cm` — volume air rerata | **Median atau rata-rata** keempat sensor | Memantau stabilitas volume total air maket secara makro (deteksi kebocoran atau luapan tangki). **Tidak** masuk fuzzy. | Tabel `logs_sensor`; kartu dan garis di grafik utama |
| **C** | **Kecepatan rerata gelombang** `kecepatan_cms` — variabel baru | Selisih waktu puncak gelombang (≥ 20 cm) saat melewati S1 (t_S1) lalu S4 (t_S4) | `v = 75 / (t_s4 - t_s1)` cm/s. **Tidak** masuk fuzzy. | Tabel `gelombang_event`; kartu dan grafik tren tersendiri |

Rumus konversi jarak pantul menjadi tinggi air dari dasar, berlaku untuk tiap sensor:

> **`ketinggian_cm = 48.0 - jarak_bacaan_sensor`**

Batasan penelitian Anda yang **tidak boleh dilanggar** saat membuat fitur:

- Dashboard hanya untuk **monitoring** (data sensor, grafik, status level). **Tidak ada remote control.**
- Fuzzy hanya memakai **dua input**: tinggi S4 dan debit air.
- Metode Mamdani, dijalankan terpusat di Raspberry Pi.
- Skala laboratorium; bukan pengganti peringatan resmi BMKG/BNPB → pasang *disclaimer* di footer dashboard.

---

## 2. Temuan dari Berkas Anda dan Keputusan yang Perlu Dikunci

Saya membaca proposal, project-spec awal, Pedoman, dan tabel jurnal Anda. Berikut hal-hal yang mengubah rancangan dibanding project-spec awal:

| # | Temuan | Dampak | Keputusan di dokumen ini |
|---|--------|--------|--------------------------|
| 1 | Gambar 2.2 proposal: sensor → **ESP32** → Wi-Fi/MQTT → Raspberry Pi (*Broker & Engine*) → Fuzzy Mamdani + **SQLite** + Flask → Cloudflare Tunnel → dashboard global. Project-spec awal mengasumsikan sensor langsung ke GPIO Pi. | Pi **tidak** membaca GPIO (paket `RPi.GPIO` tidak dipakai); Pi butuh **broker MQTT**; ada tahap firmware ESP32. | Ikuti Gambar 2.2. |
| 2 | Teks BAB II 2.1 menulis database **MySQL**, sedangkan Gambar 2.2 menulis **SQLite**. | Dua bagian proposal saling bertentangan. Di repositori Raspberry Pi OS, server yang lazim tersedia adalah MariaDB (kompatibel MySQL) yang butuh service server tersendiri. | **SQLite**. Ubah kata "MySQL" di 2.1. **[PUTUSKAN]** konfirmasi pembimbing. |
| 3 | Jumlah level: project-spec awal 4 (Aman/Waspada/Siaga/Bahaya); contoh evaluasi di proposal 3.12 hanya 3 (Aman/Waspada/Bahaya). | Mengubah himpunan output fuzzy, tabel aturan, warna, dan confusion matrix. | **Terkunci: 4 level** (K7 di bawah). Contoh 3 level di proposal 3.12 perlu disesuaikan menjadi 4. |
| 4 | Prompt awal Anda menulis mulai **30-10-2025**, sedangkan tahun berjalan 2026. | Jadwal. | Jadwal memakai **2026**. Koreksi bila maksud Anda berbeda. |
| 5 | Project-spec awal menyimpan data tiap 5–10 detik. | Terlalu lambat untuk menangkap lonjakan gelombang (skenario demo "tuang air mendadak") dan untuk mengukur kecepatan gelombang. | ESP32 mengirim **1 pesan per siklus baca 4 sensor (target ≥ 5 Hz)**; database menyimpan **1 baris/detik**. Lihat "Dampak Teknis" di bawah. |
| 6 | ESP32 punya dua keluaran: Serial → laptop (PLX-DAQ → Excel) dan Wi-Fi/MQTT → Pi. | Jalur Serial bukan bagian dashboard; ia dipakai untuk dataset dan kalibrasi. | Dipertahankan; dikerjakan di Fase 2. |
| 7 | Router lab/kampus bisa tanpa internet atau memisahkan perangkat satu sama lain. | Bootstrap/Chart.js dari CDN gagal dimuat; ESP32 tak bisa menjangkau Pi. | Semua file front-end disimpan **lokal**; pakai router/hotspot milik sendiri. |
| 8 | Cloudflare Quick Tunnel (dokumentasi resmi): tidak mendukung SSE, maksimal 200 permintaan bersamaan, URL acak berganti tiap dijalankan, tanpa jaminan uptime. | Memengaruhi cara dashboard memperbarui data dan rencana demo. | Dashboard memakai **polling 2 detik**; siapkan cadangan akses LAN. |
| 9 | Saya menguji scikit-fuzzy 0.5.0 (dengan numpy 2.5): `pip install scikit-fuzzy` **tidak** ikut memasang numpy, scipy, networkx, dan packaging; saat menghitung juga muncul *DeprecationWarning* dari numpy. | `import skfuzzy` langsung error pada instalasi baru; versi numpy yang jauh lebih baru kelak bisa merusak library. | Pasang semuanya eksplisit, **kunci versi lewat `requirements.txt`** (jangan upgrade numpy setelah semuanya jalan), dan siapkan rencana cadangan (Mamdani manual dengan NumPy). |

### Keputusan Riset Terbaru (Revisi 1.1 — Sensor Fusion): TERKUNCI

Ini keputusan penelitian Anda. Dokumen ini dan AI agent **tidak boleh mengubahnya** tanpa persetujuan Anda/pembimbing (lihat Aturan untuk AI Agent #17).

| # | Keputusan | Nilai / aturan |
|---|-----------|----------------|
| K1 | Input utama fuzzy "Ketinggian Air" | **Sensor 4 saja** (`tinggi_s4_cm`) |
| K2 | Agregasi global maket | Median **atau** rata-rata S1–S4 → `tinggi_global_cm`; tidak masuk fuzzy |
| K3 | Variabel baru | Kecepatan rerata gelombang `v = 75 / (t_s4 - t_s1)` cm/s, untuk puncak gelombang ≥ 20 cm |
| K4 | Tinggi pasang sensor | Semua sensor **tepat 48,0 cm** dari dasar akuarium |
| K5 | Konversi jarak → tinggi | `ketinggian_cm = 48.0 - jarak_bacaan_sensor` |
| K6 | Jarak S1 ke S4 | 75 cm |
| K7 | Output fuzzy | 4 level tegas: AMAN, WASPADA, SIAGA, BAHAYA |
| K8 | Himpunan Ketinggian S4 | BAHAYA = *double trapezoid* (surut ekstrem < 11 cm **dan** luapan ekstrem > 22 cm); AMAN = trapesium di sekitar air tenang maket; WASPADA = segitiga |
| K9 | Basis aturan | 9 aturan mitigasi tsunami (Bagian 7, Fase 3) |

Masih **terbuka** (catat di Log Keputusan): median atau rata-rata untuk K2; titik-titik himpunan keanggotaan (angka di dokumen ini hanya CONTOH); sumber *ground truth* evaluasi; SQLite vs MySQL.

### Dampak Teknis Revisi Ini (hasil analisis dan uji saya)

1. **Laju baca harus naik.** Kecepatan butuh selisih waktu puncak S1 → S4, dan puncak gelombang pendek (±0,7 s) bisa lolos di antara dua sampel. Dengan 1 pesan/detik (spesifikasi lama), kecepatan praktis tidak bisa diukur — lihat tabel simulasi di bawah. Maka ESP32 kini mengirim **1 pesan per siklus baca** (target ≥ 5 Hz) yang berisi **waktu tiap sensor**; database tetap 1 baris/detik.
2. **Perkiraan fisika.** Untuk gelombang panjang di air dangkal, laju ≈ √(g·h) ≈ 120 cm/s pada h ≈ 15 cm, sehingga gelombang melewati 75 cm hanya dalam ≈ 0,6 s. Ini hitungan teori kasar; **bandingkan dengan video** (Fase 2).
3. **S4 menjadi titik tunggal kegagalan fuzzy.** Bila S4 tidak valid → level TIDAK_VALID, **tanpa** *fallback* diam-diam ke sensor lain. Karena itu S4 dikalibrasi paling teliti dan persentase bacaan gagalnya dicatat.
4. **BAHAYA tunggal untuk dua anomali.** Surut ekstrem dan luapan ekstrem sama-sama menghasilkan keanggotaan BAHAYA, sehingga aturan R7–R9 tidak membedakan arahnya (pada uji saya, S4 = 8 cm dan S4 = 25 cm menghasilkan keluaran identik). Dashboard boleh menambahkan label arah (SURUT/LUAPAN) dari nilai S4 — hanya tampilan, fuzzy tidak berubah.
5. **Kecepatan adalah kejadian, bukan deret 1 Hz.** Nilainya hanya ada bila puncak ≥ 20 cm (≥ 5 cm di atas air tenang ≈ 15 cm) melewati S1 lalu S4. Karena itu disimpan di tabel terpisah `gelombang_event`.
6. **Tafsir "±15 cm".** Saya menafsirkan "air tenang maket (±15 cm)" sebagai level air tenang ≈ 15 cm. Bila maksud Anda lain, titik himpunan AMAN di Fase 3 harus digeser. **[PUTUSKAN]** setelah mengukur level air tenang sebenarnya.

**Simulasi kasar kecepatan gelombang** (bukan data Anda): pulsa gelombang berdurasi ≈ 0,7 s, puncak 23 cm di atas air tenang 15 cm, kecepatan sebenarnya 60–120 cm/s, noise sensor 0,3–0,6 cm, estimasi puncak sub-sampel dengan cap waktu **per sensor**:

| Siklus baca 4 sensor | Puncak yang gagal terdeteksi | Galat rata-rata kecepatan |
|----------------------|------------------------------|---------------------------|
| 1 Hz (spesifikasi lama) | ≈ 44–83% | tidak layak dipakai |
| 2 Hz | ≈ 0–1% | ≈ 5–14% |
| 5 Hz | 0% | ≈ 2–7% |
| 10 Hz | 0% | ≈ 1–4% |

Bila waktu dicap **per pesan** (S4 dianggap dibaca bersamaan dengan S1), galat pada 5 Hz naik menjadi ≈ 14–32%. Karena itu `t_ms` per sensor wajib ada di kontrak data (Bagian 5.5).

> Pengujian saya dilakukan di Linux x86 (Python 3.12, numpy 2.5): sistem Mamdani 2 input + centroid dengan himpunan dan 9 aturan baru (Fase 3) berjalan dan sangat cepat, begitu pula simulasi kecepatan gelombang di atas. Semua pustaka yang direkomendasikan murni-Python atau punya paket ARM64, tetapi **hardware Pi dan ESP32 Anda belum saya uji** — karena itu Fase 1 memuat *smoke test* di Pi dan Fase 2 memuat uji laju baca.

---

## 3. Aturan untuk AI Agent

Bagian ini ditujukan untuk AI agent di Antigravity/VS Code. Anda sebagai pemula juga sebaiknya membacanya: ini pagar pengaman supaya proyek tidak melebar.

1. Jawab dan beri komentar kode dalam **Bahasa Indonesia sederhana**. Istilah teknis diberi analogi singkat saat pertama muncul.
2. Mulai dengan **rencana 5–8 baris + daftar file** yang akan dibuat/diubah. **Tunggu persetujuan** sebelum menulis kode.
3. Kerjakan **satu fase, satu langkah kecil** per sesi. Jangan mengerjakan fase berikutnya.
4. Pakai **hanya stack di Bagian 4**. Menambah library/framework wajib bertanya dulu dan menjelaskan alasannya.
5. Ikuti **struktur folder flat** di Bagian 5.4. Dilarang: microservices, Docker/Kubernetes, ORM, framework frontend dengan build tools.
6. Semua angka penting (topik MQTT, interval, batas validasi, kalibrasi, parameter fuzzy, ambang level, warna) hanya ada di `config.py`, tidak ditulis ulang di tempat lain.
7. `fuzzy_engine.py` dan `wave_speed.py` berisi **fungsi murni**: angka masuk → hasil keluar (fuzzy: nilai + level; wave_speed: waktu puncak, Δt, kecepatan). Tidak ada akses database atau MQTT di dalamnya, supaya mudah dites dan dibandingkan dengan hitungan manual.
8. Semua endpoint web **GET dan read-only**. Dilarang membuat endpoint atau tombol yang mengendalikan perangkat (Batasan Penelitian).
9. **Fail-safe:** data tidak valid atau terlambat **tidak boleh** tampil sebagai "AMAN". Tampilkan "DATA TIDAK VALID" atau "OFFLINE" (abu-abu).
10. **Validasi input sebelum fuzzy** (rentang, NaN, S4 valid, debit valid), lalu batasi (*clamp*) ke rentang universe fuzzy.
11. Tidak ada rahasia (password MQTT, token Cloudflare) di kode atau Git. Pakai `.env` atau variabel lingkungan; `.env` masuk `.gitignore`.
12. Setelah menulis kode, berikan **perintah tes dan hasil yang diharapkan**, jalankan sendiri bila bisa, lalu laporkan hasil nyata. Jangan menulis "sudah berfungsi" tanpa menjalankannya.
13. Jangan merapikan atau mengubah file lain yang tidak diminta.
14. Target: Raspberry Pi 4 (ARM64), Python 3.11–3.13, dan laptop Windows. Hindari paket yang butuh kompilasi lama atau hanya jalan di satu OS.
15. Bila spesifikasi ambigu → **tanya**. Jangan menebak angka (rentang universe, ambang level); beri contoh dan tandai `# CONTOH — GANTI DENGAN DATA ANDA`.
16. Bila dokumen ini bertentangan dengan proposal → **laporkan**, jangan memilih diam-diam.
17. **Keputusan riset terkunci (Bagian 2, K1–K9):** input fuzzy hanya `tinggi_s4_cm` dan `debit_lpm`; tinggi pasang 48,0 cm; jarak S1–S4 75,0 cm; ambang puncak 20 cm; 4 level; 9 aturan; himpunan BAHAYA *double trapezoid*. Konstanta ada di `config.py`. Jangan diubah atau "diperbaiki" tanpa persetujuan saya.
18. **Fail-safe S4:** `tinggi_s4_cm` tidak valid → level `TIDAK_VALID`. Dilarang memakai sensor lain sebagai pengganti secara diam-diam. Tinggi global dan kecepatan gelombang **tidak boleh** memengaruhi fuzzy.
19. **Kecepatan gelombang** dihitung dari **cap waktu per sensor dari ESP32** (`t_ms`), bukan dari waktu terima pesan di Pi; waktu puncak diestimasi sub-sampel. Tolak pasangan puncak dengan Δt ≤ 0 atau di luar jendela `DT_MAKS_S`.
20. Fuzzy Engine dibuat **sekali**. Himpunan BAHAYA dibentuk dari gabungan (max) dua trapesium. Seluruh universe harus tertutup oleh himpunan (tanpa celah), dan pembacaan hasil dibungkus penanganan error.

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
 [S1 pembangkit]--\
 [S2]--------------+--> [ESP32] --(1) Serial/kabel--> [Laptop: PLX-DAQ -> Excel]
 [S3]--------------+       |                          (dataset & kalibrasi)
 [S4 pesisir]-----/        | (2) Wi-Fi 2,4 GHz + MQTT
 [YF-S201 debit]--/        |     1 pesan per siklus baca (>= 5 Hz)
                           v
 +---------------------- Raspberry Pi 4 Model B ---------------------+
 |  Mosquitto (broker)                                               |
 |      | subscribe                                                  |
 |      v                                                            |
 |  worker.py : validasi -> tinggi tiap sensor = 48,0 - jarak        |
 |      |-- (A) tinggi S4 + debit -> Fuzzy Mamdani -> level          |
 |      |-- (B) median/rata-rata S1..S4 -> tinggi global             |
 |      '-- (C) puncak >= 20 cm lewat S1 lalu S4 -> v = 75 / dt      |
 |      v INSERT: 1 baris/detik + 1 baris tiap kejadian gelombang    |
 |  SQLite (data/ews.db, mode WAL)                                   |
 |      ^ SELECT                                                     |
 |  app.py (Flask) : halaman HTML + API JSON (GET), port 5000        |
 +---------+-------------------------------+-------------------------+
           | LAN                           | cloudflared (tunnel keluar)
           v                               v
   Browser di jaringan sama        https://xxxx.trycloudflare.com
   http://<IP-Pi>:5000             -> browser dari internet
```

Gambar 2.2 di proposal belum menunjukkan S1–S4 dan tiga pengolahan (A, B, C). Perbarui gambar itu agar sama dengan diagram ini.

### 5.2 Peran Tiap Blok (analogi)

- **Sensor (S1–S4, YF-S201)** = mata dan meteran: empat "mata" di sepanjang maket mengukur jarak ke permukaan air; satu meteran mengukur aliran air.
- **ESP32** = kurir: membaca keempat sensor bergantian secepat yang aman, mencatat jam tiap pembacaan, lalu mengirimkannya.
- **Mosquitto** = kantor pos: menerima kiriman dan meneruskannya ke yang berlangganan.
- **worker.py** = juru hitung: memeriksa data, mengubah jarak jadi tinggi, lalu menjalankan tiga pengolahan — (A) fuzzy dari S4, (B) tinggi global, (C) kecepatan gelombang — dan mencatat hasilnya ke buku.
- **SQLite** = buku besar: satu buku harian (`logs_sensor`) dan satu buku kejadian gelombang (`gelombang_event`).
- **app.py (Flask)** = pelayan/etalase: menyajikan halaman dan data kepada pengunjung.
- **Browser** = pelanggan.
- **Cloudflare Tunnel** = pintu belakang yang aman: pelanggan dari luar bisa masuk tanpa membuka pintu depan (port) rumah Anda.

### 5.3 Dua Proses dan Mode Simulasi

- **Dua proses terpisah** di Pi: `worker.py` (menulis data) dan `app.py` (menyajikan web). Keduanya hanya "bertemu" lewat file SQLite. Analogi: dapur dan pelayan — pelayan boleh ganti shift tanpa dapur berhenti memasak. Jika web error, pencatatan data tetap jalan (penting untuk uji 24 jam).
- **Mode simulasi** adalah kunci kecepatan pengerjaan. Di `config.py` ada pilihan sumber data: `sim` (data palsu buatan program) atau `mqtt` (data nyata dari ESP32). Dengan `sim`, dashboard, fuzzy, dan perhitungan kecepatan bisa dikerjakan di laptop **tanpa menunggu hardware**.
- Simulator menghasilkan data **berbentuk persis seperti ESP32 sungguhan**: 4 jarak + `t_ms` per sensor + debit. Minimal ada 8 skenario:

| Skenario | Perilaku | Hasil yang diharapkan |
|----------|----------|-----------------------|
| `tenang` | S1–S4 ≈ 15 cm (noise kecil), debit rendah | AMAN (R1); tinggi global ≈ 15 cm; tanpa kejadian gelombang |
| `naik_perlahan` | tinggi S4 naik bertahap ±15 → 21 cm, debit naik pelan | AMAN → WASPADA → SIAGA |
| `surut_ekstrem` | tinggi S4 turun di bawah 11 cm; debit rendah → sedang | SIAGA (R7) → BAHAYA (R8) |
| `luapan_ekstrem` | tinggi S4 di atas 22 cm; debit sedang → tinggi | BAHAYA (R8/R9) |
| `gelombang_lewat` | puncak ≥ 20 cm bergerak S1 → S4 dengan v ≈ 100 cm/s (Δt ≈ 0,75 s) | 1 baris `gelombang_event` dengan v ≈ 100 cm/s |
| `gelombang_noise` | osilasi kecil (puncak < 20 cm) + noise | tanpa kejadian gelombang; level tidak berkedip liar |
| `sensor_error` | S4 `null` beberapa detik; sensor lain `null` acak | S4 null → TIDAK_VALID; tinggi global NULL bila < 2 sensor valid |
| `kebocoran_pelan` (*Should*) | keempat sensor turun pelan | badge stabilitas tinggi global → TURUN |

Simulator yang sama dipakai tes otomatis `wave_speed` (gelombang sintetis dengan kecepatan yang diketahui).

### 5.4 Struktur Folder (flat, sengaja sederhana)

```
ews-gelombang/
├── PROJECT_SPEC.md          <- file ini
├── AGENTS.md                <- (opsional) 3-5 baris yang menunjuk ke file ini
├── requirements.txt
├── .gitignore               <- .venv/, data/*.db, .env
├── .env                     <- rahasia (password MQTT); JANGAN di-commit
├── config.py                <- SEMUA angka & nama penting (48,0 / 75,0 / 20 / ambang / warna)
├── fuzzy_engine.py          <- fuzzy Mamdani: fungsi murni
├── wave_speed.py            <- deteksi puncak S1/S4 & kecepatan: fungsi murni
├── db.py                    <- fungsi SQLite (dipakai worker & app)
├── sources.py               <- sumber data: simulator, MQTT
├── worker.py                <- PROSES 1: ambil -> validasi -> tinggi -> A/B/C -> simpan
├── app.py                   <- PROSES 2: Flask (halaman + API GET)
├── templates/index.html     <- halaman dashboard
├── static/
│   ├── css/app.css
│   ├── js/app.js
│   └── vendor/              <- bootstrap & chart.js (unduh sekali, simpan lokal)
├── firmware/esp32_ews/      <- sketch Arduino (.ino)
├── deploy/                  <- contoh service systemd, catatan mosquitto & cloudflared
├── tests/                   <- tes kecil (fuzzy vs hitungan manual, wave_speed sintetis, validasi payload)
├── data/                    <- ews.db, hasil ekspor, backup (tidak di-commit)
└── docs/                    <- screenshot, foto, tabel uji (bukti BAB III–IV)
```

### 5.5 Kontrak Data ESP32 → Raspberry Pi (MQTT)

"Kontrak" = kesepakatan format data supaya sisi ESP32 dan sisi Pi bisa dikerjakan terpisah tanpa saling menebak. **Jangan diubah sepihak.**

**Posisi fisik dan konstanta terkunci** (semuanya hanya ada di `config.py`):

| Konstanta | Nilai | Arti |
|-----------|-------|------|
| `TINGGI_PASANG_CM` | 48.0 | Semua sensor tepat 48,0 cm di atas dasar akuarium |
| `JARAK_S1_S4_CM` | 75.0 | Jarak S1 ke S4 searah panjang maket (ukur ulang jarak pusat-ke-pusat yang sebenarnya) |
| `AMBANG_PUNCAK_CM` | 20.0 | Tinggi minimum puncak gelombang yang dihitung |
| `INDEKS_S4` | 3 | `us_cm[3]` = Sensor 4 (pesisir) = input fuzzy |

Urutan fisik: `us_cm[0]` = S1 (sisi pembangkit gelombang) … `us_cm[3]` = S4 (sisi pesisir). Posisi S2 dan S3 di antaranya dicatat di `config.py` tetapi tidak dipakai pada rumus kecepatan.

- **Broker:** `<IP atau hostname Pi>:1883` (Mosquitto, memakai user dan password).
- **Topic telemetri:** `ews/wavetank/telemetry` — QoS 0. **Satu pesan per siklus baca 4 sensor** (target ≥ 5 Hz; alasannya di Bagian 2, "Dampak Teknis" #1).
- **Topic status:** `ews/wavetank/status` — berisi `online` (retained) saat ESP32 tersambung. *Last Will* ("pesan wasiat" yang dikirim broker atas nama ESP32) otomatis mengubahnya jadi `offline` bila ESP32 mati mendadak.
- **Payload telemetri** (JSON satu baris; contoh air tenang ≈ 15 cm):

```
{"seq":10240,"t_ms":[512000,512030,512060,512090],"us_cm":[32.8,32.9,32.7,32.6],"flow_lpm":8.6}
```

| Field | Arti | Aturan |
|-------|------|--------|
| `seq` | Nomor urut pesan, naik 1 tiap kirim | Pi mendeteksi pesan hilang |
| `t_ms` | **4 waktu pembacaan, satu per sensor** (milidetik sejak ESP32 menyala; indeks sama dengan `us_cm`) | Dasar Δt kecepatan gelombang. **Bukan** waktu terima di Pi (Wi-Fi berjitter) |
| `us_cm` | 4 jarak sensor → permukaan air (cm) | `null` bila gagal baca atau di luar rentang |
| `flow_lpm` | Debit (L/menit) dengan faktor awal datasheet | Dikalibrasi lagi di Pi |

Contoh hitungan: jarak 32,8 cm → tinggi = 48,0 − 32,8 = 15,2 cm.

**Pembagian tugas:**

- **ESP32:** membaca 4 sensor **bergantian** secepat yang aman (jeda antar sensor mulai ±30 ms; naikkan bila terjadi *crosstalk*), mencatat `t_ms` tiap sensor saat pembacaannya selesai, menolak bacaan di luar rentang (→ `null`), lalu mengirim. ESP32 **tidak** menghitung tinggi, fuzzy, maupun kecepatan.
- **Raspberry Pi:** validasi → konversi jarak ke tinggi → tiga pengolahan (A, B, C) → simpan. Semua konstanta ada di `config.py`, sehingga **tidak perlu flash ulang ESP32** setiap kali kalibrasi atau konstanta berubah.

**Aturan pengolahan di Pi** (angkanya di `config.py`):

1. Payload bukan JSON, field hilang, atau panjang larik ≠ 4 → buang dan catat di log.
2. Jarak satu sensor valid bila `JARAK_MIN_CM` (2.0, zona buta HC-SR04) ≤ jarak ≤ `TINGGI_PASANG_CM` (48.0); selain itu dianggap tidak valid.
3. Untuk tiap sensor valid: koreksi kalibrasi per sensor (`a·jarak + b`; bawaan a = 1, b = 0), lalu **`ketinggian_cm = 48.0 - jarak_bacaan_sensor`**.
4. **(A) Input fuzzy.** `tinggi_s4_cm` = median `S4_MEDIAN_N` (bawaan 3) pembacaan S4 terakhir, dibatasi ke 0–40 cm. S4 tidak valid **atau** debit tidak valid → `sensor_ok = 0` dan level `TIDAK_VALID` (tanpa *fallback* ke sensor lain).
5. **(B) Tinggi global.** Median **atau** rata-rata (`AGREGASI_GLOBAL`) dari `ketinggian_cm` semua sensor valid pada siklus yang sama; butuh minimal `MIN_SENSOR_VALID` (2) sensor, jika kurang → NULL (tidak memengaruhi fuzzy). **[PUTUSKAN]** bawaan median (tahan terhadap satu sensor yang meleset); rata-rata lebih dekat ke makna "volume" tetapi lebih peka terhadap sensor yang meleset. Tulis pilihan Anda di BAB III.
6. **(C) Kecepatan gelombang**, dari aliran cepat `ketinggian_1(t)` dan `ketinggian_4(t)`:
   - a. Puncak = maksimum lokal yang ≥ `AMBANG_PUNCAK_CM` (20), dengan histeresis (mis. 2 cm). Waktu puncak diestimasi **sub-sampel** (parabola dari beberapa sampel dalam ±0,3 s di sekitar maksimum) memakai `t_ms` sensor itu sendiri.
   - b. Pasangkan puncak S4 dengan puncak S1 terdekat sebelumnya dalam jendela `DT_MAKS_S`; tolak bila Δt ≤ 0.
   - c. **`v = 75.0 / dt_detik`** dengan `dt_detik = (t_s4 - t_s1) / 1000` (cm/s). Contoh: Δt = 0,75 s → v = 100 cm/s.
   - d. Tolak v di luar rentang masuk akal (`V_MIN_CMS`–`V_MAKS_CMS`, CONTOH 15–300 cm/s) → simpan dengan `valid = 0`.
7. Tidak ada pesan baru lebih dari `STALE_AFTER_S` (bawaan 5 detik) → dashboard menampilkan OFFLINE.
8. **Pencatatan:** 1 baris `logs_sensor` per `LOG_INTERVAL_S` (bawaan 1 detik) berisi nilai terbaru; setiap kejadian gelombang langsung menjadi 1 baris `gelombang_event`.

### 5.6 Skema Database

Dua tabel utama: `logs_sensor` (deret waktu 1 Hz) dan `gelombang_event` (satu baris per kejadian gelombang).

**Tabel `logs_sensor`**

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id` | INTEGER, primary key | otomatis |
| `ts_ms` | INTEGER | waktu terima di Pi (epoch UTC, milidetik). **Beri index.** |
| `seq` | INTEGER | nomor urut dari ESP32 |
| `us1_cm` … `us4_cm` | REAL | jarak tersaring tiap sensor (cm); NULL bila tidak valid. `us4_cm` = S4 |
| `n_valid` | INTEGER | jumlah sensor valid (0–4) |
| **`tinggi_s4_cm`** | REAL | **BARU** — input fuzzy (A): `48.0 - jarak S4` setelah median dan pembatasan; NULL bila S4 tidak valid |
| **`tinggi_global_cm`** | REAL | **BARU** — agregasi global (B): median/rata-rata S1–S4; NULL bila < 2 sensor valid |
| `debit_lpm` | REAL | hasil kalibrasi |
| `nilai_fuzzy` | REAL | 0–100; NULL bila tidak valid |
| `level` | TEXT | AMAN / WASPADA / SIAGA / BAHAYA / TIDAK_VALID |
| `level_id` | INTEGER | 0–3; NULL bila tidak valid |
| `sensor_ok` | INTEGER | 1 bila **S4 dan debit** valid (syarat fuzzy), selain itu 0 |
| `sumber` | TEXT | `sim` atau `mqtt` |

Kolom lama `ketinggian_cm` (versi 1.0) **digantikan** oleh `tinggi_s4_cm` dan `tinggi_global_cm`.

**Tabel `gelombang_event`** (BARU)

| Kolom | Tipe | Keterangan |
|-------|------|------------|
| `id` | INTEGER, primary key | otomatis |
| `ts_ms` | INTEGER | waktu Pi mencatat kejadian (epoch UTC, ms). **Beri index.** |
| `t_s1_ms` | INTEGER | waktu puncak di S1 (ms, jam ESP32) |
| `t_s4_ms` | INTEGER | waktu puncak di S4 (ms, jam ESP32) |
| `dt_ms` | INTEGER | `t_s4_ms - t_s1_ms` |
| `puncak_s1_cm` | REAL | tinggi puncak di S1 |
| `puncak_s4_cm` | REAL | tinggi puncak di S4 |
| `jarak_s1_s4_cm` | REAL | jarak yang dipakai (75.0); disimpan supaya hitungan tetap bisa ditelusuri bila konstanta berubah |
| **`kecepatan_cms`** | REAL | **BARU** — `jarak_s1_s4_cm / (dt_ms / 1000)` |
| `valid` | INTEGER | 1 = lolos pemeriksaan; 0 = ditolak (disimpan untuk audit) |
| `sumber` | TEXT | `sim` atau `mqtt` |

- **Mengapa kecepatan di tabel terpisah?** Kecepatan hanya terdefinisi saat ada puncak ≥ 20 cm yang melewati S1 lalu S4 (kejadian, bukan deret 1 Hz). Kolomnya di `logs_sensor` akan hampir selalu NULL dan sulit divisualisasikan. Bila Anda tetap ingin satu tabel datar, tambahkan kolom `kecepatan_cms` (nullable) ke `logs_sensor` dan isi hanya pada baris yang bersangkutan.
- Jarak mentah per sensor **sengaja ikut disimpan**: itu bukti untuk validasi sensor dan perhitungan MAE/RMSE (3.10.6, 3.12).
- Tabel opsional `events` (*Should*): satu baris tiap level berubah (`id, ts_ms, level_dari, level_ke, nilai_fuzzy`) untuk panel riwayat dan ukuran waktu-tanggap.
- Aktifkan **mode WAL** (`PRAGMA journal_mode=WAL`): pembaca (web) dan penulis (worker) tidak saling memblokir. Hanya **satu penulis** (worker).
- Simpan waktu dalam UTC; tampilkan WIB (UTC+7) di dashboard.
- Perkiraan kasar: 1 baris/detik ≈ 86.400 baris/hari ≈ 10 MB/hari untuk `logs_sensor` — cukup untuk uji 24 jam. `gelombang_event` hanya bertambah saat ada gelombang.
- Bila Anda sudah punya `ews.db` berskema lama (isinya data uji simulasi), hapus lalu buat ulang, atau minta agent menulis skrip migrasi (`ALTER TABLE … ADD COLUMN`).

### 5.7 Endpoint API (semua GET, read-only)

| Endpoint | Isi |
|----------|-----|
| `/` | halaman dashboard |
| `/api/now` | data terbaru: `tinggi_s4_cm`, `tinggi_global_cm`, `debit_lpm`, `nilai_fuzzy`, `level`, `level_id`, `sensor_ok`, `n_valid`, `age_s` (umur data), `online`, serta `kecepatan_terakhir_cms` dan `kecepatan_terakhir_ts_ms` (kejadian gelombang valid terakhir; `null` bila belum ada) |
| `/api/history?limit=120` | N titik terakhir, urut waktu naik: `ts_ms`, `tinggi_s4_cm`, `tinggi_global_cm`, `debit_lpm`, `nilai_fuzzy`, `level_id`; server membatasi `limit` maksimum |
| `/api/history?minutes=30` | rentang waktu; diperkecil (*downsample*) di server bila terlalu banyak titik |
| `/api/gelombang?limit=50` | **BARU** — kejadian gelombang valid terakhir untuk grafik tren kecepatan: `ts_ms`, `kecepatan_cms`, `dt_ms`, `puncak_s1_cm`, `puncak_s4_cm` |
| `/api/events?limit=10` | perubahan level terakhir |
| `/api/export.csv?from=…&to=…` | unduh CSV `logs_sensor` (epoch ms) untuk dihitung di Excel (MAE, RMSE, confusion matrix) |
| `/api/export_gelombang.csv?from=…&to=…` | **BARU** — unduh CSV `gelombang_event` (untuk membandingkan kecepatan sensor vs video) |
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
| TINGGI S4      | DEBIT          | NILAI FUZZY    | STATUS BAHAYA     |
| 19,5 cm        | 12,0 L/mnt     | 65 / 100       | SIAGA             |
| (input fuzzy)  | maks: 12,6     | [#######---]   | (kartu oranye)    |
+----------------------------------+-----------------------------------+
| TINGGI GLOBAL (rerata maket)     | KECEPATAN GELOMBANG (terakhir)    |
| 15,3 cm   [STABIL]               | 98 cm/s   (dt 0,77 s)             |
| median S1-S4                     | 12 detik lalu                     |
+----------------------------------+-----------------------------------+
| GRAFIK UTAMA: tinggi S4 dan tinggi global (cm) + debit (L/mnt),      |
| 120 titik terakhir (dua sumbu Y)                                     |
+----------------------------------+-----------------------------------+
| Grafik nilai fuzzy (0-100)       | Grafik tren kecepatan gelombang   |
|                                  | (satu titik per kejadian)         |
+----------------------------------+-----------------------------------+
| Riwayat perubahan level (10 baris terakhir)                          |
+----------------------------------------------------------------------+
| [Jeda]  Rentang: [2 mnt] [30 mnt] [2 jam]  [Unduh CSV]               |
| Prototipe skala laboratorium - bukan pengganti peringatan BMKG/BNPB  |
+----------------------------------------------------------------------+
```

### 6.2 Perilaku yang Harus Ada

- **Pembaruan data:** browser memanggil `/api/now` setiap **2 detik** (*polling*: seperti menelepon tiap 2 detik untuk bertanya "ada kabar baru?"). Riwayat grafik dimuat **sekali** dari `/api/history` saat halaman dibuka, lalu tiap titik baru ditambahkan. Simpan maksimal 120 titik (yang tertua dibuang) agar browser tidak membengkak.
- **Kartu TINGGI S4 dan TINGGI GLOBAL:** beri label yang jelas — S4 = "input fuzzy (pesisir)", Global = "rerata maket (volume)". Keduanya berbeda arti; jangan sampai tertukar.
- **Kartu Status:** tampilkan **teks + ikon + warna** — jangan hanya warna, agar tetap terbaca oleh pengguna dengan gangguan penglihatan warna dan saat dicetak hitam-putih. Untuk level BAHAYA, tampilkan label arah dari tinggi S4 (**SURUT** bila < 11 cm, **LUAPAN** bila > 22 cm) — hanya tampilan, fuzzy tidak berubah.
- **Kartu Kecepatan Gelombang:** nilai kejadian valid terakhir + umurnya ("12 detik lalu"); tampil "—" bila belum ada kejadian. Tidak memengaruhi status.
- **Grafik tren kecepatan:** satu titik per kejadian (bukan garis kontinu 1 Hz). Sumbu X memakai label jam kejadian (HH:MM:SS) berurutan per kejadian, bukan skala waktu, karena kejadian tidak berjarak sama.
- **Badge stabilitas tinggi global (*Should*):** STABIL / TURUN (indikasi kebocoran) / NAIK (indikasi luapan), dihitung dari rata-rata bergerak (mis. 60 detik) supaya gelombang yang lewat tidak memicu alarm palsu. Ambangnya di `config.py`.
- **Offline / terlambat:** jika `age_s` lebih besar dari `STALE_AFTER_S` atau `fetch` gagal → semua kartu abu-abu, status "OFFLINE — data terlambat", dan level terakhir **tidak** dipajang sebagai kondisi saat ini.
- **Data tidak valid:** status "DATA TIDAK VALID" (abu-abu) beserta alasan singkat (mis. "S4 tidak terbaca").
- **Responsif:** HP portrait 1 kolom, tablet 2 × 2, laptop 1 × 4 untuk baris kartu pertama (kelas grid Bootstrap).
- **Waktu:** tampil WIB (UTC+7); database tetap UTC.
- **Footer:** disclaimer penelitian (Bagian 1).

### 6.3 Prioritas Fitur

| Prioritas | Fitur |
|-----------|-------|
| **Must** (wajib) | 6 kartu (tinggi S4, debit, nilai fuzzy, status, tinggi global, kecepatan gelombang); grafik real-time tinggi S4 + tinggi global + debit; **grafik tren kecepatan gelombang**; status berwarna; indikator online/offline + umur data; responsif; **bekerja tanpa internet** (aset lokal); `/api/now`, `/api/history`, `/api/gelombang`, `/health` |
| **Should** | Ekspor CSV (dua tabel); panel riwayat perubahan level; pilihan rentang waktu; badge stabilitas tinggi global; label arah SURUT/LUAPAN pada status BAHAYA; kartu berkedip halus saat ≥ SIAGA; grafik nilai fuzzy |
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

Empat level bersifat terkunci (K7). Warna dan nama level disimpan di `config.py`. Badge stabilitas tinggi global memakai hijau untuk STABIL dan kuning untuk TURUN/NAIK; ia informasi tambahan, **bukan** level fuzzy.

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

**Dampak revisi 1.1 pada jadwal:** pekerjaan tambahan terutama jatuh di Fase 2 (siklus baca cepat, cap waktu per sensor, validasi kecepatan dengan video), Fase 3 (himpunan dan 9 aturan baru), dan Fase 4 (modul `wave_speed.py`, tabel `gelombang_event`). Tanggal tidak diubah. Bila waktu mepet, urutan prioritasnya: **A** (input fuzzy dari S4) → **B** (tinggi global) → **C** (kecepatan gelombang); C paling berisiko karena bergantung pada laju baca dan kualitas puncak gelombang.

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
5. **Minta agent membuat kerangka** memakai prompt di Lampiran A: `config.py`, `db.py`, `sources.py` (simulator 4 sensor), `fuzzy_engine.py` (parameter *contoh*), `wave_speed.py`, `worker.py`, `app.py`, `templates/index.html`, `static/`. Unduh Bootstrap dan Chart.js ke `static/vendor/`. Bila kerangka Fase 1 sudah Anda buat dengan versi 1.0 dokumen ini, pakai **Lampiran B** untuk memigrasikannya.
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
- [ ] Semua skenario simulator (Bagian 5.3) memberi hasil yang diharapkan: `surut_ekstrem` dan `luapan_ekstrem` → SIAGA/BAHAYA sesuai aturan, `gelombang_lewat` → satu kejadian dengan v ≈ 100 cm/s, `sensor_error` → DATA TIDAK VALID (bukan AMAN).
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

**Target:** ESP32 membaca 4 sensor ultrasonik dan 1 flowmeter dengan stabil pada laju ≥ 5 siklus/detik, tiap pembacaan bercap waktu per sensor; hasilnya terkalibrasi dan masuk ke MQTT di Pi.

**Usulan pin ESP32** (cek ulang pinout board Anda sebelum menyolder; indeks 1–4 = urutan fisik S1 → S4):

| Fungsi | GPIO ESP32 | Catatan |
|--------|-----------|---------|
| TRIG 1–4 | 16, 17, 18, 19 | keluaran |
| ECHO 1–4 | 34, 35, 32, 33 | masukan — **lewat pembagi tegangan** (1 kΩ seri, 2 kΩ ke GND ≈ 3,3 V) |
| Sinyal YF-S201 | 27 | masukan interrupt; pastikan sinyal ≤ 3,3 V |
| VCC HC-SR04 | pin 5 V (VIN/USB) | semua GND dihubungkan bersama |

**Langkah:**

1. Siapkan: ESP32 DevKit + kabel USB data, 4× HC-SR04, 1× YF-S201, resistor 1 kΩ dan 2 kΩ (pembagi tegangan; siapkan 5 pasang), breadboard, jumper, catu 5 V, penggaris/meteran.
2. **Pasang dan kabeli bertahap.** Pasang semua sensor **tepat 48,0 cm di atas dasar akuarium** (ukur dengan penggaris; toleransi ±0,2 cm), menghadap tegak lurus ke permukaan air. **S1 di sisi pembangkit gelombang, S4 di sisi pesisir**; ukur jarak pusat S1–S4 (target 75 cm) dan catat posisi S2/S3. Kabeli satu sensor dulu, tes, baru tambah.
3. **Firmware bertahap** (Arduino IDE), tiap langkah dites sendiri:
   - a. 1 sensor → Serial Monitor.
   - b. 4 sensor **bergantian**, jeda awal ±30 ms antar sensor (naikkan ke 40–50 ms bila bacaan kacau karena *crosstalk*). Target siklus penuh ≤ 200 ms (≥ 5 Hz).
   - c. **Cap waktu per sensor:** catat `millis()` saat pembacaan tiap sensor selesai dan isi larik `t_ms` (Bagian 5.5).
   - d. Filter ringan: tolak bacaan di luar 2–48 cm (→ `null`). **Jangan** memakai median 5 sampel beruntun per sensor — itu memperlambat siklus hingga ±1 detik; penghalusan dilakukan di Pi.
   - e. Flowmeter: hitung pulsa dengan interrupt, jendela 1 detik; L/menit = frekuensi ÷ 7,5 sebagai **faktor awal** (nilai umum di datasheet; wajib dikalibrasi).
   - f. Keluaran Serial berformat PLX-DAQ → laptop → Excel.
   - g. Wi-Fi + MQTT: kirim 1 pesan JSON per siklus sesuai kontrak (Bagian 5.5), plus topic status dan *Last Will*.
4. **Kalibrasi ketinggian** (3.10.1, 3.10.3, 3.10.4), **tiap sensor**, dengan perhatian khusus pada **S4** (satu-satunya input fuzzy): minimal 6 titik ketinggian × 30 sampel per sensor, dibandingkan dengan penggaris. Untuk S4 tambahkan titik di rentang anomali (di bawah 11 cm dan di atas 22 cm). Periksa rumus `48.0 - jarak`; bila ada selisih tetap (mis. tinggi pasang sebenarnya 47,8 cm), simpan sebagai koreksi per sensor (a, b) di `config.py`. Hitung MAE, RMSE, dan %error.
5. **Kalibrasi debit** (3.10.2, 3.10.5): tuang ke wadah ukur (1–2 liter) dengan 3 kecepatan pompa × 5 pengulangan → faktor koreksi → MAE dan %error.
6. **Uji laju baca dan kecepatan gelombang:**
   - a. Ukur laju pesan sebenarnya (selisih `t_ms` antar pesan): harus ≥ 5 pesan/detik dan stabil.
   - b. Buat gelombang uji dengan wave maker dan **rekam video** (HP, 60 fps bila ada) dengan penanda jarak 75 cm atau penggaris di samping maket; hitung kecepatan dari video (frame demi frame) sebagai pembanding.
   - c. Bandingkan kecepatan dari sensor dengan kecepatan dari video untuk ≥ 10 kejadian; catat galatnya.
7. **Verifikasi di Pi:** `mosquitto_sub -h localhost -u ews -P <password> -t "ews/#" -v` menampilkan JSON ≥ 5 pesan/detik selama 30 menit tanpa putus.
8. Kumpulkan **dataset awal** lewat PLX-DAQ (Excel) untuk skenario uji — bahan menentukan rentang fungsi keanggotaan di Fase 3, termasuk **level air tenang sebenarnya**.

**DoD Fase 2:**

- [ ] Semua sensor terpasang tepat 48,0 cm (±0,2 cm, diukur) dan jarak S1–S4 sudah diukur.
- [ ] Setiap sensor sudah dites sendiri-sendiri; bacaan air diam stabil (catat simpangan baku).
- [ ] Tegangan pin Echo dan sinyal flowmeter diukur dengan multimeter: **≤ 3,3 V**.
- [ ] Tabel kalibrasi (titik uji, MAE, RMSE, %error) tersimpan untuk **tiap sensor** (S4 paling lengkap) dan untuk debit.
- [ ] Laju pesan ≥ 5/detik stabil selama 30 menit; `seq` berurutan; `t_ms` tiap sensor naik terus.
- [ ] Perbandingan kecepatan sensor vs video untuk ≥ 10 kejadian tersimpan, lengkap dengan galatnya.
- [ ] Jalur Serial → PLX-DAQ → Excel menghasilkan file data.

**[BUKTI]:** foto rangkaian dan pengukuran tinggi pasang 48 cm, tabel kalibrasi per sensor, grafik regresi, screenshot Serial Monitor + `mosquitto_sub`, file Excel PLX-DAQ, **video uji gelombang + tabel perbandingan kecepatan**.

**[JEBAKAN]:**

- GPIO ESP32 **hanya 3,3 V** (tidak toleran 5 V). Echo HC-SR04 berkeluaran 5 V → wajib pembagi tegangan atau *level shifter*; atau pakai varian HC-SR04 yang 3,3 V.
- Jangan memicu 4 HC-SR04 serentak — suaranya saling mengganggu (*crosstalk*) dan bacaan kacau.
- Bacaan 0 atau > 400 cm = gagal baca, **bukan** jarak 0 cm.
- Zona buta HC-SR04 ± 2 cm: pada tinggi pasang 48 cm, permukaan air tertinggi (bibir akuarium 40 cm) berjarak 8 cm dari sensor, jadi masih aman.
- **Tinggi pasang yang meleset 1 cm = bias tinggi 1 cm** pada rumus `48.0 - jarak` untuk sensor itu → ukur dan kalibrasi per sensor.
- **Cap waktu per pesan (bukan per sensor)** membuat Δt bias hingga ¾ siklus baca; pakai `t_ms` per sensor.
- Gelombang memantulkan suara menyamping sehingga echo hilang → pasang sensor tegak lurus, pakai median di Pi, dan catat persentase bacaan gagal (terutama S4).
- HC-SR04 bukan *waterproof*: lindungi dari percikan; jauhkan breadboard dan kabel dari air.
- ESP32 klasik hanya mendukung Wi-Fi **2,4 GHz**.
- PubSubClient: ukuran paket bawaan 256 byte → pesan lebih besar dibuang diam-diam; naikkan dengan `setBufferSize(512)` sebelum menambah field.
- Hindari pin *strapping* (GPIO 0, 2, 5, 12, 15) dan pin flash (6–11) untuk sensor; GPIO 34–39 hanya bisa input dan tanpa pull-up internal.

**[TULIS]:** BAB II 2.2.x (sensor) dan 2.3 (wave flume); BAB III 3.5, 3.7.1 (program ESP32), 3.7.3 (rumus pengolahan sensor: 48,0 − jarak, tinggi global, kecepatan gelombang), 3.10.x (kalibrasi).

---

### Fase 3 — Logika Fuzzy Mamdani (Minggu 4–5: 20 Nov – 3 Des)

**Target:** FIS Mamdani dengan **input Ketinggian S4 dan Debit**, himpunan BAHAYA *double trapezoid*, dan 9 aturan mitigasi tsunami. Parameternya punya alasan jelas, hasilnya cocok dengan hitungan manual, dan akurasinya terukur.

**Variabel** (terkunci: K1, K7, K8):

- **Input 1 — Ketinggian S4 (cm)**, universe 0–40: Aman / Waspada / Bahaya. Nilainya `tinggi_s4_cm` (Bagian 5.5, aturan 4).
- **Input 2 — Debit (L/menit)**, universe 0–30 (rentang kerja YF-S201): Rendah / Sedang / Tinggi.
- **Output — Nilai Bahaya**, universe 0–100: Aman / Waspada / Siaga / Bahaya → 4 level tegas.

**Himpunan keanggotaan.** Bentuk Ketinggian S4 **terkunci** (K8); **semua angka hanya CONTOH** — saya uji berjalan di scikit-fuzzy, ganti dengan data Fase 2:

| Variabel | Himpunan | Bentuk | Titik contoh |
|----------|----------|--------|--------------|
| **Ketinggian S4** (cm) | BAHAYA | ***Double trapezoid***: gabungan (max) dua trapesium | kiri `[0, 0, 11, 13]` + kanan `[20, 22, 40, 40]` |
| | AMAN | Trapesium | `[11, 13, 17, 19]` |
| | WASPADA | Segitiga | `[17, 19.5, 22]` |
| **Debit** (L/menit) | Rendah | Trapesium | `[0, 0, 5, 12]` |
| | Sedang | Segitiga | `[5, 12, 20]` |
| | Tinggi | Trapesium | `[12, 20, 30, 30]` |
| **Nilai Bahaya** (0–100) | AMAN | Segitiga | `[0, 0, 30]` |
| | WASPADA | Segitiga | `[15, 38, 60]` |
| | SIAGA | Segitiga | `[45, 65, 85]` |
| | BAHAYA | Segitiga | `[70, 100, 100]` |

Makna himpunan Ketinggian S4: **BAHAYA** kiri = surut ekstrem (< 11 cm) dan kanan = luapan ekstrem (> 22 cm); **AMAN** = sekitar air tenang maket (≈ 15 cm); **WASPADA** = air mulai naik mendekati luapan. Himpunan BAHAYA bersifat **non-konveks** (dua "bukit"); jelaskan ini di BAB III. Pada uji saya seluruh rentang 0–40 cm tertutup oleh minimal satu himpunan (keanggotaan gabungan terendah 0,45), jadi tidak ada celah.

**Basis aturan — 9 aturan mitigasi tsunami** (terkunci: K9):

| Aturan | IF Ketinggian S4 | AND Debit | THEN Status | Catatan |
|--------|------------------|-----------|-------------|---------|
| R1 | Aman | Rendah | AMAN | |
| R2 | Aman | Sedang | WASPADA | |
| R3 | Aman | Tinggi | SIAGA | Anomali arus bawah cepat |
| R4 | Waspada | Rendah | WASPADA | |
| R5 | Waspada | Sedang | SIAGA | |
| R6 | Waspada | Tinggi | BAHAYA | Tsunami *bore* |
| R7 | Bahaya | Rendah | SIAGA | Fase transisi surut ekstrem |
| R8 | Bahaya | Sedang | BAHAYA | |
| R9 | Bahaya | Tinggi | BAHAYA | Puncak hantaman tsunami |

Matriks ringkas (untuk memeriksa kelengkapan 3 × 3):

| Ketinggian S4 \ Debit | Rendah | Sedang | Tinggi |
|-----------------------|--------|--------|--------|
| **Aman** | R1: AMAN | R2: WASPADA | R3: SIAGA |
| **Waspada** | R4: WASPADA | R5: SIAGA | R6: BAHAYA |
| **Bahaya** | R7: SIAGA | R8: BAHAYA | R9: BAHAYA |

**Hasil uji referensi** untuk parameter CONTOH di atas, dengan ambang level contoh (< 25 AMAN; 25–50 WASPADA; 50–75 SIAGA; ≥ 75 BAHAYA) dan resolusi universe 0,1 untuk input dan 1 untuk output. Bila implementasi agent memakai parameter yang sama, angkanya harus mendekati ini (selisih kecil wajar bila resolusi berbeda):

| Aturan | S4 (cm) | Debit (L/menit) | Nilai fuzzy | Level |
|--------|---------|-----------------|-------------|-------|
| R1 | 15 | 2 | 10,0 | AMAN |
| R2 | 15 | 12 | 37,7 | WASPADA |
| R3 | 15 | 25 | 65,0 | SIAGA |
| R4 | 19,5 | 2 | 37,7 | WASPADA |
| R5 | 19,5 | 12 | 65,0 | SIAGA |
| R6 | 19,5 | 25 | 90,0 | BAHAYA |
| R7 | 8 | 2 | 65,0 | SIAGA |
| R8 | 8 | 12 | 90,0 | BAHAYA |
| R9 | 8 | 25 | 90,0 | BAHAYA |

**Langkah:**

1. **Rentang dan titik himpunan.** Ukur level air tenang maket sebenarnya (Fase 2), lalu tentukan titik trapesium/segitiga Ketinggian S4 (ambang anomali < 11 dan > 22 cm adalah jangkar yang sudah terkunci) dan himpunan Debit dari kalibrasi, rentang flowmeter, literatur/pembimbing, serta dataset. **Tulis alasan tiap angka** — bahan BAB III 3.11. **[PUTUSKAN]** tafsir "±15 cm" (Bagian 2, dampak teknis #6).
2. **Metode:** Mamdani; AND = min; implikasi = min; agregasi = max; defuzzifikasi = **centroid**. Himpunan BAHAYA dibentuk dari gabungan (max) dua trapesium.
3. Implementasi di `fuzzy_engine.py`: sistem **dibangun sekali** saat program mulai, lalu dipakai berulang lewat satu fungsi `hitung(tinggi_s4_cm, debit_lpm)`. Input dibatasi (*clamp*) ke universe; pembacaan hasil dibungkus penanganan error (→ `TIDAK_VALID`).
4. **Pemetaan nilai → level:** ambang di `config.py` (contoh di atas) atau himpunan dengan keanggotaan tertinggi. **[PUTUSKAN]**
5. **Validasi manual:** (a) 9 titik inti — satu per aturan (S4 = 15 / 19,5 / 8 cm × debit = 2 / 12 / 25 L/menit); (b) titik perbatasan: S4 ≈ 11–13 (BAHAYA↔AMAN), 17–19 (AMAN↔WASPADA), 20–22 (WASPADA↔BAHAYA); (c) uji simetri anomali: S4 = 8 dan S4 = 25 pada debit yang sama. Hitung di Excel langkah demi langkah (fuzzifikasi → kekuatan aturan → agregasi → centroid) dengan resolusi universe yang sama dengan program. Selisih hanya boleh sebatas pembulatan.
6. **Uji skenario data nyata:** rancang skenario yang mencakup ke-9 sel aturan (3 tinggi × 3 debit; surut ekstrem dibuat dengan menurunkan air, luapan dengan menaikkan air) dan ulangi beberapa kali. **Label *ground truth* ditetapkan sebelum melihat keluaran fuzzy** (mis. dari kriteria fisik yang disepakati pembimbing) supaya evaluasi tidak berputar-putar. Hitung akurasi dan *confusion matrix* 4 level.
7. Opsional anti-berkedip: rata-rata bergerak 3–5 detik atau *hysteresis*. Jika dipakai, tulis di BAB III.

**DoD Fase 3:**

- [ ] Tabel validasi manual vs program (9 titik inti + titik perbatasan + uji simetri) cocok.
- [ ] Seluruh parameter himpunan, 9 aturan, dan ambang level ada di `config.py` dan **sama persis** dengan yang ditulis di BAB III.
- [ ] Ada tes otomatis kecil di `tests/`: 9 titik inti menghasilkan level yang diharapkan; titik "pasti aman" dan "pasti bahaya"; S4 tidak valid → `TIDAK_VALID`.
- [ ] Tidak ada celah universe (telusuri seluruh rentang 0–40 cm dan 0–30 L/menit).
- [ ] *Confusion matrix* + akurasi dari skenario uji tersimpan.

**[BUKTI]:** grafik fungsi keanggotaan (dicetak dari program, termasuk himpunan BAHAYA dua bukit), tabel 9 aturan, tabel validasi manual, *confusion matrix*.

**[JEBAKAN]:**

- **Celah pada universe** (ada nilai input yang tidak "ditangkap" fungsi keanggotaan mana pun, sehingga tidak ada aturan yang aktif): pada scikit-fuzzy 0.5.0 `compute()` selesai **tanpa error**, tetapi hasilnya kosong sehingga `KeyError` baru muncul saat membaca output. Pastikan himpunan saling menutupi seluruh rentang, dan bungkus pembacaan hasil dengan penanganan error (→ `TIDAK_VALID`).
- Pada uji saya, input di luar universe **diam-diam dibatasi** ke tepi dan **tidak** error — sensor rusak (mis. 999 cm) bisa menghasilkan level yang tampak valid. Karena itu validasi sensor dilakukan **sebelum** fuzzy (Aturan Agent #10).
- Centroid hampir tak pernah mencapai tepat 0 atau 100. Pada uji saya, himpunan output segitiga `[70, 100, 100]` menghasilkan maksimum ≈ 90 (bentuk trapesium malah sedikit lebih rendah, ≈ 89). Bila ingin angka mendekati 100, **geser awal himpunan ujung mendekati tepi** (mis. `[85, 100, 100]` → ≈ 95). Apa pun pilihannya, jadikan **level (kategori)** sebagai informasi utama dan angka sebagai pendukung.
- **BAHAYA tunggal tidak membedakan arah.** S4 = 8 cm (surut) dan S4 = 25 cm (luapan) menghasilkan keluaran identik pada uji saya. Tulis sebagai keterbatasan di BAB III/IV; label arah SURUT/LUAPAN hanya ditambahkan di dashboard.
- **Satu segitiga WASPADA hanya menutup satu sisi** (sisi naik). Sisi surut (11–13 cm) dilayani lereng AMAN dan BAHAYA saja; pada uji saya S4 = 12 cm dengan debit rendah menghasilkan ≈ 42 (WASPADA) lewat interpolasi. Jelaskan di BAB III. **[PUTUSKAN]** bila Anda ingin sisi surut juga punya WASPADA tersendiri (mis. dua puncak WASPADA).
- Jangan membuat ulang sistem fuzzy tiap detik; buat sekali, pakai berulang.
- scikit-fuzzy 0.5.0 sudah memunculkan *DeprecationWarning* dari numpy 2.5. Kunci versi lewat `requirements.txt` dan **jangan upgrade numpy** setelah semuanya jalan. **Rencana cadangan:** Mamdani (min–max–centroid) bisa ditulis manual dengan NumPy; minta agent membuatnya hanya sebagai pembanding/cadangan, sekaligus berguna untuk validasi hitungan manual.
- Satuan tertukar (cm vs mm, L/menit vs L/detik) adalah sumber error klasik — tulis satuan di nama variabel.

**[TULIS]:** BAB II 2.4.x; BAB III 3.11 (Pengujian Fuzzy: tabel himpunan, 9 aturan, bentuk non-konveks BAHAYA), kerangka 3.12, dan **3.13 Parameter Keberhasilan** — isi X, Y, Z dengan angka setelah uji pendahuluan dan disepakati pembimbing (bentuk: error ketinggian ≤ …%, error debit ≤ …%, akurasi ≥ …%, galat kecepatan gelombang ≤ …% terhadap video, latensi ≤ … detik).

---

### Fase 4 — Backend dan Database dengan Data Nyata (Minggu 6: 4 – 10 Des)

**Target:** dari ESP32 sampai database berjalan **otomatis**, pulih sendiri saat ada gangguan, dan bisa diekspor.

**Langkah:**

1. Ubah sumber data jadi `mqtt` di Pi. `worker.py`: berlangganan topic, validasi, kalibrasi (sisi Pi), lalu menjalankan **tiga pengolahan** — (A) fuzzy dari S4, (B) tinggi global, (C) deteksi puncak dan kecepatan lewat `wave_speed.py` — dan menyimpan hasilnya. Callback MQTT hanya menaruh pesan ke antrean; perhitungan dilakukan di luar callback supaya koneksi tidak tertahan.
2. Database: mode WAL, index `ts_ms` pada kedua tabel, tabel `gelombang_event` (dan `events`); satu penulis (worker), banyak pembaca (web). Aliran cepat (≥ 5 Hz) diturunkan menjadi 1 baris `logs_sensor` per detik; commit tiap ±1 detik, bukan tiap pesan.
3. **Ketahanan:** sambung ulang MQTT otomatis; `subscribe` dilakukan **di dalam** `on_connect` (agar langganan pulih setelah putus); bila ESP32 mati → catat status offline dan **jangan menulis nilai palsu**; hitung pesan yang hilang dari `seq`.
4. Selesaikan API final (termasuk `/api/gelombang`) dan ekspor CSV kedua tabel (Bagian 5.7).
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
- [ ] Tes otomatis `wave_speed` lulus: gelombang sintetis dengan kecepatan diketahui (mis. 100 cm/s) menghasilkan v dalam toleransi yang Anda tetapkan pada laju 5 Hz; puncak < 20 cm tidak menghasilkan kejadian; Δt ≤ 0 ditolak.
- [ ] Gelombang uji nyata menghasilkan baris `gelombang_event` dan muncul di `/api/gelombang`.
- [ ] `tinggi_global_cm` terisi bila ≥ 2 sensor valid dan NULL bila kurang; S4 dimatikan → level TIDAK_VALID (bukan AMAN).

**[BUKTI]:** screenshot `systemctl status`, potongan log saat ESP32 dimatikan/dihidupkan, contoh CSV (kedua tabel), isi tabel `gelombang_event`, ukuran dan jumlah baris database.

**[JEBAKAN]:**

- *"database is locked"* → pastikan hanya satu penulis, mode WAL aktif, dan koneksi tidak dibiarkan terbuka lama.
- **Pi tidak punya baterai jam (RTC).** Tanpa internet, jam bisa salah setelah reboot dan semua `ts_ms` ikut salah. Cek `date` sebelum setiap sesi pengambilan data; sambungkan ke internet atau set jam manual.
- paho-mqtt 2.x: lupa `callback_api_version` → error saat membuat Client.
- Password Mosquitto salah → koneksi ditolak; periksa log (`journalctl -u mosquitto`).
- **Pasangan puncak salah:** puncak S4 dipasangkan dengan puncak S1 yang lama → batasi dengan jendela `DT_MAKS_S` dan tandai pasangan yang sudah dipakai.
- **Jangan memakai waktu terima pesan di Pi untuk Δt** — Wi-Fi dapat berjitter puluhan hingga ratusan milidetik; pakai `t_ms` dari ESP32.
- **ESP32 restart** → `t_ms` kembali dari 0 dan `seq` mundur; kosongkan buffer puncak agar tidak terbentuk Δt negatif palsu.

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
6. **Ukur parameter keberhasilan 3.13:** error ketinggian dan debit (dari kalibrasi), akurasi klasifikasi, galat kecepatan gelombang terhadap video, latensi (rekam layar + kejadian fisik, lalu hitung selisih waktu; latensi ≈ interval kirim + proses + interval polling), dan kelengkapan data Web IoT.
7. Latih **skrip demo** (Bagian 10) minimal dua kali dan rekam **video cadangan**.

**DoD Fase 5:**

- [ ] Semua fitur *Must* dan *Should* di Bagian 6.3 berfungsi.
- [ ] Dashboard terbuka lewat URL tunnel dari HP berdata seluler.
- [ ] Grafik tren kecepatan terisi saat wave maker dinyalakan; kartu tinggi global stabil saat air tenang.
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
- **Satuan:** tulis satuan di nama variabel (`tinggi_s4_cm`, `debit_lpm`).
- **Konstanta terkunci** (48,0 cm; 75,0 cm; 20 cm; 4 level; 9 aturan) hanya ditulis di `config.py` dan BAB III. Jangan menyalinnya ke banyak tempat: satu angka yang berbeda antara kode dan naskah pasti ditemukan penguji.
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

**3.8 Perancangan Dashboard dan 3.9 Perancangan Database:** ambil dari Bagian 6 (wireframe, perilaku, warna) dan Bagian 5.5–5.7 (kontrak data, skema, endpoint). Sajikan sebagai tabel "Daftar API", "Skema `logs_sensor`", dan "Skema `gelombang_event`".

**Tambahan akibat Sensor Fusion:**

- **3.7.3 Pengolahan Data Sensor:** tuliskan rumus `ketinggian_cm = 48.0 - jarak_bacaan_sensor`, alasan memakai S4 sebagai input fuzzy (*run-up* dan surut ekstrem di pesisir), definisi tinggi global (median/rata-rata) beserta tujuannya, dan definisi kecepatan `v = 75 / (t_s4 - t_s1)` (puncak ≥ 20 cm, cap waktu per sensor, estimasi puncak sub-sampel).
- **3.11 Pengujian Fuzzy:** tabel himpunan Ketinggian S4 (termasuk bentuk *double trapezoid* / non-konveks), tabel 9 aturan, dan keterbatasan "BAHAYA tunggal untuk dua anomali".
- **3.8 dan 3.9:** tambahkan kartu dan grafik tinggi global serta kecepatan; skema dua tabel.
- **BAB II (Gelombang):** hubungan kecepatan gelombang dengan kedalaman air dangkal (v ≈ √(g·h)) sebagai pembanding teoritis hasil C. **Cari rujukan jurnal** untuk klaim ini; jangan hanya mengandalkan saya.
- **3.13 Parameter Keberhasilan:** tambahkan galat kecepatan gelombang terhadap video.

Contoh format IEEE untuk sumber online (ganti tanggal dengan tanggal akses Anda):

```
[n] Cloudflare, "Quick Tunnels," Cloudflare Docs. Accessed: <tanggal akses>. [Online]. Available: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/
```

### 9.3 Temuan di Proposal yang Perlu Diperbaiki

1. **Abstract (Inggris)** masih berisi "Keywords: Rice," (sisa templat lama); abstrak dan kata kunci bahasa Indonesia masih kosong.
2. **Tabel 3.2:** baris HC-SR04 menulis "mempermudah segmentasi objek beras" → ganti: mengukur jarak ke permukaan air pada empat titik (S1–S4, dipasang 48 cm dari dasar akuarium) untuk menghitung ketinggian muka air. "Micro HMI to HMI" → "Micro HDMI to HDMI".
3. **Tabel 3.3:** "Arduino IDE — Model untuk deteksi objek beras" dan "Raspberry Pi OS — Melakukan pelabelan dataset (*bounding box*)" adalah sisa templat; "Pythone" → "Python"; fungsi "Web Dashboard" masih kosong. Tambahkan Mosquitto, SQLite, Flask, scikit-fuzzy, Bootstrap/Chart.js, dan cloudflared.
4. **MySQL vs SQLite** di 2.1 dan "Flash" di Gambar 2.2 (lihat Bagian 2, butir 2).
5. **Daftar Pustaka:** muncul kata berbahasa Catalan (*núm.*, *i*, *Accedit*, *En línia*, *Disponible a*) — kemungkinan dari pengaturan bahasa (*locale*) gaya sitasi di aplikasi referensi Anda; ubah ke English (US) atau Indonesia. Beberapa entri terbaca salah: [17] penulis tertulis "S. Siaga" (itu kata dari judul), [27] "M. L. C. D. Lml", [28] "J. Tera" (nama jurnal, bukan penulis) dengan judul terpotong, [30] teks abstrak ikut masuk judul, [21] dan [31] hanya nama berkas `.pdf`, serta [5] dan [24] adalah artikel yang sama. Pedoman melarang "et al."/"dkk." (ada di [16] dan [18]).
6. **Proporsi referensi lima tahun terakhir:** hitungan kasar saya ±16 dari 30 (≈ 53%) terbit 2021–2026, sedangkan Pedoman menyarankan 70%. Saat menambah rujukan untuk Dashboard/Database/MQTT, utamakan jurnal 2021–2026.
7. **Urutan daftar pustaka:** Pedoman menyebut "alfabetik" sekaligus format IEEE bernomor (urut kemunculan). Tanyakan pembimbing; defaultnya IEEE = urut kemunculan.
8. **Jadwal (Tabel 3.0.1):** teks menulis Januari–November 2026, sedangkan rencana kerja ini sampai 31 Desember 2026 → sesuaikan. Daftar Tabel masih berisi hyperlink ke jalur berkas lokal, dan nama berkas proposal masih memakai judul proyek lain → ganti nama dan hapus hyperlink.

---

## 10. Demo dan Bukti

### 10.1 Skrip Demo (±5–7 menit)

1. Tunjukkan diagram arsitektur (30 detik): sensor S1–S4 → ESP32 → MQTT → Pi (fuzzy dari S4, tinggi global, kecepatan gelombang, SQLite, Flask) → Cloudflare → dashboard.
2. Buka dashboard di laptop (LAN) dan di HP lewat **data seluler** (URL tunnel) — bukti akses dari luar.
3. Kondisi awal air tenang → **AMAN** (hijau); tinggi global stabil di sekitar level air tenang; kartu kecepatan masih "—".
4. Naikkan debit pompa → debit naik → **WASPADA / SIAGA** (aturan R2/R3).
5. Nyalakan wave maker → puncak ≥ 20 cm melewati S1 lalu S4 → **kartu kecepatan terisi** (mis. ±100 cm/s) dan muncul titik baru di grafik tren kecepatan; saat tinggi S4 > 22 cm dengan debit sedang/tinggi → **BAHAYA** (merah, berlabel LUAPAN).
6. Bila aman dilakukan: turunkan air hingga tinggi S4 < 11 cm → anomali **surut ekstrem** → SIAGA/BAHAYA (R7/R8, berlabel SURUT).
7. Cabut ESP32 (atau lepas S4) → muncul **OFFLINE / DATA TIDAK VALID** (bukan AMAN) → tunjukkan sifat *fail-safe*.
8. Buka tabel `logs_sensor` dan `gelombang_event` atau ekspor CSV → riwayat tercatat; sebut hasil uji 24 jam, tabel akurasi, dan perbandingan kecepatan sensor vs video.

### 10.2 Daftar Periksa Sebelum Sidang

- [ ] Adaptor 5 V / 3 A, kabel cadangan, power strip; Pi tidak panas; kartu SD sudah di-backup.
- [ ] Router/hotspot sendiri menyala; Pi berIP tetap; ESP32 tersambung.
- [ ] `cloudflared` dinyalakan 30 menit sebelumnya; URL dicatat; dicoba dari HP berdata seluler.
- [ ] Salinan `ews.db`, CSV, dan video cadangan ada di laptop **dan** flashdisk.
- [ ] Perlengkapan skenario fisik siap: air, pompa, wave maker, wadah ukur.
- [ ] Tinggi pasang 48,0 cm dan jarak S1–S4 diukur ulang (sensor tidak bergeser); video acuan kecepatan gelombang tersedia.
- [ ] Akses cadangan siap: `http://<IP-Pi>:5000` lewat LAN.

### 10.3 Pertanyaan Penguji yang Mungkin dan Jawaban Singkat

- **Kenapa fuzzy Mamdani?** Aturan IF–THEN mudah dibaca dan divalidasi dengan hitungan manual; cocok untuk mengklasifikasi level dari dua variabel fisik.
- **Kenapa centroid?** Menghasilkan satu nilai tegas yang memperhitungkan seluruh bentuk himpunan output; defuzzifikasi yang umum pada Mamdani.
- **Kenapa hanya Sensor 4 yang menjadi input fuzzy?** Pantai adalah titik kritis *run-up* dan surut ekstrem tsunami; sensor lain dipakai untuk tinggi global (stabilitas volume) dan kecepatan gelombang — itulah sensor fusion.
- **Mengapa himpunan BAHAYA berbentuk dua trapesium?** Untuk menangkap dua anomali tsunami sekaligus: surut ekstrem (< 11 cm) dan luapan ekstrem (> 22 cm).
- **Bagaimana kecepatan gelombang dihitung, dan seberapa akurat?** v = 75 cm / Δt, dengan Δt selisih waktu puncak ≥ 20 cm di S1 dan S4 yang dicap per sensor di ESP32; akurasinya ditunjukkan lewat perbandingan terhadap video (tabel Fase 2/5).
- **Apa gunanya tinggi global?** Memantau stabilitas volume air maket secara makro (kebocoran atau luapan tangki), terpisah dari klasifikasi fuzzy.
- **Kenapa SQLite, bukan MySQL?** Satu Pi, satu tabel, satu penulis; tanpa service server sehingga lebih ringan dan mudah di-backup.
- **Kenapa MQTT?** Ringan, dan memisahkan ESP32 dari Pi — ESP32 cukup mengirim ke sebuah topic.
- **Kenapa polling, bukan WebSocket?** Cukup untuk pembaruan 2 detik, lebih sederhana, dan berjalan di Cloudflare Quick Tunnel.
- **Bagaimana jika sensor mati?** Data divalidasi: S4 atau debit tidak valid → "DATA TIDAK VALID"; > 5 detik tanpa data → "OFFLINE"; sistem tidak pernah menampilkan AMAN. Mati-nya sensor lain hanya mengurangi tinggi global (butuh ≥ 2 sensor) dan kecepatan gelombang.
- **Bagaimana akurasi dan latensinya?** Jawab dengan tabel hasil Fase 5 (parameter keberhasilan 3.13).
- **Apa keterbatasannya?** Skala laboratorium; dua input fuzzy (tinggi S4 dan debit); himpunan BAHAYA tidak membedakan surut dan luapan; bukan pengganti sistem resmi BMKG/BNPB (Batasan Penelitian).
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
- **Sensor fusion** — menggabungkan beberapa sensor untuk mendapatkan informasi yang lebih kaya; di sini tiga informasi dari empat sensor yang sama (tinggi pesisir, tinggi global, kecepatan gelombang).
- ***Run-up*** — kenaikan air ke arah pantai saat gelombang tiba; di maket diamati di sisi S4.
- **Surut ekstrem / luapan ekstrem** — tinggi air di S4 turun jauh di bawah normal (< 11 cm) / naik jauh di atas normal (> 22 cm).
- ***Double trapezoid*** — himpunan fuzzy yang dibentuk dari dua trapesium (kiri dan kanan); bentuknya non-konveks (dua "bukit").
- **Cap waktu (*timestamp*)** — jam yang ditempelkan pada data saat data diambil; untuk kecepatan gelombang dipakai cap waktu **per sensor** dari ESP32.
- **Δt (dt)** — selisih waktu puncak gelombang antara S1 dan S4; kecepatan = 75 cm dibagi Δt.

---

## Log Keputusan

Isi saat keputusan diambil; bahan penjelasan di BAB III.

| Tanggal | Keputusan | Hasil | Disetujui oleh |
|---------|-----------|-------|----------------|
| 4 Nov 2026 | Input fuzzy = Sensor 4 saja (K1) | Terkunci | Anda (keputusan riset) |
| 4 Nov 2026 | Tinggi pasang 48,0 cm; jarak S1–S4 75 cm; rumus `48.0 - jarak` (K4–K6) | Terkunci | Anda (keputusan riset) |
| 4 Nov 2026 | 4 level; 9 aturan; BAHAYA *double trapezoid* (K7–K9) | Terkunci | Anda (keputusan riset) |
| | Database: SQLite (bukan MySQL) | | |
| | Agregasi tinggi global: median atau rata-rata (K2) | | |
| | Titik himpunan keanggotaan (angka CONTOH → final) dan tafsir "±15 cm" | | |
| | Pemetaan nilai fuzzy → level (ambang / keanggotaan tertinggi) | | |
| | Sumber *ground truth* untuk evaluasi 3.12 | | |
| | Laju baca ESP32 final (target ≥ 5 Hz) dan jeda antar sensor | | |

---

## Lampiran A. Prompt Siap Tempel untuk Fase 1

> **Konteks:** Baca `PROJECT_SPEC.md` (Bagian 1, Bagian 2 butir K1–K9, Bagian 3, 5, 6, dan Fase 1 di Bagian 7). Kita mengerjakan **Fase 1 langkah 5: kerangka mode simulasi**.
>
> **Tugas:** buat kerangka proyek yang berjalan di laptop Windows dan Raspberry Pi **tanpa MQTT dan tanpa hardware**: `config.py` (termasuk konstanta terkunci 48,0 / 75,0 / 20), `db.py` (tabel `logs_sensor` dan `gelombang_event` sesuai Bagian 5.6), `sources.py` (simulator 8 skenario Bagian 5.3 yang menghasilkan 4 jarak + `t_ms` per sensor + debit), `fuzzy_engine.py` (himpunan Ketinggian S4 dan 9 aturan sesuai Fase 3; angka *contoh* ditandai jelas), `wave_speed.py`, `worker.py` (tiga pengolahan A/B/C), `app.py` (endpoint GET di Bagian 5.7), `templates/index.html`, dan `static/` (Bootstrap + Chart.js disimpan lokal di `static/vendor/`).
>
> **Batasan:** struktur flat Bagian 5.4; tanpa library di luar Bagian 4; semua angka di `config.py`; input fuzzy hanya `tinggi_s4_cm` dan `debit_lpm`; data tidak valid atau terlambat tidak boleh tampil "AMAN"; semua endpoint read-only.
>
> **Cara kerja:** (1) tulis rencana 5–8 baris dan daftar file, tunggu persetujuan saya; (2) buat file satu per satu dan jelaskan tiap file dalam 2–3 kalimat sederhana; (3) beri perintah menjalankan beserta hasil yang diharapkan; (4) jalankan sendiri dan laporkan hasil nyata.
>
> **Selesai bila:** butir dashboard di DoD Fase 1 terpenuhi.

Untuk fase lain, ganti "Fase 1 langkah 5: kerangka mode simulasi" dengan fase dan langkah yang sedang dikerjakan, misalnya "Fase 3 langkah 3–4: `fuzzy_engine.py` dengan parameter dari `config.py`".

---

## Lampiran B. Prompt Migrasi ke Sensor Fusion

Gunakan bila kerangka kode Anda sudah dibuat memakai **versi 1.0** dokumen ini (satu ketinggian agregat, 1 pesan/detik, satu tabel).

> **Konteks:** Baca `PROJECT_SPEC.md` versi 1.1: Bagian 1, Bagian 2 (K1–K9 dan Dampak Teknis), Bagian 3 (aturan #17–#20), Bagian 5.5–5.7, Bagian 6, dan Fase 3. Kode saat ini dibuat dengan versi 1.0. Kita **memigrasikan** kode ke Sensor Fusion.
>
> **Tugas, berurutan — kerjakan satu per satu dan tunggu persetujuan saya di tiap langkah:**
> 1. `config.py`: tambah konstanta terkunci (`TINGGI_PASANG_CM` = 48.0, `JARAK_S1_S4_CM` = 75.0, `AMBANG_PUNCAK_CM` = 20.0, `INDEKS_S4` = 3) beserta `S4_MEDIAN_N`, `AGREGASI_GLOBAL`, `MIN_SENSOR_VALID`, `DT_MAKS_S`, `V_MIN_CMS`, `V_MAKS_CMS`, `LOG_INTERVAL_S`; ganti nama himpunan Debit menjadi Rendah/Sedang/Tinggi dan parameter fuzzy sesuai Fase 3.
> 2. `db.py`: skema Bagian 5.6 (`tinggi_s4_cm` dan `tinggi_global_cm` menggantikan `ketinggian_cm`; tabel baru `gelombang_event`). Data lama hanya hasil simulasi, jadi boleh hapus `data/ews.db` dan buat ulang.
> 3. `sources.py`: simulator 4 sensor dengan `t_ms` per sensor dan 8 skenario Bagian 5.3.
> 4. `fuzzy_engine.py`: input `tinggi_s4_cm` dan `debit_lpm`; himpunan BAHAYA *double trapezoid*; 9 aturan; dibangun sekali.
> 5. `wave_speed.py` (fungsi murni) beserta tes dengan gelombang sintetis.
> 6. `worker.py`: pipeline A/B/C, penurunan ke 1 baris/detik, penulisan `gelombang_event`.
> 7. `app.py`: endpoint dan field baru (Bagian 5.7).
> 8. `templates/index.html` dan `static/js/app.js`: kartu tinggi S4, tinggi global, dan kecepatan; grafik utama (S4 + global + debit) dan grafik tren kecepatan.
>
> **Aturan:** di tiap langkah beri perintah tes dan hasil yang diharapkan; jangan mengubah konstanta terkunci; laporkan bila ada pertentangan dengan kode lama.

*— Akhir dokumen —*
