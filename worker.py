"""
worker.py — Proses 1: Pengambilan, Validasi, Kalibrasi, Inferensi Fuzzy, & Penyimpanan
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 5.1 & 5.5:
- Mengolah 3 jalur informasi dari 4 sensor:
  (A) Tinggi S4 -> Fuzzy Mamdani -> Level Bahaya (Fail-safe: S4 invalid -> TIDAK_VALID)
  (B) Tinggi Global maket -> Median/Rata-rata S1..S4 (monitoring stabilitas volume air)
  (C) Kecepatan Gelombang -> WaveSpeedTracker (v = 75 cm / dt) -> gelombang_event
- Berjalan mandiri di latar belakang, menyimpan ke SQLite (WAL mode).
"""

import statistics
import time
from typing import List, Optional, Dict, Any, Tuple

import config
import db
import fuzzy_engine
import sources
from wave_speed import WaveSpeedTracker

# Inisialisasi pelacak kecepatan gelombang global
_wave_tracker = WaveSpeedTracker()

# Buffer sirkuler lokal untuk median bergerak pembacaan S4 di Pi
_s4_history: List[float] = []


def process_telemetry(payload: dict,
                      tick: int,
                      last_level: Optional[str]) -> Tuple[str, Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Memproses satu paket telemetri:
    1. Validasi jarak & konversi ke ketinggian air: h = 48.0 - jarak
    2. Jalur A: Penghalusan S4 & inferensi Fuzzy Mamdani (fail-safe)
    3. Jalur B: Agregasi tinggi global maket (median S1..S4)
    4. Jalur C: Pelacakan puncak & kecepatan gelombang (v = 75 / dt)
    5. Penyusunan data untuk database logs_sensor & gelombang_event
    """
    ts_ms = int(time.time() * 1000)
    seq = payload.get("seq", tick)
    t_ms = payload.get("t_ms", [ts_ms, ts_ms + 30, ts_ms + 60, ts_ms + 90])
    us_readings = payload.get("us_cm", [None, None, None, None])
    flow_raw = payload.get("flow_lpm", 0.0)

    # 1. Validasi & Kalibrasi Jarak Sensor
    us_clean: List[Optional[float]] = []
    heights: List[Optional[float]] = []

    for i in range(4):
        d = us_readings[i] if i < len(us_readings) else None
        if d is not None and isinstance(d, (int, float)):
            if config.SENSOR_MIN_CM <= d <= config.SENSOR_MAX_CM:
                # Koreksi kalibrasi: y = a * x + b
                cal_d = (config.CAL_A_US[i] * float(d)) + config.CAL_B_US[i]
                us_clean.append(round(cal_d, 2))
                # Konversi jarak pantul ke tinggi muka air: h = 48.0 - jarak (K5)
                h_i = config.TINGGI_PASANG_CM - cal_d
                heights.append(round(h_i, 2))
            else:
                us_clean.append(None)
                heights.append(None)
        else:
            us_clean.append(None)
            heights.append(None)

    valid_heights = [h for h in heights if h is not None]
    n_valid = len(valid_heights)

    # 2. Kalibrasi Debit Air
    if flow_raw is not None and isinstance(flow_raw, (int, float)):
        if config.FLOW_MIN_LPM <= flow_raw <= config.FLOW_MAX_LPM:
            cal_flow = (config.CAL_A_FLOW * float(flow_raw)) + config.CAL_B_FLOW
            debit_lpm = round(max(0.0, min(config.FLOW_MAX_LPM, cal_flow)), 2)
        else:
            debit_lpm = None
    else:
        debit_lpm = None

    # ========================================================
    # JALUR A: TINGGI S4 & FUZZY MAMDANI (INPUT UTAMA FUZZY)
    # ========================================================
    h_s4_raw = heights[config.INDEKS_S4]
    tinggi_s4_cm: Optional[float] = None
    nilai_fuzzy: Optional[float] = None
    level: str = "TIDAK_VALID"
    level_id: Optional[int] = None
    sensor_ok: int = 0

    if h_s4_raw is not None and debit_lpm is not None:
        # Masukkan ke buffer median bergerak S4 (S4_MEDIAN_N = 3)
        _s4_history.append(h_s4_raw)
        if len(_s4_history) > config.S4_MEDIAN_N:
            _s4_history.pop(0)

        # Median S4
        tinggi_s4_cm = round(statistics.median(_s4_history), 2)
        # Batasi ke universe fisik (0 s/d 40 cm)
        tinggi_s4_cm = max(0.0, min(config.HEIGHT_UNIVERSE_MAX, tinggi_s4_cm))
        sensor_ok = 1

        # Inferensi Fuzzy Mamdani (Fungsi Murni)
        nilai_fuzzy, level, level_id = fuzzy_engine.evaluate_fuzzy(tinggi_s4_cm, debit_lpm)
    else:
        # Aturan #18 Fail-safe: S4 atau debit tidak valid -> TIDAK_VALID
        sensor_ok = 0
        tinggi_s4_cm = None
        nilai_fuzzy = None
        level = "TIDAK_VALID"
        level_id = None
        _s4_history.clear()

    # ========================================================
    # JALUR B: TINGGI GLOBAL MAKET (VOLUME TOTAL AIR)
    # ========================================================
    tinggi_global_cm: Optional[float] = None
    if n_valid >= config.MIN_SENSOR_VALID:
        if config.AGREGASI_GLOBAL == "median":
            tinggi_global_cm = round(statistics.median(valid_heights), 2)
        else:
            tinggi_global_cm = round(sum(valid_heights) / n_valid, 2)
    else:
        tinggi_global_cm = None

    # ========================================================
    # JALUR C: KECEPATAN GELOMBANG (v = 75 / dt)
    # ========================================================
    t_s1 = t_ms[0] if len(t_ms) > 0 else None
    t_s4 = t_ms[config.INDEKS_S4] if len(t_ms) > config.INDEKS_S4 else None
    h_s1 = heights[0]
    h_s4 = heights[config.INDEKS_S4]

    wave_event = _wave_tracker.process_sample(t_s1, h_s1, t_s4, h_s4)
    if wave_event is not None:
        wave_event["ts_ms"] = ts_ms
        wave_event["sumber"] = config.DATA_SOURCE
        # Catat kejadian gelombang ke tabel gelombang_event
        db.insert_gelombang_event(wave_event)

    # 3. Susun rekaman log sensor untuk tabel logs_sensor
    record = {
        "ts_ms": ts_ms,
        "seq": seq,
        "us1_cm": us_clean[0],
        "us2_cm": us_clean[1],
        "us3_cm": us_clean[2],
        "us4_cm": us_clean[3],
        "n_valid": n_valid,
        "tinggi_s4_cm": tinggi_s4_cm,
        "tinggi_global_cm": tinggi_global_cm,
        "debit_lpm": debit_lpm,
        "nilai_fuzzy": nilai_fuzzy,
        "level": level,
        "level_id": level_id,
        "sensor_ok": sensor_ok,
        "sumber": config.DATA_SOURCE,
    }

    # 4. Catat ke tabel events bila status level berubah
    if last_level is not None and level != last_level:
        db.insert_event(ts_ms, last_level, level, nilai_fuzzy)

    return level, record, wave_event


def run_worker():
    """Fungsi utama menjalankan loop worker."""
    print("==================================================")
    print("  EWS GELOMBANG AIR — PROSES WORKER (SENSOR FUSION)")
    print("==================================================")
    print(f"[*] Sumber Data : {config.DATA_SOURCE.upper()}")
    if config.DATA_SOURCE == "sim":
        print(f"[*] Skenario    : {config.SIM_SCENARIO}")
    print(f"[*] Interval    : {config.WORKER_INTERVAL_S} detik (log: {config.LOG_INTERVAL_S} s)")
    print(f"[*] Database    : {config.DB_PATH}")
    print("[*] Menginisialisasi skema database SQLite...")
    db.init_db()
    print("[*] Database siap. Memulai pemrosesan data (Tekan Ctrl+C untuk berhenti)...\n")

    tick = 0
    last_level: Optional[str] = None
    last_log_time = 0.0
    mqtt_source = None

    if config.DATA_SOURCE == "mqtt":
        mqtt_source = sources.MQTTTelemetrySource()
        mqtt_source.start()

    try:
        while True:
            t_start = time.time()

            # 1. Ambil data sesuai sumber
            if config.DATA_SOURCE == "sim":
                payload = sources.generate_simulated_payload(config.SIM_SCENARIO, tick)
            else:
                # Mode MQTT: ambil dari antrean (tunggu maksimal 0.1 detik)
                payload = mqtt_source.get_payload(timeout=0.1)
                if payload is None:
                    # Tidak ada pesan baru; jangan tulis nilai palsu
                    continue

            # 2. Proses data 3 jalur (A, B, C)
            current_level, rec, wave_event = process_telemetry(payload, tick, last_level)
            last_level = current_level

            # 3. Penurunan laju penyimpanan: simpan ke logs_sensor tiap LOG_INTERVAL_S
            now_sec = time.time()
            if (now_sec - last_log_time) >= config.LOG_INTERVAL_S:
                db.insert_log(rec)
                last_log_time = now_sec

                # Cetak log status di konsol
                s4_str = f"{rec['tinggi_s4_cm']:.1f} cm" if rec['tinggi_s4_cm'] is not None else "-- cm"
                glb_str = f"{rec['tinggi_global_cm']:.1f} cm" if rec['tinggi_global_cm'] is not None else "-- cm"
                q_str = f"{rec['debit_lpm']:.1f} L/m" if rec['debit_lpm'] is not None else "-- L/m"
                fz_str = f"{rec['nilai_fuzzy']:.1f}" if rec['nilai_fuzzy'] is not None else "--"

                wv_info = ""
                if wave_event is not None:
                    wv_info = f" | [GELOMBANG! v={wave_event['kecepatan_cms']} cm/s]"

                print(f"[{time.strftime('%H:%M:%S')}] Seq:{rec['seq']:<4} | Valid:{rec['n_valid']}/4 | "
                      f"S4:{s4_str:<7} | Maket:{glb_str:<7} | Debit:{q_str:<7} | Fuzzy:{fz_str:<5} | Level:{rec['level']}{wv_info}")

            tick += 1

            # Jaga interval eksekusi pada mode simulator (di MQTT mengikuti laju pesan ESP32)
            if config.DATA_SOURCE == "sim":
                elapsed = time.time() - t_start
                sleep_time = max(0.02, config.WORKER_INTERVAL_S - elapsed)
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[!] Worker dihentikan oleh pengguna.")
    finally:
        if mqtt_source is not None:
            mqtt_source.stop()


if __name__ == "__main__":
    run_worker()
