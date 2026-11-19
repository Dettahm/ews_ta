"""
app.py — Server Web Flask: Dashboard & API JSON Read-Only
Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) Bagian 5.7 & Aturan #8:
- Semua endpoint bersifat GET dan read-only (monitoring murni).
- Menyediakan endpoint /api/now, /api/history, /api/gelombang, /api/events,
  /api/export.csv, /api/export_gelombang.csv, dan /health.
"""

import csv
import io
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, Response

import config
import db

app = Flask(__name__)
server_start_time = time.time()


@app.route("/")
def index():
    """Menyajikan halaman antarmuka web dashboard EWS."""
    return render_template(
        "index.html",
        poll_interval_ms=config.POLL_INTERVAL_MS,
        stale_after_s=config.STALE_AFTER_S,
        levels=config.LEVELS,
    )


@app.route("/api/now")
def api_now():
    """
    Endpoint JSON data telemetri terkini.
    Dipanggil oleh frontend secara polling tiap 2 detik.
    """
    latest = db.get_latest_log()
    latest_wave = db.get_latest_gelombang(only_valid=True)
    now_ms = int(time.time() * 1000)

    if not latest:
        return jsonify({
            "online": False,
            "age_s": None,
            "data": None,
            "status_label": "OFFLINE",
            "bg_color": config.LEVELS["OFFLINE"]["bg_color"],
            "text_color": config.LEVELS["OFFLINE"]["text_color"],
            "tinggi_s4_cm": None,
            "tinggi_global_cm": None,
            "debit_lpm": None,
            "nilai_fuzzy": None,
            "kecepatan_terakhir_cms": None,
            "kecepatan_terakhir_age_s": None,
            "arah_bahaya": None,
            "stabilitas_global": "OFFLINE",
        })

    age_s = round((now_ms - latest["ts_ms"]) / 1000.0, 1)
    is_online = age_s <= config.STALE_AFTER_S

    level_name = latest["level"] if is_online else "OFFLINE"
    lvl_info = config.LEVELS.get(level_name, config.LEVELS["OFFLINE"])

    # Label arah anomali tsunami khusus level BAHAYA (Bagian 6.2)
    arah_bahaya = None
    if is_online and level_name == "BAHAYA" and latest["tinggi_s4_cm"] is not None:
        if latest["tinggi_s4_cm"] < 11.0:
            arah_bahaya = "SURUT"
        elif latest["tinggi_s4_cm"] > 22.0:
            arah_bahaya = "LUAPAN"

    # Evaluasi stabilitas tinggi global maket (indikasi kebocoran/luapan tangki)
    stabilitas_global = "STABIL"
    if is_online and latest["tinggi_global_cm"] is not None:
        # Periksa deviasi terhadap level air tenang acuan maket (15 cm)
        delta_global = latest["tinggi_global_cm"] - 15.0
        if delta_global <= -config.GLOBAL_STABILITY_THRESHOLD_CM:
            stabilitas_global = "TURUN"
        elif delta_global >= config.GLOBAL_STABILITY_THRESHOLD_CM:
            stabilitas_global = "NAIK"

    # Data kecepatan gelombang terakhir
    kecepatan_cms = None
    kecepatan_age_s = None
    kecepatan_dt_ms = None
    if latest_wave is not None:
        kecepatan_cms = latest_wave["kecepatan_cms"]
        kecepatan_age_s = round((now_ms - latest_wave["ts_ms"]) / 1000.0, 1)
        kecepatan_dt_ms = latest_wave["dt_ms"]

    # Format timestamp lokal WIB (UTC+7)
    dt_wib = datetime.fromtimestamp(latest["ts_ms"] / 1000.0)
    time_str = dt_wib.strftime("%H:%M:%S WIB")

    return jsonify({
        "online": is_online,
        "age_s": age_s,
        "time_str": time_str,
        "level": level_name,
        "level_id": latest["level_id"] if is_online else None,
        "bg_color": lvl_info["bg_color"],
        "text_color": lvl_info["text_color"],
        "tinggi_s4_cm": latest["tinggi_s4_cm"] if is_online else None,
        "tinggi_global_cm": latest["tinggi_global_cm"] if is_online else None,
        "debit_lpm": latest["debit_lpm"] if is_online else None,
        "nilai_fuzzy": latest["nilai_fuzzy"] if is_online else None,
        "arah_bahaya": arah_bahaya,
        "stabilitas_global": stabilitas_global if is_online else "OFFLINE",
        "kecepatan_terakhir_cms": kecepatan_cms,
        "kecepatan_terakhir_age_s": kecepatan_age_s,
        "kecepatan_terakhir_dt_ms": kecepatan_dt_ms,
        "n_valid": latest["n_valid"],
        "sensor_ok": latest["sensor_ok"],
        "seq": latest["seq"],
        "sumber": latest["sumber"],
    })


@app.route("/api/history")
def api_history():
    """
    Mengambil data riwayat logs_sensor untuk inisialisasi & pembaruan grafik utama Chart.js.
    Format sumbu waktu teks 'HH:MM:SS'.
    """
    limit = request.args.get("limit", default=config.HISTORY_MAX_POINTS, type=int)
    minutes = request.args.get("minutes", default=None, type=int)

    # Batasi limit maksimum agar browser tetap ringan
    limit = min(limit, 600)
    rows = db.get_history(limit=limit, minutes=minutes)

    labels = []
    tinggi_s4_data = []
    tinggi_global_data = []
    debit_data = []
    fuzzy_data = []

    for r in rows:
        dt = datetime.fromtimestamp(r["ts_ms"] / 1000.0)
        labels.append(dt.strftime("%H:%M:%S"))
        tinggi_s4_data.append(r["tinggi_s4_cm"])
        tinggi_global_data.append(r["tinggi_global_cm"])
        debit_data.append(r["debit_lpm"])
        fuzzy_data.append(r["nilai_fuzzy"])

    return jsonify({
        "labels": labels,
        "tinggi_s4": tinggi_s4_data,
        "tinggi_global": tinggi_global_data,
        "debit": debit_data,
        "fuzzy": fuzzy_data,
        "count": len(rows),
    })


@app.route("/api/gelombang")
def api_gelombang():
    """
    Mengambil daftar kejadian gelombang valid terakhir untuk grafik tren kecepatan gelombang.
    """
    limit = request.args.get("limit", default=config.GELOMBANG_MAX_POINTS, type=int)
    limit = min(limit, 200)
    events = db.get_recent_gelombang(limit=limit, only_valid=True)

    result = []
    for ev in events:
        dt = datetime.fromtimestamp(ev["ts_ms"] / 1000.0)
        result.append({
            "id": ev["id"],
            "time_str": dt.strftime("%H:%M:%S"),
            "kecepatan_cms": ev["kecepatan_cms"],
            "dt_ms": ev["dt_ms"],
            "puncak_s1_cm": ev["puncak_s1_cm"],
            "puncak_s4_cm": ev["puncak_s4_cm"],
            "valid": ev["valid"],
        })
    return jsonify(result)


@app.route("/api/events")
def api_events():
    """Mengambil riwayat pergantian level bahaya terbaru."""
    limit = request.args.get("limit", default=10, type=int)
    events = db.get_recent_events(limit=limit)

    result = []
    for ev in events:
        dt = datetime.fromtimestamp(ev["ts_ms"] / 1000.0)
        result.append({
            "id": ev["id"],
            "time_str": dt.strftime("%H:%M:%S"),
            "level_dari": ev["level_dari"],
            "level_ke": ev["level_ke"],
            "nilai_fuzzy": ev["nilai_fuzzy"],
        })
    return jsonify(result)


@app.route("/api/export.csv")
def api_export_csv():
    """Mengekspor seluruh riwayat telemetri logs_sensor ke format CSV untuk analisis Excel."""
    rows = db.get_history(limit=10000)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp_utc_ms", "waktu_wib", "seq",
        "us1_cm", "us2_cm", "us3_cm", "us4_cm", "sensor_valid",
        "tinggi_s4_cm", "tinggi_global_cm", "debit_lpm", "nilai_fuzzy",
        "level", "sumber"
    ])

    for r in rows:
        dt_wib = datetime.fromtimestamp(r["ts_ms"] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([
            r["id"], r["ts_ms"], dt_wib, r["seq"],
            r["us1_cm"], r["us2_cm"], r["us3_cm"], r["us4_cm"], r["n_valid"],
            r["tinggi_s4_cm"], r["tinggi_global_cm"], r["debit_lpm"], r["nilai_fuzzy"],
            r["level"], r["sumber"]
        ])

    csv_data = output.getvalue()
    filename = f"ews_telemetri_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/export_gelombang.csv")
def api_export_gelombang_csv():
    """Mengekspor data kejadian gelombang (gelombang_event) ke format CSV."""
    rows = db.get_recent_gelombang(limit=5000, only_valid=False)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp_utc_ms", "waktu_wib",
        "t_s1_ms", "t_s4_ms", "dt_ms",
        "puncak_s1_cm", "puncak_s4_cm", "jarak_s1_s4_cm",
        "kecepatan_cms", "valid", "sumber"
    ])

    for r in rows:
        dt_wib = datetime.fromtimestamp(r["ts_ms"] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([
            r["id"], r["ts_ms"], dt_wib,
            r["t_s1_ms"], r["t_s4_ms"], r["dt_ms"],
            r["puncak_s1_cm"], r["puncak_s4_cm"], r["jarak_s1_s4_cm"],
            r["kecepatan_cms"], r["valid"], r["sumber"]
        ])

    csv_data = output.getvalue()
    filename = f"ews_gelombang_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/health")
def health():
    """Pemeriksaan kesehatan sistem (status proses, uptime, umur data, ukuran database)."""
    latest = db.get_latest_log()
    now_ms = int(time.time() * 1000)
    stats = db.get_db_stats()

    age_s = round((now_ms - latest["ts_ms"]) / 1000.0, 1) if latest else None
    uptime_s = int(time.time() - server_start_time)

    return jsonify({
        "status": "ok",
        "uptime_seconds": uptime_s,
        "latest_data_age_seconds": age_s,
        "database": stats,
    })


if __name__ == "__main__":
    db.init_db()
    print("==================================================")
    print("  EWS GELOMBANG AIR — SERVER WEB FLASK (SENSOR FUSION)")
    print("==================================================")
    print("Dashboard dapat diakses di: http://127.0.0.1:5000")
    print("Mode: Produksi/Lokal (Debug dimatikan)")
    print("Tekan Ctrl+C untuk menghentikan server.\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
