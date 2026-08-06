/* =========================================================
   FaceAttendance - Student Directory Management Controller
   ========================================================= */

let allStudents = [];

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadStudentsList();
    initStudentSearch();
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

async function loadStudentsList() {
    const grid = document.getElementById('studentsGrid');
    const empty = document.getElementById('studentsEmptyState');
    const countEl = document.getElementById('studentTotalCount');

    try {
        const res = await fetch('/api/students/list');
        const data = await res.json();
        allStudents = data.students || [];

        if (countEl) countEl.textContent = `${allStudents.length} Enrolled Student${allStudents.length === 1 ? '' : 's'}`;

        if (allStudents.length === 0) {
            grid.innerHTML = '';
            if (empty) empty.style.display = 'block';
            return;
        }

        if (empty) empty.style.display = 'none';
        renderStudentsGrid(allStudents);

    } catch (e) {
        console.error("Failed to load students directory:", e);
        showToast("Error", "Failed to load student directory.", "error");
    }
}

function renderStudentsGrid(students) {
    const grid = document.getElementById('studentsGrid');
    if (!grid) return;

    grid.innerHTML = students.map(s => `
        <div class="student-card" id="studentCard-${escapeAttr(s.name)}">
            <img src="${s.sample_image || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(s.name) + '&background=6366f1&color=fff'}" 
                 alt="${escapeAttr(s.name)}" 
                 class="student-card-avatar"
                 onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(s.name)}&background=6366f1&color=fff'">
            <h3 class="student-card-name">${escapeHtml(s.name)}</h3>
            <p class="student-card-meta">
                <i class="bi bi-images" style="color: var(--accent-primary);"></i> ${s.image_count} Stored Photos &bull; <i class="bi bi-calendar3"></i> ${escapeHtml(s.registered_on)}
            </p>
            <div class="student-card-actions">
                <a href="/register?re_register=${encodeURIComponent(s.name)}" class="btn btn-secondary btn-sm" title="Re-take 20 face samples">
                    <i class="bi bi-arrow-repeat"></i> Re-Train
                </a>
                <button onclick="confirmDeleteStudent('${escapeAttr(s.name)}')" class="btn btn-danger-outline btn-sm" title="Delete student from database">
                    <i class="bi bi-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');
}

function initStudentSearch() {
    const input = document.getElementById('studentSearchInput');
    if (!input) return;

    input.addEventListener('input', (e) => {
        const q = e.target.value.toLowerCase().trim();
        const filtered = allStudents.filter(s => s.name.toLowerCase().includes(q));
        renderStudentsGrid(filtered);

        const empty = document.getElementById('studentsEmptyState');
        if (empty) {
            empty.style.display = (filtered.length === 0) ? 'block' : 'none';
        }
    });
}

function confirmDeleteStudent(name) {
    openModal(
        "Delete Student Record?",
        `Are you sure you want to delete '${name}'? This will permanently delete all stored face samples and clear the student's encodings from memory.`,
        () => {
            deleteStudent(name);
        }
    );
}

async function deleteStudent(name) {
    try {
        const res = await fetch('/api/students/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Student Deleted", data.message, "success");
            loadStudentsList();
        } else {
            showToast("Delete Error", data.message || "Failed to delete student.", "error");
        }
    } catch (e) {
        showToast("Error", "Server connection error deleting student.", "error");
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

function escapeAttr(str) {
    if (!str) return '';
    return String(str).replace(/"/g, '&quot;');
}
