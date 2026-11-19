"""
db.py — Pengelola Database SQLite untuk Sistem EWS Gelombang Air
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 5.6:
- Mode WAL aktif
- Tabel logs_sensor: tinggi_s4_cm & tinggi_global_cm (menggantikan ketinggian_cm)
- Tabel baru gelombang_event: mencatat kecepatan & puncak gelombang
- Tabel events: mencatat transisi pergantian level bahaya
"""

import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

import config


def get_connection() -> sqlite3.Connection:
    """Membuka koneksi SQLite dengan mode WAL dan format baris kamus (Row)."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    # Mode WAL: Pembaca (web) dan penulis (worker) tidak saling memblokir
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def init_db(reset: bool = False):
    """
    Menginisialisasi tabel-tabel database jika belum ada.
    Jika reset=True, menghapus tabel lama untuk migrasi bersih.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        if reset:
            cursor.execute("DROP TABLE IF EXISTS logs_sensor;")
            cursor.execute("DROP TABLE IF EXISTS gelombang_event;")
            cursor.execute("DROP TABLE IF EXISTS events;")

        # 1. Tabel utama deret waktu sensor (1 Hz)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs_sensor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_ms INTEGER NOT NULL,
                seq INTEGER,
                us1_cm REAL,
                us2_cm REAL,
                us3_cm REAL,
                us4_cm REAL,
                n_valid INTEGER,
                tinggi_s4_cm REAL,
                tinggi_global_cm REAL,
                debit_lpm REAL,
                nilai_fuzzy REAL,
                level TEXT,
                level_id INTEGER,
                sensor_ok INTEGER,
                sumber TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs_sensor(ts_ms);")

        # 2. Tabel kejadian gelombang (per kejadian deteksi puncak S1 -> S4)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gelombang_event (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_ms INTEGER NOT NULL,
                t_s1_ms INTEGER,
                t_s4_ms INTEGER,
                dt_ms INTEGER,
                puncak_s1_cm REAL,
                puncak_s4_cm REAL,
                jarak_s1_s4_cm REAL,
                kecepatan_cms REAL,
                valid INTEGER DEFAULT 1,
                sumber TEXT
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gelombang_ts ON gelombang_event(ts_ms);")

        # 3. Tabel riwayat kejadian perubahan level bahaya
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_ms INTEGER NOT NULL,
                level_dari TEXT,
                level_ke TEXT,
                nilai_fuzzy REAL
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_ms);")

        conn.commit()


def insert_log(record: Dict[str, Any]) -> int:
    """Menyimpan satu baris pembacaan data reguler ke logs_sensor."""
    sql = """
        INSERT INTO logs_sensor (
            ts_ms, seq, us1_cm, us2_cm, us3_cm, us4_cm,
            n_valid, tinggi_s4_cm, tinggi_global_cm, debit_lpm,
            nilai_fuzzy, level, level_id, sensor_ok, sumber
        ) VALUES (
            :ts_ms, :seq, :us1_cm, :us2_cm, :us3_cm, :us4_cm,
            :n_valid, :tinggi_s4_cm, :tinggi_global_cm, :debit_lpm,
            :nilai_fuzzy, :level, :level_id, :sensor_ok, :sumber
        )
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, record)
        conn.commit()
        return cursor.lastrowid


def insert_gelombang_event(record: Dict[str, Any]) -> int:
    """Menyimpan satu kejadian gelombang yang terdeteksi ke gelombang_event."""
    sql = """
        INSERT INTO gelombang_event (
            ts_ms, t_s1_ms, t_s4_ms, dt_ms,
            puncak_s1_cm, puncak_s4_cm, jarak_s1_s4_cm,
            kecepatan_cms, valid, sumber
        ) VALUES (
            :ts_ms, :t_s1_ms, :t_s4_ms, :dt_ms,
            :puncak_s1_cm, :puncak_s4_cm, :jarak_s1_s4_cm,
            :kecepatan_cms, :valid, :sumber
        )
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, record)
        conn.commit()
        return cursor.lastrowid


def insert_event(ts_ms: int, level_dari: str, level_ke: str, nilai_fuzzy: Optional[float]) -> int:
    """Mencatat perubahan level bahaya ke tabel events."""
    sql = """
        INSERT INTO events (ts_ms, level_dari, level_ke, nilai_fuzzy)
        VALUES (?, ?, ?, ?)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (ts_ms, level_dari, level_ke, nilai_fuzzy))
        conn.commit()
        return cursor.lastrowid


def get_latest_log() -> Optional[Dict[str, Any]]:
    """Mengambil rekaman data terbaru dari logs_sensor."""
    sql = "SELECT * FROM logs_sensor ORDER BY id DESC LIMIT 1"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_latest_gelombang(only_valid: bool = True) -> Optional[Dict[str, Any]]:
    """Mengambil kejadian gelombang terbaru."""
    where_clause = "WHERE valid = 1" if only_valid else ""
    sql = f"SELECT * FROM gelombang_event {where_clause} ORDER BY id DESC LIMIT 1"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None


def get_history(limit: int = 120, minutes: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Mengambil data riwayat logs_sensor urut dari waktu lampau ke terkini (ASC)
    untuk kebutuhan plotting grafik Chart.js.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        if minutes:
            cutoff_ms = int((time.time() - (minutes * 60)) * 1000)
            sql = """
                SELECT * FROM logs_sensor
                WHERE ts_ms >= ?
                ORDER BY ts_ms ASC
            """
            cursor.execute(sql, (cutoff_ms,))
        else:
            sql = """
                SELECT * FROM (
                    SELECT * FROM logs_sensor
                    ORDER BY id DESC
                    LIMIT ?
                ) ORDER BY id ASC
            """
            cursor.execute(sql, (limit,))

        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_recent_gelombang(limit: int = 50, only_valid: bool = True) -> List[Dict[str, Any]]:
    """
    Mengambil daftar kejadian gelombang terakhir urut menaik (ASC)
    untuk grafik tren kecepatan gelombang.
    """
    where_clause = "WHERE valid = 1" if only_valid else ""
    sql = f"""
        SELECT * FROM (
            SELECT * FROM gelombang_event
            {where_clause}
            ORDER BY id DESC
            LIMIT ?
        ) ORDER BY id ASC
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_recent_events(limit: int = 10) -> List[Dict[str, Any]]:
    """Mengambil riwayat transisi status level terakhir."""
    sql = "SELECT * FROM events ORDER BY id DESC LIMIT ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, (limit,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_db_stats() -> Dict[str, Any]:
    """Mengambil informasi ukuran berkas dan jumlah baris data (untuk /health)."""
    file_size_bytes = 0
    if config.DB_PATH.exists():
        file_size_bytes = config.DB_PATH.stat().st_size

    total_logs = 0
    total_gelombang = 0
    total_events = 0
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM logs_sensor")
        res = cursor.fetchone()
        if res:
            total_logs = res[0]

        cursor.execute("SELECT COUNT(*) FROM gelombang_event")
        res = cursor.fetchone()
        if res:
            total_gelombang = res[0]

        cursor.execute("SELECT COUNT(*) FROM events")
        res = cursor.fetchone()
        if res:
            total_events = res[0]

    return {
        "file_size_bytes": file_size_bytes,
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
        "total_logs": total_logs,
        "total_gelombang": total_gelombang,
        "total_events": total_events,
    }
