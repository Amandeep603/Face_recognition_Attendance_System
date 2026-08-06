/* =========================================================
   FaceAttendance - Biometric Student Registration Controller
   ========================================================= */

let currentStudentName = "";
let isCapturing = false;
let captureInterval = null;
let capturedThumbnails = [];

const POSE_INSTRUCTIONS = [
    { max: 4, title: "Look Straight (Center)", hint: "Center your face in the oval guide" },
    { max: 8, title: "Turn Slightly Left", hint: "Turn head 15° to your left side" },
    { max: 12, title: "Turn Slightly Right", hint: "Turn head 15° to your right side" },
    { max: 16, title: "Tilt Chin Slightly Up", hint: "Tilt head upwards slightly" },
    { max: 20, title: "Tilt Chin Slightly Down", hint: "Tilt head downwards slightly" }
];

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initRegistrationForm();
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

function initRegistrationForm() {
    const form = document.getElementById('studentStartForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const nameInput = document.getElementById('studentNameInput');
            const name = nameInput.value.trim();

            if (!name) {
                showToast("Error", "Please enter a valid student name.", "error");
                return;
            }

            currentStudentName = name;
            startRegistrationSession(name, false);
        });
    }
}

async function startRegistrationSession(name, overwrite = false) {
    const btn = document.getElementById('startCaptureBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Checking Database...';
    }

    try {
        const res = await fetch('/api/register/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, overwrite: overwrite })
        });

        const data = await res.json();

        if (data.already_exists && !overwrite) {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-camera-fill"></i> Start Registration';
            }
            openModal(
                "Student Already Registered",
                data.message || `Student '${name}' already exists. Overwrite with 20 new photos?`,
                () => {
                    startRegistrationSession(name, true);
                }
            );
            return;
        }

        if (!data.success) {
            showToast("Registration Error", data.message || "Failed to start registration.", "error");
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-camera-fill"></i> Start Registration';
            }
            return;
        }

        // Switch to Step 2 UI
        document.getElementById('step1Container').style.display = 'none';
        document.getElementById('step2Container').style.display = 'block';
        document.getElementById('stepItem1').className = 'step-item completed';
        document.getElementById('stepItem2').className = 'step-item active';

        document.getElementById('displayStudentName').textContent = name;
        capturedThumbnails = [];
        document.getElementById('thumbnailStrip').innerHTML = '';
        updateProgress(0, data.target_count || 20);

        showToast("Capture Started", `Align your face in the guide for ${name}.`, "info");

        // Begin automated capture loop
        startAutoCapture();

    } catch (e) {
        showToast("Connection Error", "Failed to communicate with the server.", "error");
        console.error(e);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-camera-fill"></i> Start Registration';
        }
    }
}

function startAutoCapture() {
    isCapturing = true;
    updatePoseGuidance(1);

    captureInterval = setInterval(async () => {
        if (!isCapturing) return;

        try {
            const res = await fetch('/api/register/capture_sample', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: currentStudentName })
            });

            const data = await res.json();

            if (data.success) {
                const count = data.current_count;
                const total = data.target_count;

                // Trigger shutter flash animation
                triggerShutterFlash();

                // Update Progress UI (Circular & Linear)
                updateProgress(count, total);

                // Update Quality Badge
                const qualityText = document.getElementById('qualityStatusText');
                if (qualityText) {
                    qualityText.textContent = `Sharpness: ${data.blur_score} (Valid)`;
                    qualityText.parentElement.style.borderColor = 'var(--success)';
                }

                // Add to thumbnail preview strip
                if (data.thumbnail) {
                    const strip = document.getElementById('thumbnailStrip');
                    const img = document.createElement('img');
                    img.src = data.thumbnail;
                    img.className = 'sample-thumb-item';
                    img.alt = `Sample ${count}`;
                    strip.appendChild(img);
                    strip.scrollLeft = strip.scrollWidth;

                    const countText = document.getElementById('stripCountText');
                    if (countText) countText.textContent = `${count} / ${total} images`;
                }

                // Update Pose Prompt for next sample
                updatePoseGuidance(count + 1);

                if (data.is_complete || count >= total) {
                    stopAutoCapture();
                    finalizeRegistration();
                }
            } else {
                // Display reason (e.g. blurry, no face, multiple faces, too similar)
                const qualityText = document.getElementById('qualityStatusText');
                if (qualityText) {
                    qualityText.textContent = data.message;
                    qualityText.parentElement.style.borderColor = 'var(--warning)';
                }
            }

        } catch (err) {
            console.warn("Capture sample request error:", err);
        }
    }, 420); // Capture sample every 420ms
}

function triggerShutterFlash() {
    const flash = document.getElementById('cameraFlashOverlay');
    if (flash) {
        flash.classList.add('flashing');
        setTimeout(() => flash.classList.remove('flashing'), 100);
    }
}

function updateProgress(count, total) {
    const percent = Math.round((count / total) * 100);

    // Linear bar
    const bar = document.getElementById('progressBarFill');
    if (bar) bar.style.width = `${percent}%`;

    // Circular ring (perimeter = 2 * PI * 45 ≈ 283)
    const circle = document.getElementById('circleProgressVal');
    if (circle) {
        const offset = 283 - (283 * (percent / 100));
        circle.style.strokeDashoffset = offset;
    }

    // Counters
    const countText = document.getElementById('progressCountText');
    const percentText = document.getElementById('progressPercentageText');
    if (countText) countText.textContent = `${count} / ${total}`;
    if (percentText) percentText.textContent = `${percent}% Complete`;
}

function updatePoseGuidance(sampleNumber) {
    let guide = POSE_INSTRUCTIONS[0];
    for (const p of POSE_INSTRUCTIONS) {
        if (sampleNumber <= p.max) {
            guide = p;
            break;
        }
    }

    const titleEl = document.getElementById('poseTitle');
    const hintEl = document.getElementById('poseHint');
    if (titleEl) titleEl.textContent = guide.title;
    if (hintEl) hintEl.textContent = guide.hint;
}

function stopAutoCapture() {
    isCapturing = false;
    if (captureInterval) clearInterval(captureInterval);
}

async function cancelRegistrationSession() {
    stopAutoCapture();
    try {
        await fetch('/api/register/cancel', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: currentStudentName })
        });
    } catch (e) {}

    showToast("Registration Cancelled", "Face enrollment was cancelled.", "info");
    
    // Reset to Step 1
    document.getElementById('step2Container').style.display = 'none';
    document.getElementById('step1Container').style.display = 'block';
    document.getElementById('stepItem2').className = 'step-item';
    document.getElementById('stepItem1').className = 'step-item active';

    const btn = document.getElementById('startCaptureBtn');
    if (btn) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-camera-fill"></i> Start Registration';
    }
}

async function finalizeRegistration() {
    // Show Step 3 Loading
    document.getElementById('step2Container').style.display = 'none';
    document.getElementById('step3Container').style.display = 'block';
    document.getElementById('stepItem2').className = 'step-item completed';
    document.getElementById('stepItem3').className = 'step-item active';

    document.getElementById('encodingStatus').textContent = "Compiling Deep AI Face Encodings...";

    try {
        const res = await fetch('/api/register/finalize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: currentStudentName })
        });

        const data = await res.json();
        if (data.success) {
            document.getElementById('encodingLoading').style.display = 'none';
            document.getElementById('registrationSuccessCard').style.display = 'block';
            document.getElementById('successStudentName').textContent = currentStudentName;
            document.getElementById('successSampleCount').textContent = `${data.count} high-resolution images`;
            document.getElementById('stepItem3').className = 'step-item completed';

            showToast("Enrollment Complete", `${currentStudentName} is now active in the recognition database!`, "success");
        } else {
            showToast("Encoding Error", data.message || "Failed to finalize encodings.", "error");
            document.getElementById('encodingStatus').textContent = "Error generating face encodings.";
        }
    } catch (e) {
        showToast("Error", "Failed to build AI encodings.", "error");
        console.error(e);
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
