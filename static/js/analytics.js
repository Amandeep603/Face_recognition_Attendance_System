/* =========================================================
   FaceAttendance - Analytics & Chart.js Visualizer
   ========================================================= */

let trendChartInstance = null;
let defenseChartInstance = null;
let hourlyChartInstance = null;
let studentChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadAnalyticsSummary();
    loadTrendData(7);
    loadHourlyDistribution();
    loadStudentRankings();
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

async function loadAnalyticsSummary() {
    try {
        const res = await fetch('/api/analytics/summary');
        const data = await res.json();

        document.getElementById('kpiTotalStudents').textContent = data.total_students ?? 0;
        document.getElementById('kpiPresentToday').textContent = data.present_today ?? 0;
        document.getElementById('kpiAttendancePct').textContent = `${data.attendance_percentage ?? 0}%`;
        document.getElementById('kpiAbsentToday').textContent = data.absent_today ?? 0;
        document.getElementById('kpiMostPunctual').textContent = data.most_punctual || 'N/A';
        document.getElementById('kpiSpoofsBlocked').textContent = data.spoofs_blocked ?? 0;
        
        if (data.storage) {
            document.getElementById('kpiStorage').textContent = `${data.storage.total_mb} MB`;
        }

        renderDefenseChart(data.present_today, data.unknown_faces_today, data.spoofs_blocked);

    } catch (e) {
        console.error("Failed to load analytics summary:", e);
    }
}

async function loadTrendData(days = 7) {
    // Update button states
    const b7 = document.getElementById('btnTrend7');
    const b30 = document.getElementById('btnTrend30');
    if (b7 && b30) {
        b7.classList.toggle('active', days === 7);
        b30.classList.toggle('active', days === 30);
    }

    try {
        const res = await fetch(`/api/analytics/trends?days=${days}`);
        const data = await res.json();

        const ctx = document.getElementById('trendChart').getContext('2d');

        if (trendChartInstance) {
            trendChartInstance.destroy();
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

        trendChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Present Students',
                    data: data.counts,
                    borderColor: '#6366f1',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#ffffff',
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        padding: 10,
                        titleFont: { size: 12, weight: 'bold' },
                        bodyFont: { size: 12 }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { color: '#94a3b8', font: { size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { precision: 0, color: '#94a3b8', font: { size: 11 } }
                    }
                }
            }
        });

    } catch (e) {
        console.error("Failed to load trend data:", e);
    }
}

function renderDefenseChart(liveCount = 0, unknownCount = 0, spoofCount = 0) {
    const ctx = document.getElementById('defenseChart').getContext('2d');

    if (defenseChartInstance) {
        defenseChartInstance.destroy();
    }

    const safeLive = Math.max(liveCount, 0);
    const safeUnk = Math.max(unknownCount, 0);
    const safeSpoof = Math.max(spoofCount, 0);

    defenseChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Live Verified', 'Unknown Visitors', 'Spoofs Blocked'],
            datasets: [{
                data: [safeLive || 1, safeUnk, safeSpoof],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 0,
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { size: 11 }, padding: 14 }
                }
            },
            cutout: '70%'
        }
    });
}

async function loadHourlyDistribution() {
    try {
        const res = await fetch('/api/analytics/hourly');
        const data = await res.json();

        const ctx = document.getElementById('hourlyChart').getContext('2d');

        if (hourlyChartInstance) {
            hourlyChartInstance.destroy();
        }

        hourlyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Check-ins',
                    data: data.counts,
                    backgroundColor: 'rgba(245, 158, 11, 0.75)',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { precision: 0, color: '#94a3b8' }
                    }
                }
            }
        });

    } catch (e) {
        console.error("Failed to load hourly check-in distribution:", e);
    }
}

async function loadStudentRankings() {
    try {
        const res = await fetch('/api/analytics/rankings');
        const data = await res.json();

        // 1. Render Student Attendance Breakdown Horizontal Bar
        const summaries = data.student_summaries || [];
        const top10 = summaries.slice(0, 10);

        const ctx = document.getElementById('studentBarChart').getContext('2d');

        if (studentChartInstance) {
            studentChartInstance.destroy();
        }

        studentChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: top10.map(s => s.name),
                datasets: [{
                    label: 'Attendance %',
                    data: top10.map(s => s.attendance_percentage),
                    backgroundColor: top10.map(s => s.attendance_percentage >= 75 ? 'rgba(16, 185, 129, 0.8)' : 'rgba(239, 68, 68, 0.8)'),
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(255, 255, 255, 0.06)' },
                        ticks: { color: '#94a3b8', callback: v => v + '%' }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#e2e8f0', font: { size: 11, weight: '500' } }
                    }
                }
            }
        });

        // 2. Populate Chronic Absentees Table
        const tbody = document.getElementById('chronicAbsenteesBody');
        const absentees = data.chronic_absentees || [];

        if (absentees.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--success); padding: 18px;"><i class="bi bi-check-circle-fill"></i> Excellent! All enrolled students maintain &gt;= 75% attendance.</td></tr>`;
            return;
        }

        tbody.innerHTML = absentees.map(s => `
            <tr>
                <td style="font-weight: 600; color: var(--text-primary);">${escapeHtml(s.name)}</td>
                <td>${s.days_present} Days</td>
                <td>${s.total_days} Days</td>
                <td>
                    <span style="color: var(--danger); font-weight: 700;">${s.attendance_pct}%</span>
                </td>
                <td>
                    <a href="/reports?student=${encodeURIComponent(s.name)}" class="btn btn-secondary btn-sm" style="padding: 4px 10px; font-size: 11px;">
                        <i class="bi bi-file-earmark-text"></i> View History
                    </a>
                </td>
            </tr>
        `).join('');

    } catch (e) {
        console.error("Failed to load student rankings:", e);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}
