// ==============================================================================
//  AI Face Recognition Attendance System - System Diagnostics Test Runner
// ==============================================================================

let lastDiagnosticReport = null;

const initialTestDefinitions = [
    { id: 1, name: "Dependencies & Runtime Environment", desc: "Verifies Python 3.11, OpenCV, face_recognition, dlib, numpy, pandas, reportlab, psutil" },
    { id: 2, name: "Directory Structure & Write Permissions", desc: "Validates known_faces, attendance, unknown_faces, reports, and logs folders" },
    { id: 3, name: "Camera Stream Connectivity & FPS", desc: "Pings ESP32-CAM stream URL, checks buffer latency, and verifies video frame read" },
    { id: 4, name: "Face Engine & Encodings Cache", desc: "Validates encodings.pkl cache integrity, recognition tolerances, and model initialization" },
    { id: 5, name: "Attendance Engine & CSV Storage", desc: "Tests CSV record appending, schema integrity, and duplicate attendance debouncing" },
    { id: 6, name: "Registration Capture & Blur Pipeline", desc: "Validates Laplacian blur estimation, burst frame sampling, and multi-angle scoring" },
    { id: 7, name: "Anti-Spoofing & Liveness Verification", desc: "Tests Eye Aspect Ratio (EAR) blink detection, spectral texture, and multi-frame fusion" },
    { id: 8, name: "Unknown Face Registry & Conversion", desc: "Tests visitor auto-capturing, JSON metadata tracking, and student conversion" },
    { id: 9, name: "Multi-Format Exporters (CSV / XLSX / PDF)", desc: "Generates test daily/weekly CSV, styled Excel (.xlsx), and institutional PDF reports" },
    { id: 10, name: "Analytics Engine Aggregation", desc: "Validates KPI summaries, 7-day attendance trends, and peak arrival distribution" }
];

document.addEventListener("DOMContentLoaded", () => {
    renderInitialTestCards();
});

function renderInitialTestCards() {
    const container = document.getElementById("testItemsContainer");
    if (!container) return;

    container.innerHTML = initialTestDefinitions.map(t => `
        <div class="test-card" id="test-card-${t.id}">
            <div class="test-info">
                <div class="test-num">${String(t.id).padStart(2, '0')}</div>
                <div>
                    <div class="test-title">${t.name}</div>
                    <div class="test-desc" id="test-desc-${t.id}">${t.desc}</div>
                </div>
            </div>
            <div id="test-badge-${t.id}" class="test-badge badge-pending">
                <i class="fa-solid fa-clock"></i> PENDING
            </div>
        </div>
    `).join('');
}

async function runDiagnostics() {
    const runBtn = document.getElementById("runDiagBtn");
    const exportBtn = document.getElementById("exportDiagBtn");
    const statusBadge = document.getElementById("overallStatusBadge");
    const summaryText = document.getElementById("diagSummaryText");
    const lastRunTime = document.getElementById("lastRunTime");
    const consoleEl = document.getElementById("logConsole");

    if (runBtn) {
        runBtn.disabled = true;
        runBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Diagnostics...';
    }
    if (exportBtn) exportBtn.disabled = true;

    // Reset badges to running
    for (let i = 1; i <= 10; i++) {
        const badge = document.getElementById(`test-badge-${i}`);
        if (badge) {
            badge.className = "test-badge badge-running";
            badge.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> TESTING';
        }
    }

    if (statusBadge) {
        statusBadge.style.background = "rgba(99,102,241,0.2)";
        statusBadge.style.color = "#818cf8";
        statusBadge.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> TESTING IN PROGRESS';
    }
    if (summaryText) summaryText.textContent = "Executing 10-Point System Diagnostics...";
    if (consoleEl) consoleEl.textContent = `[${new Date().toLocaleTimeString()}] Initiating full automated diagnostic test suite...\n`;

    try {
        const res = await fetch("/api/diagnostics/run");
        const data = await res.json();
        lastDiagnosticReport = data;

        if (data.status === "success" && data.report) {
            const report = data.report;
            
            // Update hero stats
            document.getElementById("pillPassed").textContent = report.passed;
            document.getElementById("pillFailed").textContent = report.failed;
            document.getElementById("pillDuration").textContent = `${report.total_duration_sec}s`;
            
            if (lastRunTime) lastRunTime.textContent = `Last run at ${report.timestamp} (Duration: ${report.total_duration_sec}s)`;

            let consoleOutput = `[${report.timestamp}] Full diagnostics completed in ${report.total_duration_sec}s\n`;
            consoleOutput += `Summary: ${report.passed}/${report.total_tests} Tests Passed\n`;
            consoleOutput += `------------------------------------------------------------\n`;

            // Update individual test cards
            report.tests.forEach(t => {
                const badge = document.getElementById(`test-badge-${t.id}`);
                const desc = document.getElementById(`test-desc-${t.id}`);
                
                if (badge) {
                    if (t.status === "PASS") {
                        badge.className = "test-badge badge-pass";
                        badge.innerHTML = `<i class="fa-solid fa-check"></i> PASS (${t.duration_ms}ms)`;
                    } else {
                        badge.className = "test-badge badge-fail";
                        badge.innerHTML = `<i class="fa-solid fa-xmark"></i> FAIL (${t.duration_ms}ms)`;
                    }
                }
                if (desc && t.details) {
                    desc.innerHTML = `<span style="color: ${t.status === 'PASS' ? '#a7f3d0' : '#fca5a5'}; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem;">${t.details}</span>`;
                }

                consoleOutput += `[${String(t.id).padStart(2, '0')}] ${t.name.padEnd(42)} [${t.status}] (${t.duration_ms}ms)\n       -> ${t.details}\n`;
            });

            if (consoleEl) consoleEl.textContent = consoleOutput;

            // Overall badge
            if (statusBadge) {
                if (report.failed === 0) {
                    statusBadge.style.background = "rgba(16,185,129,0.2)";
                    statusBadge.style.color = "#10b981";
                    statusBadge.style.borderColor = "rgba(16,185,129,0.4)";
                    statusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> 100% PASS - SYSTEM OPERATIONAL';
                    if (summaryText) summaryText.textContent = "All 10 Verification Checks Passed Successfully";
                } else {
                    statusBadge.style.background = "rgba(239,68,68,0.2)";
                    statusBadge.style.color = "#ef4444";
                    statusBadge.style.borderColor = "rgba(239,68,68,0.4)";
                    statusBadge.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${report.failed} TESTS FAILED`;
                    if (summaryText) summaryText.textContent = `Diagnostics Detected ${report.failed} Issue(s)`;
                }
            }

            if (exportBtn) exportBtn.disabled = false;
        } else {
            alert("Diagnostics execution failed: " + (data.message || "Unknown error"));
        }
    } catch (err) {
        alert("Failed to connect to diagnostics API: " + err.message);
    } finally {
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = '<i class="fa-solid fa-play"></i> Run Full System Test';
        }
    }
}

function exportDiagnosticReport() {
    if (!lastDiagnosticReport) return;
    const blob = new Blob([JSON.stringify(lastDiagnosticReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Diagnostic_Report_${new Date().toISOString().slice(0,10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
