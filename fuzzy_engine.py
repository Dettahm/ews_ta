"""
fuzzy_engine.py — Modul Logika Fuzzy Mamdani Murni
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 7 Fase 3 & Aturan #7, #17, #18, #20:
- Input 1: tinggi_s4_cm (Sensor 4 pesisir saja)
- Input 2: debit_lpm (Flowmeter)
- Output: nilai_bahaya (0 s/d 100) -> 4 level tegas (AMAN, WASPADA, SIAGA, BAHAYA)
- Himpunan Ketinggian S4: BAHAYA double trapezoid (surut ekstrem < 11 cm & luapan ekstrem > 22 cm)
- 9 Aturan Mitigasi Tsunami (R1 s/d R9)
- Fungsi murni tanpa akses database atau I/O, dibangun sekali (built once).
"""

import math
from typing import Tuple, Optional
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

import config

# Inisialisasi variabel semesta (Universe of Discourse)
_height_universe = np.arange(
    config.HEIGHT_UNIVERSE_MIN,
    config.HEIGHT_UNIVERSE_MAX + config.HEIGHT_UNIVERSE_STEP,
    config.HEIGHT_UNIVERSE_STEP
)

_flow_universe = np.arange(
    config.FLOW_UNIVERSE_MIN,
    config.FLOW_UNIVERSE_MAX + config.FLOW_UNIVERSE_STEP,
    config.FLOW_UNIVERSE_STEP
)

_danger_universe = np.arange(
    config.DANGER_UNIVERSE_MIN,
    config.DANGER_UNIVERSE_MAX + config.DANGER_UNIVERSE_STEP,
    config.DANGER_UNIVERSE_STEP
)

# Definisi Antecedent (Input) & Consequent (Output)
_var_height = ctrl.Antecedent(_height_universe, 'tinggi_s4')
_var_flow = ctrl.Antecedent(_flow_universe, 'debit')
_var_danger = ctrl.Consequent(_danger_universe, 'bahaya', defuzzify_method='centroid')

# ==========================================
# 1. FUNGSI KEANGGOTAAN KETINGGIAN S4 (INPUT 1)
# ==========================================
# BAHAYA: Double trapezoid (gabungan max trapesium surut ekstrem dan luapan ekstrem)
_trap_kiri = fuzz.trapmf(_height_universe, config.MF_HEIGHT_S4['bahaya_kiri'])
_trap_kanan = fuzz.trapmf(_height_universe, config.MF_HEIGHT_S4['bahaya_kanan'])
_var_height['bahaya'] = np.maximum(_trap_kiri, _trap_kanan)

# AMAN: Trapesium sekitar air tenang maket (~15 cm)
_var_height['aman'] = fuzz.trapmf(_height_universe, config.MF_HEIGHT_S4['aman'])

# WASPADA: Segitiga kenaikan air menuju luapan
_var_height['waspada'] = fuzz.trimf(_height_universe, config.MF_HEIGHT_S4['waspada'])

# ==========================================
# 2. FUNGSI KEANGGOTAAN DEBIT AIR (INPUT 2)
# ==========================================
_var_flow['rendah'] = fuzz.trapmf(_flow_universe, config.MF_FLOW['rendah'])
_var_flow['sedang'] = fuzz.trimf(_flow_universe, config.MF_FLOW['sedang'])
_var_flow['tinggi'] = fuzz.trapmf(_flow_universe, config.MF_FLOW['tinggi'])

# ==========================================
# 3. FUNGSI KEANGGOTAAN NILAI BAHAYA (OUTPUT)
# ==========================================
_var_danger['aman']    = fuzz.trimf(_danger_universe, config.MF_DANGER['aman'])
_var_danger['waspada'] = fuzz.trimf(_danger_universe, config.MF_DANGER['waspada'])
_var_danger['siaga']   = fuzz.trimf(_danger_universe, config.MF_DANGER['siaga'])
_var_danger['bahaya']  = fuzz.trimf(_danger_universe, config.MF_DANGER['bahaya'])

# ==========================================
# 4. BASIS 9 ATURAN MITIGASI TSUNAMI (K9, FASE 3)
# ==========================================
_rules = [
    ctrl.Rule(_var_height['aman'] & _var_flow['rendah'], _var_danger['aman']),     # R1
    ctrl.Rule(_var_height['aman'] & _var_flow['sedang'], _var_danger['waspada']),  # R2
    ctrl.Rule(_var_height['aman'] & _var_flow['tinggi'], _var_danger['siaga']),    # R3 (Anomali arus bawah)
    ctrl.Rule(_var_height['waspada'] & _var_flow['rendah'], _var_danger['waspada']),# R4
    ctrl.Rule(_var_height['waspada'] & _var_flow['sedang'], _var_danger['siaga']),  # R5
    ctrl.Rule(_var_height['waspada'] & _var_flow['tinggi'], _var_danger['bahaya']), # R6 (Tsunami bore)
    ctrl.Rule(_var_height['bahaya'] & _var_flow['rendah'], _var_danger['siaga']),   # R7 (Transisi surut)
    ctrl.Rule(_var_height['bahaya'] & _var_flow['sedang'], _var_danger['bahaya']),  # R8
    ctrl.Rule(_var_height['bahaya'] & _var_flow['tinggi'], _var_danger['bahaya']),  # R9 (Hantaman tsunami)
]

# Bangun sistem kendali fuzzy sekali saat aplikasi dimulai
_fuzzy_ctrl = ctrl.ControlSystem(_rules)
_fuzzy_sim = ctrl.ControlSystemSimulation(_fuzzy_ctrl)


def evaluate_fuzzy(tinggi_s4_cm: Optional[float], debit_lpm: Optional[float]) -> Tuple[Optional[float], str, Optional[int]]:
    """
    Menghitung inferensi Fuzzy Mamdani berdasarkan ketinggian Sensor 4 dan debit air.

    Parameter:
        tinggi_s4_cm (float): Tinggi air pada Sensor 4 (cm)
        debit_lpm (float): Debit air (Liter/menit)

    Kembalian:
        tuple: (nilai_fuzzy: float, level: str, level_id: int)
        Jika input tidak valid: (None, "TIDAK_VALID", None)
    """
    # 1. Validasi fail-safe (Aturan #9, #10, #18)
    if tinggi_s4_cm is None or debit_lpm is None:
        return None, "TIDAK_VALID", None

    try:
        tinggi_val = float(tinggi_s4_cm)
        debit_val = float(debit_lpm)

        if math.isnan(tinggi_val) or math.isnan(debit_val) or math.isinf(tinggi_val) or math.isinf(debit_val):
            return None, "TIDAK_VALID", None

        # 2. Batasi (clamp) ke universe fuzzy
        clamped_h = max(config.HEIGHT_UNIVERSE_MIN, min(config.HEIGHT_UNIVERSE_MAX, tinggi_val))
        clamped_f = max(config.FLOW_UNIVERSE_MIN, min(config.FLOW_UNIVERSE_MAX, debit_val))

        # 3. Hitung inferensi fuzzy
        _fuzzy_sim.input['tinggi_s4'] = clamped_h
        _fuzzy_sim.input['debit'] = clamped_f
        _fuzzy_sim.compute()

        score = float(_fuzzy_sim.output['bahaya'])
        score = round(max(0.0, min(100.0, score)), 1)

        # 4. Pemetaan nilai tegas ke 4 Level Klasifikasi (Bagian 7 Fase 3)
        if score < 25.0:
            level = "AMAN"
            level_id = config.LEVELS["AMAN"]["id"]
        elif score < 50.0:
            level = "WASPADA"
            level_id = config.LEVELS["WASPADA"]["id"]
        elif score < 75.0:
            level = "SIAGA"
            level_id = config.LEVELS["SIAGA"]["id"]
        else:
            level = "BAHAYA"
            level_id = config.LEVELS["BAHAYA"]["id"]

        return score, level, level_id

    except Exception:
        # Penanganan error jika output defuzzifikasi tidak terdefinisi
        return None, "TIDAK_VALID", None
