/* =========================================================
   FaceAttendance - Main Dashboard Frontend Controller
   ========================================================= */

// Global State
let currentStats = {};
let previousAttendanceCount = -1;
let sseEventSource = null;
let selectedFilterDate = "";

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initClock();
    initDatePicker();
    initStatsPolling();
    initSSE();
    initSearchFilter();
    initCameraControls();
});

/* ----------------- Theme Manager ----------------- */
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeButtonIcon(savedTheme);

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'dark';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            updateThemeButtonIcon(next);
        });
    }
}

function updateThemeButtonIcon(theme) {
    const icon = document.querySelector('#themeToggleBtn i');
    const text = document.querySelector('#themeToggleBtn span');
    if (icon) {
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
    if (text) {
        text.textContent = theme === 'dark' ? 'Light Theme' : 'Dark Theme';
    }
}

/* ----------------- Live Digital Clock ----------------- */
function initClock() {
    const timeEl = document.getElementById('liveClockTime');
    const dateEl = document.getElementById('liveClockDate');

    function update() {
        const now = new Date();
        if (timeEl) {
            timeEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
        }
        if (dateEl) {
            dateEl.textContent = now.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric'
            });
        }
    }
    update();
    setInterval(update, 1000);
}

/* ----------------- Date Filter Picker ----------------- */
function initDatePicker() {
    const dateInput = document.getElementById('attendanceDateFilter');
    if (!dateInput) return;

    // Default to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;
    selectedFilterDate = today;

    dateInput.addEventListener('change', async (e) => {
        const pickedDate = e.target.value;
        selectedFilterDate = pickedDate;
        
        // Update Export Buttons
        updateExportLinks(pickedDate);

        // Update Panel Title
        const titleEl = document.getElementById('panelTitle');
        if (titleEl) {
            titleEl.textContent = (pickedDate === today) ? "Today's Attendance" : `Attendance (${pickedDate})`;
        }

        // Fetch records for selected date
        try {
            const res = await fetch(`/api/attendance/date/${pickedDate}`);
            const data = await res.json();
            if (data.success) {
                renderAttendanceTable(data.records);
            }
        } catch (err) {
            console.error("Error loading date attendance:", err);
        }
    });
}

function updateExportLinks(dateStr) {
    const csvBtn = document.getElementById('btnExportCsv');
    const excelBtn = document.getElementById('btnExportExcel');
    if (csvBtn) csvBtn.href = `/api/attendance/export/csv?date=${dateStr}`;
    if (excelBtn) excelBtn.href = `/api/attendance/export/excel?date=${dateStr}`;
}

/* ----------------- Real-time Polling & SSE ----------------- */
function initStatsPolling() {
    fetchStats();
    setInterval(fetchStats, 2500);
}

function initSSE() {
    if (typeof EventSource !== "undefined") {
        try {
            sseEventSource = new EventSource('/api/stream/events');
            sseEventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'attendance_marked') {
                    // Visual green glow animation on camera
                    triggerCameraPulse();
                    const confText = data.record.confidence ? ` (${data.record.confidence}%)` : '';
                    showToast('Attendance Marked!', `${data.record.name}${confText} recorded as Present.`, 'success');
                    fetchStats();
                } else if (data.type === 'unknown_face') {
                    showToast('Unknown Face', 'Unregistered person detected in view.', 'warning');
                } else if (data.type === 'heartbeat') {
                    updateDashboard(data.stats);
                }
            };
            sseEventSource.onerror = () => {
                console.warn("[SSE] EventSource failed, relying on background polling.");
            };
        } catch (e) {
            console.warn("[SSE] SSE error: ", e);
        }
    }
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        updateDashboard(data);
    } catch (e) {
        console.error("Error fetching stats:", e);
    }
}

function triggerCameraPulse() {
    const cam = document.getElementById('cameraContainer');
    if (cam) {
        cam.classList.remove('pulse-success');
        void cam.offsetWidth; // Trigger reflow
        cam.classList.add('pulse-success');
        setTimeout(() => cam.classList.remove('pulse-success'), 1200);
    }
}

function updateDashboard(data) {
    currentStats = data;

    // Update KPI counters
    animateValue('statRegistered', data.total_registered || 0);
    animateValue('statPresent', data.present_today || 0);
    animateValue('statAbsent', data.absent_today || 0);
    animateValue('statUnknown', data.unknown_detections || 0);

    // Update Camera HUD
    if (data.camera) {
        const cam = data.camera;
        const dot = document.getElementById('cameraStatusDot');
        const text = document.getElementById('cameraStatusText');
        const fps = document.getElementById('cameraFps');
        const latency = document.getElementById('cameraLatency');
        const lastRec = document.getElementById('lastRecTime');

        if (dot && text) {
            dot.className = `status-dot ${cam.status}`;
            text.textContent = cam.status.toUpperCase();
        }
        if (fps) {
            fps.textContent = `${cam.fps.toFixed(1)} FPS`;
        }
        if (latency) {
            latency.textContent = `${cam.latency_ms} ms`;
        }
        if (lastRec && data.last_recognition_time) {
            lastRec.textContent = data.last_recognition_time;
        }
    }

    // Only update table if looking at Today's date
    const today = new Date().toISOString().split('T')[0];
    if (selectedFilterDate === "" || selectedFilterDate === today) {
        if (data.recent_records && data.recent_records.length !== previousAttendanceCount) {
            renderAttendanceTable(data.recent_records);
            previousAttendanceCount = data.recent_records.length;
        }
    }
}

function animateValue(id, targetVal) {
    const el = document.getElementById(id);
    if (!el) return;
    const current = parseInt(el.textContent) || 0;
    if (current === targetVal) return;

    const diff = targetVal - current;
    const step = diff > 0 ? 1 : -1;
    let val = current;

    const timer = setInterval(() => {
        val += step;
        el.textContent = val;
        if (val === targetVal) clearInterval(timer);
    }, 25);
}

/* ----------------- Table Rendering ----------------- */
function renderAttendanceTable(records) {
    const tbody = document.getElementById('attendanceTableBody');
    const emptyState = document.getElementById('tableEmptyState');
    if (!tbody) return;

    if (!records || records.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';

    tbody.innerHTML = records.map(r => `
        <tr>
            <td>
                <div class="student-thumb-cell">
                    <img src="${r.thumbnail}" alt="${r.name}" class="student-avatar" 
                         onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(r.name)}&background=6366f1&color=fff'">
                    <div class="student-meta-sub">
                        <span class="student-name-text">${escapeHtml(r.name)}</span>
                        ${r.confidence ? `<span class="chip-confidence">${r.confidence}% Match</span>` : ''}
                    </div>
                </div>
            </td>
            <td>
                <span class="time-badge"><i class="bi bi-clock"></i> ${escapeHtml(r.time)}</span>
            </td>
            <td>
                <span class="status-chip chip-present"><i class="bi bi-check-circle-fill"></i> ${escapeHtml(r.status)}</span>
            </td>
        </tr>
    `).join('');
}

/* ----------------- Search Filter ----------------- */
function initSearchFilter() {
    const input = document.getElementById('attendanceSearch');
    if (!input) return;

    input.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const rows = document.querySelectorAll('#attendanceTableBody tr');
        let visibleCount = 0;

        rows.forEach(row => {
            const name = row.querySelector('.student-name-text')?.textContent.toLowerCase() || '';
            if (name.includes(query)) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        const emptyState = document.getElementById('tableEmptyState');
        if (emptyState) {
            emptyState.style.display = (visibleCount === 0 && rows.length > 0) ? 'block' : 'none';
        }
    });
}

/* ----------------- Camera Controls & Fullscreen ----------------- */
function initCameraControls() {
    const fsBtn = document.getElementById('fullscreenBtn');
    const camCard = document.getElementById('cameraContainer');

    if (fsBtn && camCard) {
        fsBtn.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                camCard.requestFullscreen().catch(err => {
                    alert(`Error attempting fullscreen: ${err.message}`);
                });
            } else {
                document.exitFullscreen();
            }
        });
    }
}

/* ----------------- Actions: Reset Attendance & Camera Source ----------------- */
function confirmResetAttendance() {
    openModal(
        "Reset Today's Attendance?",
        "This will clear all attendance records and saved face thumbnails for today. This action cannot be undone.",
        async () => {
            try {
                const res = await fetch('/api/attendance/reset', { method: 'POST' });
                const data = await res.json();
                showToast('Success', data.message, 'success');
                previousAttendanceCount = -1;
                fetchStats();
            } catch (e) {
                showToast('Error', 'Failed to reset attendance.', 'error');
            }
        }
    );
}

function promptChangeSource() {
    const currentSrc = currentStats.camera?.source || "http://192.168.18.142/capture";
    const newSrc = prompt("Enter ESP32-CAM stream URL or '0' for local webcam:", currentSrc);
    if (newSrc && newSrc.trim() !== "") {
        fetch('/api/camera/source', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source: newSrc.trim() })
        })
        .then(res => res.json())
        .then(data => {
            showToast('Camera Source', data.message, data.success ? 'success' : 'error');
            fetchStats();
        })
        .catch(err => showToast('Error', 'Failed to update camera source', 'error'));
    }
}

/* ----------------- Modal Utility ----------------- */
let modalConfirmCallback = null;

function openModal(title, message, onConfirm) {
    const overlay = document.getElementById('customModal');
    const titleEl = document.getElementById('modalTitle');
    const msgEl = document.getElementById('modalMessage');

    if (overlay && titleEl && msgEl) {
        titleEl.textContent = title;
        msgEl.textContent = message;
        modalConfirmCallback = onConfirm;
        overlay.classList.add('active');
    }
}

function closeModal() {
    const overlay = document.getElementById('customModal');
    if (overlay) overlay.classList.remove('active');
    modalConfirmCallback = null;
}

document.addEventListener('click', (e) => {
    if (e.target.id === 'modalConfirmBtn' && modalConfirmCallback) {
        modalConfirmCallback();
        closeModal();
    } else if (e.target.id === 'modalCancelBtn' || e.target.classList.contains('modal-overlay')) {
        closeModal();
    }
});

/* ----------------- Toast Utility ----------------- */
function showToast(title, message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    let iconClass = 'bi-info-circle-fill';
    if (type === 'success') iconClass = 'bi-check-circle-fill';
    if (type === 'error') iconClass = 'bi-exclamation-triangle-fill';
    if (type === 'warning') iconClass = 'bi-shield-exclamation';

    toast.innerHTML = `
        <i class="bi ${iconClass} toast-icon"></i>
        <div class="toast-content">
            <h4>${escapeHtml(title)}</h4>
            <p>${escapeHtml(message)}</p>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}
