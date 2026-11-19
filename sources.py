"""
sources.py — Sumber Data: Simulator Sensor & Pembacaan
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 5.3 & 5.5:
- Kontrak payload mencakup t_ms per sensor (larik 4 elemen) untuk estimasi kecepatan gelombang sub-sampel
- 8 skenario pengujian komprehensif (tenang, naik_perlahan, surut_ekstrem, luapan_ekstrem,
  gelombang_lewat, gelombang_noise, sensor_error, kebocoran_pelan)
"""

import math
import random
import time
from typing import Dict, Any, List, Optional

import config

_start_time = time.time()


def generate_simulated_payload(scenario: str, tick: int) -> Dict[str, Any]:
    """
    Menghasilkan satu payload telemetri tiruan sesuai kontrak JSON Bagian 5.5:
    {"seq": int, "t_ms": [t1, t2, t3, t4], "us_cm": [us1, us2, us3, us4], "flow_lpm": float}

    Catatan Fisik:
    - S1 di posisi pembangkit gelombang (d=0 cm), S4 di posisi pesisir (d=75 cm).
    - Tinggi pasang sensor = 48.0 cm dari dasar akuarium.
    - jarak_pantul (cm) = TINGGI_PASANG_CM (48.0) - ketinggian_air (cm).
    """
    seq = tick
    # Jam ESP32 (milidetik sejak boot): gunakan kombinasi jam dinding dan tick virtual
    now_ms = int((time.time() - _start_time) * 1000)
    virtual_ms = tick * int(config.WORKER_INTERVAL_S * 1000)
    clock_ms = max(now_ms, virtual_ms)

    # ESP32 membaca 4 sensor bergantian dengan jeda ~30 ms antar sensor
    t_ms = [
        clock_ms,
        clock_ms + 30,
        clock_ms + 60,
        clock_ms + 90,
    ]

    # Level air dasar (air tenang maket sekitar 15 cm)
    base_water_level = 15.0

    # 1. Hitung ketinggian air (cm) per sensor dan debit (L/mnt) berdasarkan skenario
    if scenario == "tenang":
        # S1–S4 ~ 15 cm (noise kecil), debit rendah (2 - 4 L/mnt) -> AMAN (R1)
        h_s1 = base_water_level + random.uniform(-0.2, 0.2)
        h_s2 = base_water_level + random.uniform(-0.2, 0.2)
        h_s3 = base_water_level + random.uniform(-0.2, 0.2)
        h_s4 = base_water_level + random.uniform(-0.2, 0.2)
        flow_lpm = 3.0 + random.uniform(-0.2, 0.2)

    elif scenario == "naik_perlahan":
        # Ketinggian naik bertahap dari 15 cm ke 21 cm, debit naik pelan
        # AMAN -> WASPADA -> SIAGA
        cycle_pos = (tick % 40) / 40.0
        h_target = 15.0 + (cycle_pos * 6.5) + random.uniform(-0.2, 0.2)
        h_s1 = h_target + random.uniform(-0.2, 0.2)
        h_s2 = h_target + random.uniform(-0.2, 0.2)
        h_s3 = h_target + random.uniform(-0.2, 0.2)
        h_s4 = h_target + random.uniform(-0.2, 0.2)
        flow_lpm = 2.0 + (cycle_pos * 14.0) + random.uniform(-0.3, 0.3)

    elif scenario == "surut_ekstrem":
        # Anomali surut tsunami: S4 turun di bawah 11 cm (< 11 cm)
        # Sesuai aturan R7 (SIAGA jika debit rendah) dan R8 (BAHAYA jika debit sedang)
        step = tick % 30
        if step < 8:
            h_s4 = 15.0 + random.uniform(-0.3, 0.3)
            flow_lpm = 3.0 + random.uniform(-0.2, 0.2)
        else:
            # Air di pesisir surut drastis ke 7 - 9 cm
            h_s4 = 8.5 + random.uniform(-0.4, 0.4)
            flow_lpm = 11.0 + random.uniform(-0.5, 0.5)
        h_s1 = 15.0 + random.uniform(-0.3, 0.3)
        h_s2 = 14.5 + random.uniform(-0.3, 0.3)
        h_s3 = 12.0 + random.uniform(-0.3, 0.3)

    elif scenario == "luapan_ekstrem":
        # Anomali luapan tsunami: S4 melonjak di atas 22 cm (> 22 cm)
        # Sesuai aturan R8/R9 (BAHAYA)
        step = tick % 30
        if step < 6:
            h_s4 = 15.0 + random.uniform(-0.3, 0.3)
            flow_lpm = 5.0 + random.uniform(-0.3, 0.3)
        else:
            h_s4 = 25.5 + random.uniform(-0.5, 0.5)
            flow_lpm = 22.0 + random.uniform(-0.8, 0.8)
        h_s1 = 20.0 + random.uniform(-0.4, 0.4)
        h_s2 = 22.0 + random.uniform(-0.4, 0.4)
        h_s3 = 24.0 + random.uniform(-0.4, 0.4)

    elif scenario == "gelombang_lewat":
        # Pulsa gelombang puncak >= 20 cm merambat dari S1 ke S4
        # Kecepatan gelombang v = 100 cm/s (dt = 0.75 s antara S1 dan S4 sejauh 75 cm)
        # Siklus gelombang periodik setiap 15 detik (atau 15 tick jika 1 tick = 1 s, atau sub-detik)
        period_ms = 12000
        t_in_period = now_ms % period_ms

        # Gelombang diluncurkan pada ms ke 2000 dalam tiap periode
        t0 = 2000
        v_cms = 100.0  # 100 cm/s = 0.1 cm/ms
        sigma_ms = 250.0  # Lebar pulsa Gaussian

        # Jarak sensor dari S1: S1=0, S2=25, S3=50, S4=75 cm
        distances = [0.0, 25.0, 50.0, 75.0]
        heights = []
        for i, dist in enumerate(distances):
            # Waktu tiba puncak di sensor i = t0 + (dist / v_cms * 1000)
            t_arrival = t0 + (dist / v_cms * 1000.0)
            t_sensor = t_ms[i] % period_ms
            dt_pulse = t_sensor - t_arrival

            # Puncak Gaussian setinggi 9 cm di atas air tenang 15 cm -> Puncak 24 cm
            pulse = 9.0 * math.exp(-((dt_pulse / sigma_ms) ** 2))
            heights.append(base_water_level + pulse + random.uniform(-0.2, 0.2))

        h_s1, h_s2, h_s3, h_s4 = heights
        flow_lpm = 8.0 + random.uniform(-0.3, 0.3)

    elif scenario == "gelombang_noise":
        # Osilasi kecil dengan puncak < 20 cm + noise, tidak boleh memicu deteksi kecepatan
        wave_comp = math.sin(tick * 0.5) * 2.5  # Amplitudo 2.5 cm -> Ketinggian 12.5 s/d 17.5 cm
        h_s1 = base_water_level + wave_comp + random.uniform(-0.5, 0.5)
        h_s2 = base_water_level + wave_comp + random.uniform(-0.5, 0.5)
        h_s3 = base_water_level + wave_comp + random.uniform(-0.5, 0.5)
        h_s4 = base_water_level + wave_comp + random.uniform(-0.5, 0.5)
        flow_lpm = 6.0 + random.uniform(-0.4, 0.4)

    elif scenario == "sensor_error":
        # S4 bernilai None (kegagalan sensor pesisir) atau sensor lain error acak
        h_s1 = base_water_level + random.uniform(-0.3, 0.3)
        h_s2 = base_water_level + random.uniform(-0.3, 0.3)
        h_s3 = base_water_level + random.uniform(-0.3, 0.3)
        h_s4 = None  # S4 mati -> Aturan #18: harus menghasilkan level TIDAK_VALID
        flow_lpm = 7.0 + random.uniform(-0.2, 0.2)

    elif scenario == "kebocoran_pelan":
        # Seluruh sensor perlahan turun dari 15 cm ke 9 cm (indikasi tangki bocor)
        decay = min(1.0, (tick % 60) / 50.0)
        h_target = 15.0 - (decay * 6.0) + random.uniform(-0.2, 0.2)
        h_s1 = h_target + random.uniform(-0.2, 0.2)
        h_s2 = h_target + random.uniform(-0.2, 0.2)
        h_s3 = h_target + random.uniform(-0.2, 0.2)
        h_s4 = h_target + random.uniform(-0.2, 0.2)
        flow_lpm = 2.0 + random.uniform(-0.2, 0.2)

    else:
        # Fallback kondisi tenang
        h_s1 = h_s2 = h_s3 = h_s4 = base_water_level
        flow_lpm = 3.0

    # 2. Konversi ketinggian (cm) ke jarak pantul sensor (cm): jarak = 48.0 - tinggi
    us_readings: List[Optional[float]] = []
    for h in [h_s1, h_s2, h_s3, h_s4]:
        if h is None:
            us_readings.append(None)
        else:
            # Batasi tinggi fisik ke rentang 0 s/d 45 cm
            clamped_h = max(0.0, min(45.0, h))
            distance = round(config.TINGGI_PASANG_CM - clamped_h, 2)
            # Pastikan berada di rentang fisik sensor
            if config.SENSOR_MIN_CM <= distance <= config.SENSOR_MAX_CM:
                us_readings.append(distance)
            else:
                us_readings.append(None)

    flow_lpm = round(max(0.0, min(config.FLOW_MAX_LPM, flow_lpm)), 2)

    return {
        "seq": seq,
        "t_ms": t_ms,
        "us_cm": us_readings,
        "flow_lpm": flow_lpm,
    }
