# Panduan Desain Web Dashboard IoT (Anti-AI Slop)

Dokumen ini adalah panduan desain khusus untuk membangun antarmuka web (frontend) proyek "Dashboard IoT Peringatan Dini Gelombang Air". Panduan ini dirancang agar agen AI (seperti Claude atau GPT) menghasilkan desain yang bersih, fungsional, dan bebas dari pola "AI Slop" yang umum (seperti desain yang terlalu padat, elemen UI palsu, atau tata letak bersarang yang rumit).

Dokumen ini merujuk pada prinsip-prinsip desain premium dan mematuhi batasan yang ditetapkan dalam `PROJECT_SPEC.md`.

## 1. Prinsip Utama (Core Directives)

*   **Fokus pada Keterbacaan dan Fungsionalitas:** Dashboard ini adalah alat pemantauan (monitoring tool). Keterbacaan metrik (Ketinggian, Debit, Status) adalah prioritas mutlak.
*   **Minimalis & Fungsional (Anti-Slop):** Hindari elemen dekoratif yang tidak berguna. Jangan gunakan *pills*, *badges*, teks jargon palsu (seperti "00 orchestration layer"), atau wadah bersarang (kartu di dalam kartu) yang hanya menghabiskan ruang tanpa memberi nilai informasi [cite: 2].
*   **Responsif sejak Awal:** Desain harus terlihat rapi dan tidak penuh sesak saat dilihat pada layar laptop kecil maupun perangkat seluler [cite: 2].
*   **Satu Area, Satu Fungsi:** Jangan menjejalkan semua informasi dalam satu tampilan yang padat. Berikan ruang bernapas (*whitespace*) yang cukup antar elemen [cite: 2].

## 2. Palet Warna dan Tipografi

**Warna (Merujuk pada `PROJECT_SPEC.md`):**
Status bahaya menentukan skema warna kartu indikator. Warna harus memiliki kontras teks yang jelas.

*   **Aman:** Hijau (`#2E7D32`) dengan teks putih.
*   **Waspada:** Kuning (`#F9A825`) dengan teks gelap.
*   **Siaga:** Oranye (`#EF6C00`) dengan teks putih.
*   **Bahaya:** Merah (`#C62828`) dengan teks putih.
*   **Offline/Tidak Valid:** Abu-abu (`#757575`) dengan teks putih.

**Tipografi:**
*   Gunakan font *sans-serif* yang bersih, rasional, dan mudah dibaca (misalnya Inter, Roboto, atau font bawaan sistem seperti Segoe UI/San Francisco).
*   Hindari menggunakan terlalu banyak bobot font. Gunakan *Bold* untuk angka metrik utama dan *Regular/Medium* untuk label.
*   **Hierarki:** Ukuran teks untuk angka Ketinggian/Debit harus menjadi elemen visual terbesar setelah status warna.

## 3. Struktur Tata Letak (Layout Structure)

Struktur harus mengikuti kelas grid Bootstrap secara langsung, tanpa elemen pembungkus (wrapper) ekstra yang tidak perlu [cite: 2].

**Pola Tata Letak (Atas ke Bawah):**

1.  **Header Utama (Hero Area):**
    *   Sangat bersih dan jelas.
    *   Tampilkan Judul: "EWS Gelombang Air - Kanal Gelombang Lab".
    *   Tampilkan Indikator Status Koneksi: "[ONLINE]" atau "[OFFLINE]" dan umur data ("Data terakhir: X detik lalu").
    *   *Batasan Anti-Slop:* Jangan ada tombol berlebihan atau efek gradien AI (ungu/biru) di header [cite: 2].

2.  **Baris Metrik Utama (4 Kartu):**
    *   Kartu 1: Ketinggian Air (cm).
    *   Kartu 2: Debit (L/mnt).
    *   Kartu 3: Nilai Fuzzy (0-100).
    *   Kartu 4: Status Bahaya (Warna penuh sesuai status).
    *   *Desain Kartu:* Gunakan *border-radius* yang konsisten, bayangan yang sangat lembut (subtle shadow), dan jangan meletakkan kartu di dalam kartu [cite: 2].

3.  **Area Grafik Utama (Chart.js):**
    *   Grafik garis lebar (full width container) yang menampilkan Ketinggian dan Debit secara bersamaan (dua sumbu Y).
    *   Sumbu waktu (X) harus berupa teks `HH:MM:SS` yang dapat dibaca, bukan label waktu bawaan AI yang acak.

4.  **Area Informasi Sekunder (Bawah):**
    *   Dibagi menjadi dua kolom pada layar besar (Grid 50/50).
    *   Kolom Kiri: Grafik nilai Fuzzy.
    *   Kolom Kanan: Daftar riwayat perubahan level terbaru (Event logs).
    *   *Batasan Anti-Slop:* Gunakan daftar sederhana (list-group), bukan tata letak dasbor rumit ala "control room" [cite: 2].

5.  **Footer:**
    *   Area untuk kontrol waktu (Rentang: 2 mnt, 30 mnt, 2 jam) dan tombol Unduh CSV.
    *   *Disclaimer* wajib: "Prototipe skala laboratorium - bukan pengganti peringatan BMKG/BNPB".

## 4. Instruksi Implementasi untuk AI Agent

Saat AI Agent menerjemahkan desain ini ke dalam kode (HTML + Bootstrap + Chart.js), instruksikan AI untuk:

1.  **Gunakan File Lokal:** Panggil Bootstrap dan Chart.js dari `static/vendor/`, JANGAN menggunakan CDN (karena Raspberry Pi mungkin berjalan luring) [cite: 1].
2.  **Hindari "Design Drift":** Jangan mengubah tata letak sederhana yang diminta ini menjadi templat generik bersarang. Patuhi instruksi ruang kosong (*spacing*) dan ukuran tipografi [cite: 2].
3.  **Hanya Komponen Sederhana:** Jangan menggunakan elemen UI mikro yang dekoratif (jangan tambah ikon yang tidak diminta, jangan tambah status bar palsu) [cite: 2].
4.  **Fokus pada Kode Nyata:** Kode yang dihasilkan harus dapat langsung disalin ke `templates/index.html` tanpa memerlukan *build tool* (seperti Webpack atau Vite) [cite: 1].

## 5. Pemeriksaan Akhir (Clarity Check)

Sebelum menyatakan desain/kode selesai, agen harus memverifikasi:
*   [ ] Apakah layout hanya menggunakan satu lapisan *container* Bootstrap? (Anti kartu-dalam-kartu) [cite: 2].
*   [ ] Apakah tipografi untuk angka metrik cukup besar dan terbaca jelas? [cite: 2].
*   [ ] Apakah warna status digunakan secara fungsional untuk menunjukkan kondisi aman/bahaya, bukan sekadar dekorasi? [cite: 1, 2].
*   [ ] Apakah ruang kosong (padding/margin) terlihat seimbang dan rapi? [cite: 2].
*   [ ] Apakah sudah dipastikan tidak ada efek gradien, glassmorphism, atau ornamen visual yang tidak relevan dengan dashboard pemantauan teknis? [cite: 2].
