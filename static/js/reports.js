/* =========================================================
   FaceAttendance - Reports Configurator & Multi-Format Exporter
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    setupInitialDates();
    loadStudentOptions();
    
    // Check if student query param exists in URL
    const urlParams = new URLSearchParams(window.location.search);
    const studentParam = urlParams.get('student');
    if (studentParam) {
        document.getElementById('reportType').value = 'student';
        onReportTypeChange();
        setTimeout(() => {
            document.getElementById('studentSelect').value = studentParam;
            loadReportPreview();
        }, 300);
    } else {
        loadReportPreview();
    }
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

function setupInitialDates() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('startDate').value = today;
    document.getElementById('endDate').value = today;
}

async function loadStudentOptions() {
    try {
        const res = await fetch('/api/students/list');
        const data = await res.json();
        const select = document.getElementById('studentSelect');
        
        if (data.students) {
            data.students.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.name;
                opt.textContent = s.name;
                select.appendChild(opt);
            });
        }
    } catch (e) {
        console.error("Failed to load students for dropdown:", e);
    }
}

function onReportTypeChange() {
    const type = document.getElementById('reportType').value;
    const startGroup = document.getElementById('startDateGroup');
    const endGroup = document.getElementById('endDateGroup');
    const studentGroup = document.getElementById('studentSelectGroup');
    const startLabel = document.getElementById('startDateLabel');

    if (type === 'daily') {
        startGroup.style.display = 'block';
        startLabel.textContent = 'Date';
        endGroup.style.display = 'none';
        studentGroup.style.display = 'none';
    } else if (type === 'weekly' || type === 'monthly') {
        startGroup.style.display = 'none';
        endGroup.style.display = 'block';
        studentGroup.style.display = 'none';
    } else if (type === 'custom') {
        startGroup.style.display = 'block';
        startLabel.textContent = 'Start Date';
        endGroup.style.display = 'block';
        studentGroup.style.display = 'none';
    } else if (type === 'student') {
        startGroup.style.display = 'block';
        startLabel.textContent = 'Start Date';
        endGroup.style.display = 'block';
        studentGroup.style.display = 'block';
    }
}

async function loadReportPreview() {
    const type = document.getElementById('reportType').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const student = document.getElementById('studentSelect').value;

    const tbody = document.getElementById('reportPreviewBody');
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);"><span class="spinner" style="width: 16px; height: 16px; margin-right: 8px;"></span> Loading preview...</td></tr>`;

    try {
        const params = new URLSearchParams({
            report_type: type,
            start_date: startDate,
            end_date: endDate,
            student_name: student
        });

        const res = await fetch(`/api/reports/preview?${params.toString()}`);
        const data = await res.json();

        // Update KPIs
        const sum = data.summary || {};
        document.getElementById('sumTotalEnrolled').textContent = sum.total_registered_students ?? '--';
        document.getElementById('sumUniquePresent').textContent = sum.unique_present_students ?? '--';
        document.getElementById('sumTotalEntries').textContent = sum.total_entries ?? '--';
        document.getElementById('sumAttendanceRate').textContent = sum.attendance_rate ?? '--%';
        document.getElementById('previewMeta').textContent = `Showing ${sum.total_entries || 0} entries for ${sum.date_range || ''}`;

        const records = data.records || [];
        if (records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 30px;">No attendance records found for this criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = records.map((r, idx) => `
            <tr>
                <td style="color: var(--text-muted);">${idx + 1}</td>
                <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(r.Name)}</td>
                <td>${r.Date}</td>
                <td style="font-family: var(--font-mono); font-size: 13px;">${r.Time}</td>
                <td>
                    <span style="color: var(--success); font-weight: 700;">
                        <i class="bi bi-check-circle-fill"></i> ${r.Status}
                    </span>
                </td>
                <td>
                    <span style="color: var(--accent-primary); font-size: 12px; font-weight: 500;">
                        <i class="bi bi-shield-check"></i> ${r.Verification}
                    </span>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--danger);">Failed to fetch report preview.</td></tr>`;
    }
}

function exportReport(format = 'csv') {
    const type = document.getElementById('reportType').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const student = document.getElementById('studentSelect').value;

    const params = new URLSearchParams({
        report_type: type,
        start_date: startDate,
        end_date: endDate,
        student_name: student,
        format: format
    });

    // Trigger file download in browser
    window.location.href = `/api/reports/download?${params.toString()}`;
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}
