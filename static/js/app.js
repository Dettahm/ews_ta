/**
 * app.js — Penggerak Frontend Dashboard IoT EWS Gelombang Air
 * Sesuai PROJECT_SPEC_BARU.md v1.1 (Sensor Fusion) & Bagian 6:
 * - Polling 2 detik ke /api/now tanpa reload halaman
 * - 6 Kartu metrik: S4, Debit, Nilai Fuzzy, Status Bahaya (Arah Surut/Luapan),
 *   Tinggi Global (Badge Stabilitas), Kecepatan Gelombang Terakhir
 * - Grafik utama dual Y-axis: Tinggi S4 (Biru), Tinggi Global (Ungu), Debit (Cyan)
 * - Grafik sekunder: Indeks Risiko Fuzzy (0-100) & Tren Kecepatan Gelombang (cm/s)
 * - Fail-safe: jika data terlambat / terputus, kartu berubah OFFLINE abu-abu
 */

document.addEventListener("DOMContentLoaded", function () {
    // 1. ELEMEN DOM
    const connBadge = document.getElementById("conn-badge");
    const clockWib = document.getElementById("clock-wib");
    const dataAgeInfo = document.getElementById("data-age-info");
    const valHeightS4 = document.getElementById("val-height-s4");
    const valFlow = document.getElementById("val-flow");
    const valFuzzy = document.getElementById("val-fuzzy");
    const valStatus = document.getElementById("val-status");
    const valSource = document.getElementById("val-source");
    const statusCard = document.getElementById("status-card");
    const badgeArah = document.getElementById("badge-arah");
    const valHeightGlobal = document.getElementById("val-height-global");
    const badgeStabilitas = document.getElementById("badge-stabilitas");
    const valWaveSpeed = document.getElementById("val-wave-speed");
    const valWaveInfo = document.getElementById("val-wave-info");
    const sensorCountInfo = document.getElementById("sensor-count-info");
    const eventsList = document.getElementById("events-list");
    const rangeButtons = document.querySelectorAll(".range-btn");

    let lastLevel = null;
    let lastWaveTimestamp = null;
    let mainChart = null;
    let fuzzyChart = null;
    let waveChart = null;
    let activeLimit = 120;
    let activeMinutes = null;

    // 2. INISIALISASI GRAFIK UTAMA (S4, GLOBAL MAKET, & DEBIT AIR — DUAL Y-AXIS)
    const ctxMain = document.getElementById("chart-main").getContext("2d");
    mainChart = new Chart(ctxMain, {
        type: "line",
        data: {
            labels: [],
            datasets: [
                {
                    label: "Tinggi S4 Pesisir (cm)",
                    data: [],
                    borderColor: "#0D6EFD", // Biru Solid
                    backgroundColor: "rgba(13, 110, 253, 0.05)",
                    borderWidth: 2.2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.2,
                    yAxisID: "y-height",
                },
                {
                    label: "Tinggi Global Maket (cm)",
                    data: [],
                    borderColor: "#6F42C1", // Ungu
                    backgroundColor: "transparent",
                    borderWidth: 1.8,
                    borderDash: [5, 4],
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.2,
                    yAxisID: "y-height",
                },
                {
                    label: "Debit Air (L/mnt)",
                    data: [],
                    borderColor: "#0DCAF0", // Cyan Putus-putus
                    backgroundColor: "transparent",
                    borderWidth: 1.8,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.2,
                    yAxisID: "y-flow",
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 8, font: { size: 11 } }
                },
                "y-height": {
                    type: "linear",
                    position: "left",
                    min: 0,
                    max: 40,
                    title: { display: true, text: "Ketinggian (cm)", font: { size: 12, weight: "bold" } },
                    grid: { color: "#F0F0F0" }
                },
                "y-flow": {
                    type: "linear",
                    position: "right",
                    min: 0,
                    max: 30,
                    title: { display: true, text: "Debit (L/mnt)", font: { size: 12, weight: "bold" } },
                    grid: { drawOnChartArea: false }
                }
            },
            plugins: {
                legend: { position: "top", labels: { boxWidth: 14, font: { size: 12 } } }
            }
        }
    });

    // 3. INISIALISASI GRAFIK SEKUNDER 1: SKOR RISIKO FUZZY (0–100)
    const ctxFuzzy = document.getElementById("chart-fuzzy").getContext("2d");
    fuzzyChart = new Chart(ctxFuzzy, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Skor Fuzzy",
                data: [],
                borderColor: "#EF6C00", // Oranye
                backgroundColor: "rgba(239, 108, 0, 0.08)",
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4,
                fill: true,
                tension: 0.2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 6, font: { size: 10 } }
                },
                y: {
                    min: 0,
                    max: 100,
                    ticks: { stepSize: 25 },
                    title: { display: true, text: "Skor (0-100)", font: { size: 11 } },
                    grid: { color: "#F5F5F5" }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });

    // 4. INISIALISASI GRAFIK SEKUNDER 2: TREN KECEPATAN GELOMBANG (cm/s)
    const ctxWave = document.getElementById("chart-wave").getContext("2d");
    waveChart = new Chart(ctxWave, {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Kecepatan (cm/s)",
                data: [],
                borderColor: "#198754", // Hijau Toska
                backgroundColor: "rgba(25, 135, 84, 0.15)",
                borderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: "#198754",
                showLine: true,
                tension: 0.1,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { maxTicksLimit: 6, font: { size: 10 } }
                },
                y: {
                    min: 0,
                    max: 200,
                    title: { display: true, text: "v (cm/s)", font: { size: 11 } },
                    grid: { color: "#F5F5F5" }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Kecepatan: ${context.parsed.y} cm/s`;
                        }
                    }
                }
            }
        }
    });

    // 5. FUNGSI PEMUATAN DATA AWAL (HISTORY GRAFIK UTAMA & FUZZY)
    async function loadHistory(limit = 120, minutes = null) {
        try {
            let url = `/api/history?limit=${limit}`;
            if (minutes) url += `&minutes=${minutes}`;

            const res = await fetch(url);
            if (!res.ok) throw new Error("Gagal mengambil data history");
            const data = await res.json();

            mainChart.data.labels = data.labels || [];
            mainChart.data.datasets[0].data = data.tinggi_s4 || [];
            mainChart.data.datasets[1].data = data.tinggi_global || [];
            mainChart.data.datasets[2].data = data.debit || [];
            mainChart.update();

            fuzzyChart.data.labels = data.labels || [];
            fuzzyChart.data.datasets[0].data = data.fuzzy || [];
            fuzzyChart.update();
        } catch (err) {
            console.warn("[Dashboard] Error memuat riwayat grafik:", err);
        }
    }

    // 6. FUNGSI PEMUATAN DATA AWAL GRAFIK TREN KECEPATAN GELOMBANG
    async function loadWaveHistory() {
        try {
            const res = await fetch("/api/gelombang?limit=30");
            if (!res.ok) return;
            const events = await res.json();

            const labels = [];
            const speeds = [];

            events.forEach(ev => {
                labels.push(ev.time_str || "");
                speeds.push(ev.kecepatan_cms || null);
            });

            waveChart.data.labels = labels;
            waveChart.data.datasets[0].data = speeds;
            waveChart.update();
        } catch (err) {
            console.warn("[Dashboard] Error memuat riwayat gelombang:", err);
        }
    }

    // 7. FUNGSI PEMUATAN RIWAYAT EVENT TRANSISI LEVEL
    async function loadEvents() {
        try {
            const res = await fetch("/api/events?limit=8");
            if (!res.ok) return;
            const events = await res.json();

            if (!events || events.length === 0) {
                eventsList.innerHTML = '<li class="list-group-item text-muted py-2 px-0">Belum ada riwayat transisi level.</li>';
                return;
            }

            eventsList.innerHTML = "";
            events.forEach(ev => {
                const li = document.createElement("li");
                li.className = "list-group-item d-flex justify-content-between align-items-center py-2 px-0";
                const fz = ev.nilai_fuzzy !== null ? `(${ev.nilai_fuzzy.toFixed(1)})` : "";
                li.innerHTML = `
                    <div>
                        <span class="fw-semibold">${ev.level_dari}</span> &rarr;
                        <span class="fw-bold">${ev.level_ke}</span>
                        <span class="text-muted small ms-1">${fz}</span>
                    </div>
                    <span class="text-secondary small font-monospace">${ev.time_str}</span>
                `;
                eventsList.appendChild(li);
            });
        } catch (err) {
            console.warn("[Dashboard] Error memuat event:", err);
        }
    }

    // 8. FUNGSI POLLING DATA TERKINI (/api/now)
    async function pollLatest() {
        try {
            const res = await fetch("/api/now");
            if (!res.ok) throw new Error("Gagal mengambil status terkini");
            const d = await res.json();

            // A. Update Status Koneksi & Jam
            if (d.online) {
                connBadge.textContent = "[ONLINE]";
                connBadge.className = "badge bg-success fs-6 px-3 py-2";
                dataAgeInfo.textContent = `Data terakhir: ${d.age_s} detik lalu`;
            } else {
                connBadge.textContent = "[TERPUTUS]";
                connBadge.className = "badge bg-secondary fs-6 px-3 py-2";
                dataAgeInfo.textContent = d.age_s ? `Data terlambat: ${d.age_s} detik lalu` : "Tidak ada sinyal telemetri";
            }

            if (d.time_str) {
                clockWib.textContent = d.time_str;
            }

            // B. Update Kartu Metrik 1: Tinggi S4 (Pesisir)
            valHeightS4.textContent = (d.online && d.tinggi_s4_cm !== null) ? d.tinggi_s4_cm.toFixed(1) : "--";
            sensorCountInfo.textContent = d.n_valid !== undefined ? `Sensor aktif: ${d.n_valid}/4` : "Sensor: --";

            // C. Update Kartu Metrik 2: Debit Air
            valFlow.textContent = (d.online && d.debit_lpm !== null) ? d.debit_lpm.toFixed(1) : "--";

            // D. Update Kartu Metrik 3: Skor Fuzzy
            valFuzzy.textContent = (d.online && d.nilai_fuzzy !== null) ? d.nilai_fuzzy.toFixed(1) : "--";

            // E. Update Kartu Metrik 4: Status Bahaya & Badge Arah (Surut / Luapan)
            statusCard.className = "metric-card p-3 rounded border h-100";
            if (!d.online) {
                statusCard.classList.add("status-offline");
                valStatus.textContent = "OFFLINE";
                valSource.textContent = "Sistem Offline";
                badgeArah.classList.add("d-none");
            } else {
                valStatus.textContent = d.level || "TIDAK_VALID";
                valSource.textContent = `Sumber: ${(d.sumber || "--").toUpperCase()} | Seq: ${d.seq || "--"}`;

                if (d.level === "AMAN") statusCard.classList.add("status-aman");
                else if (d.level === "WASPADA") statusCard.classList.add("status-waspada");
                else if (d.level === "SIAGA") statusCard.classList.add("status-siaga");
                else if (d.level === "BAHAYA") statusCard.classList.add("status-bahaya");
                else statusCard.classList.add("status-offline");

                // Badge arah anomali tsunami
                if (d.level === "BAHAYA" && d.arah_bahaya) {
                    badgeArah.textContent = d.arah_bahaya;
                    badgeArah.classList.remove("d-none");
                } else {
                    badgeArah.classList.add("d-none");
                }
            }

            // F. Update Kartu Metrik 5: Tinggi Global Maket & Badge Stabilitas
            valHeightGlobal.textContent = (d.online && d.tinggi_global_cm !== null) ? d.tinggi_global_cm.toFixed(1) : "--";
            if (d.online && d.stabilitas_global) {
                badgeStabilitas.textContent = d.stabilitas_global;
                if (d.stabilitas_global === "STABIL") {
                    badgeStabilitas.className = "badge badge-stabil fs-7 px-2 py-1";
                } else if (d.stabilitas_global === "TURUN") {
                    badgeStabilitas.className = "badge badge-turun fs-7 px-2 py-1";
                } else if (d.stabilitas_global === "NAIK") {
                    badgeStabilitas.className = "badge badge-naik fs-7 px-2 py-1";
                } else {
                    badgeStabilitas.className = "badge bg-secondary fs-7 px-2 py-1";
                }
            } else {
                badgeStabilitas.textContent = "OFFLINE";
                badgeStabilitas.className = "badge bg-secondary fs-7 px-2 py-1";
            }

            // G. Update Kartu Metrik 6: Kecepatan Gelombang Terakhir
            if (d.kecepatan_terakhir_cms !== null && d.kecepatan_terakhir_cms !== undefined) {
                valWaveSpeed.textContent = d.kecepatan_terakhir_cms.toFixed(1);
                const dtStr = d.kecepatan_terakhir_dt_ms ? `Δt: ${d.kecepatan_terakhir_dt_ms} ms` : "";
                const ageStr = d.kecepatan_terakhir_age_s ? `${d.kecepatan_terakhir_age_s}s lalu` : "";
                valWaveInfo.textContent = [dtStr, ageStr].filter(Boolean).join(" • ");

                // Jika ada gelombang baru, perbarui grafik tren gelombang
                if (d.kecepatan_terakhir_cms !== lastWaveTimestamp) {
                    lastWaveTimestamp = d.kecepatan_terakhir_cms;
                    loadWaveHistory();
                }
            } else {
                valWaveSpeed.textContent = "--";
                valWaveInfo.textContent = "Belum ada kejadian gelombang tercatat";
            }

            // H. Update Titik Baru ke Grafik Real-Time (Tanpa Reload)
            if (d.online && d.time_str) {
                const timeLabel = d.time_str.split(" ")[0]; // Ambil HH:MM:SS
                const labels = mainChart.data.labels;
                const lastLabel = labels.length > 0 ? labels[labels.length - 1] : "";

                if (timeLabel !== lastLabel) {
                    labels.push(timeLabel);
                    mainChart.data.datasets[0].data.push(d.tinggi_s4_cm);
                    mainChart.data.datasets[1].data.push(d.tinggi_global_cm);
                    mainChart.data.datasets[2].data.push(d.debit_lpm);

                    if (labels.length > activeLimit) {
                        labels.shift();
                        mainChart.data.datasets[0].data.shift();
                        mainChart.data.datasets[1].data.shift();
                        mainChart.data.datasets[2].data.shift();
                    }
                    mainChart.update();

                    fuzzyChart.data.labels.push(timeLabel);
                    fuzzyChart.data.datasets[0].data.push(d.nilai_fuzzy);
                    if (fuzzyChart.data.labels.length > activeLimit) {
                        fuzzyChart.data.labels.shift();
                        fuzzyChart.data.datasets[0].data.shift();
                    }
                    fuzzyChart.update();
                }
            }

            // I. Update Riwayat Event Jika Status Level Berubah
            if (d.level && d.level !== lastLevel) {
                lastLevel = d.level;
                loadEvents();
            }

        } catch (err) {
            // Fail-safe jika server web / jaringan terputus
            connBadge.textContent = "[TERPUTUS]";
            connBadge.className = "badge bg-danger fs-6 px-3 py-2";
            dataAgeInfo.textContent = "Koneksi ke backend Flask terputus";
            statusCard.className = "metric-card p-3 rounded border h-100 status-offline";
            valStatus.textContent = "OFFLINE";
            valSource.textContent = "Server Tidak Terjangkau";
            badgeArah.classList.add("d-none");
            badgeStabilitas.className = "badge bg-secondary fs-7 px-2 py-1";
            badgeStabilitas.textContent = "OFFLINE";
        }
    }

    // 9. EVENT LISTENER UNTUK TOMBOL PILIHAN RENTANG WAKTU
    rangeButtons.forEach(btn => {
        btn.addEventListener("click", function () {
            rangeButtons.forEach(b => b.classList.remove("active"));
            this.classList.add("active");

            activeLimit = parseInt(this.getAttribute("data-limit")) || 120;
            activeMinutes = parseInt(this.getAttribute("data-minutes")) || null;

            loadHistory(activeLimit, activeMinutes);
        });
    });

    // 10. EKSEKUSI AWAL
    loadHistory(activeLimit);
    loadWaveHistory();
    loadEvents();
    pollLatest();

    // Polling setiap 2 detik sesuai spesifikasi Bagian 6.2
    setInterval(pollLatest, 2000);
});
