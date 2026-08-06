/* =========================================================
   FaceAttendance - Unknown Faces Gallery & Conversion
   ========================================================= */

let activeRecordId = null;

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    
    // Set default date filter to today
    const dateInput = document.getElementById('dateFilter');
    if (dateInput) {
        dateInput.value = new Date().toISOString().split('T')[0];
        dateInput.addEventListener('change', loadUnknownFaces);
    }

    loadUnknownFaces();
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

async function loadUnknownFaces() {
    const gallery = document.getElementById('unknownGallery');
    const dateInput = document.getElementById('dateFilter');
    const dateVal = dateInput ? dateInput.value : '';

    try {
        const url = dateVal ? `/api/unknown/list?date=${encodeURIComponent(dateVal)}` : '/api/unknown/list';
        const res = await fetch(url);
        const records = await res.json();

        if (!records || records.length === 0) {
            gallery.innerHTML = `
                <div class="glass-card" style="grid-column: 1 / -1; padding: 40px 20px; text-align: center;">
                    <div style="width: 56px; height: 56px; border-radius: 50%; background: rgba(99, 102, 241, 0.1); color: var(--accent-primary); display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; font-size: 24px;">
                        <i class="bi bi-shield-check"></i>
                    </div>
                    <h3 style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px;">No Unknown Faces Recorded</h3>
                    <p style="font-size: 13px; color: var(--text-secondary);">All faces detected during this period were recognized or no visitors were seen.</p>
                </div>
            `;
            return;
        }

        gallery.innerHTML = records.map(r => {
            const isConverted = r.status && r.status.startsWith('converted_to_');
            const studentName = isConverted ? r.status.replace('converted_to_', '') : '';

            return `
                <div class="unknown-card">
                    <span class="unknown-badge">
                        <i class="bi bi-clock-history"></i> ${r.time}
                    </span>
                    <div class="unknown-img-box">
                        <img src="${r.relative_url}" alt="Unknown Capture" onerror="this.src='/static/img/avatar_placeholder.png'">
                    </div>
                    <div class="unknown-body">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Record: ${escapeHtml(r.id)}</div>
                        <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 12px;">
                            ${isConverted ? `<span style="color: var(--success);"><i class="bi bi-check-circle"></i> Enrolled as ${escapeHtml(studentName)}</span>` : `Unidentified Visitor`}
                        </div>
                        <div style="display: flex; gap: 8px;">
                            ${!isConverted ? `
                                <button class="btn btn-primary btn-sm" style="flex: 1; justify-content: center; font-size: 12px;" 
                                        onclick="openConvertModal('${escapeHtml(r.id)}', '${escapeHtml(r.relative_url)}')">
                                    <i class="bi bi-person-plus-fill"></i> Enroll
                                </button>
                            ` : ''}
                            <button class="btn btn-danger btn-sm" style="${isConverted ? 'width: 100%;' : ''} justify-content: center; font-size: 12px;" 
                                    onclick="deleteUnknownRecord('${escapeHtml(r.id)}')">
                                <i class="bi bi-trash3-fill"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

    } catch (e) {
        gallery.innerHTML = `
            <div class="glass-card" style="grid-column: 1 / -1; padding: 30px; text-align: center; color: var(--danger);">
                <i class="bi bi-exclamation-triangle-fill"></i> Failed to load unknown visitors log.
            </div>
        `;
    }
}

function openConvertModal(recordId, imgUrl) {
    activeRecordId = recordId;
    document.getElementById('convertPreviewImg').src = imgUrl;
    document.getElementById('convertRecordMeta').textContent = `ID: ${recordId}`;
    document.getElementById('newStudentName').value = '';
    document.getElementById('convertModal').style.display = 'flex';
    document.getElementById('newStudentName').focus();
}

function closeConvertModal() {
    document.getElementById('convertModal').style.display = 'none';
    activeRecordId = null;
}

async function confirmConversion() {
    const studentName = document.getElementById('newStudentName').value.trim();
    if (!studentName) {
        alert("Please enter a valid student name.");
        return;
    }

    const btn = document.getElementById('btnConfirmConvert');
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner" style="width: 14px; height: 14px; margin-right: 6px;"></span> Retraining AI...`;

    try {
        const res = await fetch('/api/unknown/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: activeRecordId,
                student_name: studentName
            })
        });
        const result = await res.json();

        if (result.success) {
            closeConvertModal();
            loadUnknownFaces();
        } else {
            alert(`Error: ${result.message}`);
        }
    } catch (e) {
        alert("Failed to convert unknown face.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-check2-circle"></i> Save & Retrain AI`;
    }
}

async function deleteUnknownRecord(recordId) {
    if (!confirm(`Are you sure you want to delete unknown record ${recordId}?`)) {
        return;
    }

    try {
        const res = await fetch('/api/unknown/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record_id: recordId })
        });
        const result = await res.json();

        if (result.success) {
            loadUnknownFaces();
        } else {
            alert(`Error: ${result.message}`);
        }
    } catch (e) {
        alert("Failed to delete record.");
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[m]));
}
