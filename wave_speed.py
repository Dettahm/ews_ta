"""
wave_speed.py — Modul Deteksi Puncak & Kecepatan Gelombang Air
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 3 Aturan #7, #19 & Bagian 5.5 Aturan 6:
- Fungsi murni: angka masuk -> kejadian gelombang keluar (tanpa I/O, tanpa database)
- Deteksi puncak lokal >= AMBANG_PUNCAK_CM (20.0 cm) dengan estimasi waktu sub-sampel (parabola)
- Pencocokan puncak S1 -> S4 dalam jendela DT_MAKS_S (3.0 detik)
- Menghitung kecepatan: v = JARAK_S1_S4_CM / dt_detik = 75.0 / (dt_ms / 1000) (cm/s)
- Menolak dt <= 0 atau v di luar rentang V_MIN_CMS s/d V_MAKS_CMS (ditandai valid = 0)
"""

from typing import Optional, Dict, Any, List, Tuple
import config


def fit_parabola_vertex(t0: float, y0: float, t1: float, y1: float, t2: float, y2: float) -> Tuple[float, float]:
    """
    Menghitung titik puncak parabola sub-sampel (vertex) dari 3 titik (t0, y0), (t1, y1), (t2, y2)
    di mana (t1, y1) adalah puncak diskrit lokal (y1 >= y0 dan y1 >= y2).

    Mengembalikan:
        (t_vertex, y_vertex)
    """
    dt1 = t1 - t0
    dt2 = t2 - t1
    if dt1 <= 0 or dt2 <= 0:
        return t1, y1

    # Slope segmen 1 dan segmen 2
    s1 = (y1 - y0) / dt1
    s2 = (y2 - y1) / dt2

    # Kelengkungan parabola A = (s2 - s1) / (t2 - t0)
    denom = t2 - t0
    if denom <= 0:
        return t1, y1

    a = (s2 - s1) / denom
    # Jika a >= 0 (cekung ke atas atau garis lurus), puncak terjadi di t1
    if a >= -1e-9:
        return t1, y1

    # Koefisien b: y1 - y0 = a*(t1^2 - t0^2) + b*(t1 - t0) -> b = s1 - a*(t1 + t0)
    b = s1 - a * (t1 + t0)
    t_vertex = -b / (2.0 * a)

    # Batasi agar vertex tidak melompat terlalu jauh di luar interval [t0, t2]
    t_vertex = max(t0, min(t2, t_vertex))

    # Nilai y di vertex: y(t) = a*t^2 + b*t + c
    c = y1 - a * (t1 ** 2) - b * t1
    y_vertex = a * (t_vertex ** 2) + b * t_vertex + c

    # Puncak sub-sampel setidaknya sebesar y1
    y_vertex = max(y1, y_vertex)

    return float(t_vertex), float(y_vertex)


class WaveSpeedTracker:
    """
    Pelacak aliran gelombang real-time untuk mendeteksi puncak di Sensor 1 dan Sensor 4,
    serta menghitung kecepatan rambat gelombang v = 75 cm / dt.
    """

    def __init__(self,
                 ambang_puncak_cm: float = config.AMBANG_PUNCAK_CM,
                 jarak_s1_s4_cm: float = config.JARAK_S1_S4_CM,
                 dt_maks_s: float = config.DT_MAKS_S,
                 v_min_cms: float = config.V_MIN_CMS,
                 v_maks_cms: float = config.V_MAKS_CMS):
        self.ambang_puncak_cm = ambang_puncak_cm
        self.jarak_s1_s4_cm = jarak_s1_s4_cm
        self.dt_maks_ms = int(dt_maks_s * 1000.0)
        self.v_min_cms = v_min_cms
        self.v_maks_cms = v_maks_cms

        # Buffer pembacaan terkini: list of (t_ms, height_cm)
        self.buf_s1: List[Tuple[int, float]] = []
        self.buf_s4: List[Tuple[int, float]] = []

        # Antrean kandidat puncak S1 yang belum dipasangkan: list of (t_peak_ms, h_peak_cm)
        self.pending_s1_peaks: List[Tuple[float, float]] = []

        # Cap waktu pembacaan terakhir untuk mendeteksi ESP32 reboot / rollback jam
        self.last_t_s1: Optional[int] = None
        self.last_t_s4: Optional[int] = None

        # Waktu puncak terakhir yang terdeteksi untuk mencegah double-trigger pada puncak yang sama
        self.last_detected_peak_t_s1: float = -1e9
        self.last_detected_peak_t_s4: float = -1e9
        self.dead_time_ms = 400.0  # Jeda minimal antar puncak pada sensor yang sama (400 ms)

    def reset(self):
        """Mengosongkan semua buffer pelacak (misal saat ESP32 restart)."""
        self.buf_s1.clear()
        self.buf_s4.clear()
        self.pending_s1_peaks.clear()
        self.last_t_s1 = None
        self.last_t_s4 = None
        self.last_detected_peak_t_s1 = -1e9
        self.last_detected_peak_t_s4 = -1e9

    def process_sample(self,
                       t_s1_ms: Optional[int],
                       h_s1_cm: Optional[float],
                       t_s4_ms: Optional[int],
                       h_s4_cm: Optional[float]) -> Optional[Dict[str, Any]]:
        """
        Menerima satu sampel pembacaan baru dari S1 dan S4.
        
        Kembalian:
            Dict berisi detail kejadian gelombang jika puncak S4 berhasil dipasangkan
            dengan puncak S1 sebelumnya, atau None jika belum ada gelombang baru.
        """
        # 1. Cek rollback waktu (reboot ESP32)
        if t_s1_ms is not None and self.last_t_s1 is not None and t_s1_ms < self.last_t_s1:
            self.reset()
        if t_s4_ms is not None and self.last_t_s4 is not None and t_s4_ms < self.last_t_s4:
            self.reset()

        if t_s1_ms is not None:
            self.last_t_s1 = t_s1_ms
        if t_s4_ms is not None:
            self.last_t_s4 = t_s4_ms

        # 2. Masukkan sampel valid ke buffer sirkuler (maksimal simpan 10 titik)
        if t_s1_ms is not None and h_s1_cm is not None:
            self.buf_s1.append((t_s1_ms, float(h_s1_cm)))
            if len(self.buf_s1) > 10:
                self.buf_s1.pop(0)

        if t_s4_ms is not None and h_s4_cm is not None:
            self.buf_s4.append((t_s4_ms, float(h_s4_cm)))
            if len(self.buf_s4) > 10:
                self.buf_s4.pop(0)

        # 3. Deteksi apakah ada puncak baru di S1
        s1_peak = self._detect_peak(self.buf_s1, self.last_detected_peak_t_s1)
        if s1_peak is not None:
            t_pk, h_pk = s1_peak
            self.last_detected_peak_t_s1 = t_pk
            self.pending_s1_peaks.append((t_pk, h_pk))

        # Bersihkan pending S1 peaks yang sudah kedaluwarsa (> DT_MAKS_S dari waktu sekarang)
        current_time_ref = t_s4_ms if t_s4_ms is not None else (t_s1_ms or 0)
        self.pending_s1_peaks = [
            (tp, hp) for (tp, hp) in self.pending_s1_peaks
            if (current_time_ref - tp) <= self.dt_maks_ms
        ]

        # 4. Deteksi apakah ada puncak baru di S4
        s4_peak = self._detect_peak(self.buf_s4, self.last_detected_peak_t_s4)
        if s4_peak is None:
            return None

        t_s4_pk, h_s4_pk = s4_peak
        self.last_detected_peak_t_s4 = t_s4_pk

        # 5. Pasangkan puncak S4 ini dengan puncak S1 terdekat sebelumnya
        # Cari kandidat di pending_s1_peaks dengan t_s1_pk < t_s4_pk dan selisih <= dt_maks_ms
        best_candidate_idx = -1
        best_dt = 1e9

        for idx, (t_s1_pk, h_s1_pk) in enumerate(self.pending_s1_peaks):
            dt = t_s4_pk - t_s1_pk
            # Syarat fisik: gelombang merambat dari S1 ke S4 -> dt harus positif
            if 0 < dt <= self.dt_maks_ms:
                # Pilih yang paling mendekati (terdekat sebelum S4)
                if dt < best_dt:
                    best_dt = dt
                    best_candidate_idx = idx

        if best_candidate_idx == -1:
            # Tidak ditemukan pasangan puncak S1 yang cocok
            return None

        # Ambil pasangan terbaik dan hapus dari antrean agar tidak dipasangkan dua kali
        matched_t_s1_pk, matched_h_s1_pk = self.pending_s1_peaks.pop(best_candidate_idx)

        dt_ms = int(round(best_dt))
        dt_s = dt_ms / 1000.0

        if dt_s <= 0.0:
            return None

        # Kecepatan v = 75 / dt (cm/s)
        kecepatan_cms = round(self.jarak_s1_s4_cm / dt_s, 2)

        # Validasi rentang kecepatan (15 s/d 300 cm/s)
        is_valid = 1 if (self.v_min_cms <= kecepatan_cms <= self.v_maks_cms) else 0

        return {
            "t_s1_ms": int(round(matched_t_s1_pk)),
            "t_s4_ms": int(round(t_s4_pk)),
            "dt_ms": dt_ms,
            "puncak_s1_cm": round(matched_h_s1_pk, 2),
            "puncak_s4_cm": round(h_s4_pk, 2),
            "jarak_s1_s4_cm": self.jarak_s1_s4_cm,
            "kecepatan_cms": kecepatan_cms,
            "valid": is_valid,
        }

    def _detect_peak(self, buf: List[Tuple[int, float]], last_peak_t: float) -> Optional[Tuple[float, float]]:
        """
        Mengecek 3 sampel terakhir di buffer [t-2, t-1, t] apakah t-1 adalah puncak lokal.
        Syarat: h(t-1) >= ambang_puncak_cm, h(t-1) > h(t-2), h(t-1) >= h(t).
        """
        if len(buf) < 3:
            return None

        (t0, y0), (t1, y1), (t2, y2) = buf[-3], buf[-2], buf[-1]

        # Cek apakah titik tengah y1 adalah puncak lokal di atas ambang batas
        if y1 >= self.ambang_puncak_cm and y1 > y0 and y1 >= y2:
            # Cegah deteksi berulang pada puncak yang sama
            if (t1 - last_peak_t) < self.dead_time_ms:
                return None

            # Hitung vertex sub-sampel dengan aproksimasi parabola
            t_vertex, y_vertex = fit_parabola_vertex(float(t0), y0, float(t1), y1, float(t2), y2)
            return t_vertex, y_vertex

        return None
