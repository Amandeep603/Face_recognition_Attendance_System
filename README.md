# 📸 AI Face Recognition Attendance System (ESP32-CAM)

An enterprise-grade, high-performance **AI Face Recognition Attendance System** engineered with Python 3.11, Flask, OpenCV, Dlib/face_recognition, and a modern glassmorphic web dashboard. Designed to work directly with an **ESP32-CAM live MJPEG stream** with multi-frame anti-spoofing liveness verification, automated 20-frame student registration, unknown visitor auto-capture, institutional reports export (CSV, styled Excel, PDF), analytics, and automated 10-point self-diagnostics.

---

## 🌟 Key Features

1. **ESP32-CAM MJPEG Resilient Streaming:**
   - Zero-latency buffer management with background thread reading.
   - Automatic exponential backoff auto-reconnect with sleek "Reconnecting..." HUD overlay.
   - Dynamic FPS counter and network bitrate monitoring.
   - Fallback video test loop if ESP32-CAM hardware is temporarily unplugged.

2. **Core AI Face Recognition:**
   - Optimized with frame-skipping (every 3rd frame) and `0.5x` downscaled processing.
   - Multi-metric nearest neighbor recognition using Euclidean `face_distance` with `0.45` tolerance.
   - Real-time confidence percentage calculation and dynamic color-coded HUD bounding boxes.
   - `encodings.pkl` cache persistence with auto-regeneration when student photos change.

3. **Multi-Frame Anti-Spoofing & Liveness Gating:**
   - Eye Aspect Ratio (EAR) blink detection using facial landmarks.
   - Laplacian frequency domain spectral texture analysis (detects phone screens, glossy paper, monitors).
   - Multi-frame spatiotemporal tracking prevents static photo bypass.
   - Liveness badges: `Live Face Verified` (Green) vs. `Spoof Detected` (Red).

4. **Automated Student Registration Wizard:**
   - 20-frame automated burst capture with Laplacian blur rejection (sharpness threshold > 60).
   - Pose diversity guidance (Center, Turn Left, Turn Right, Look Up, Look Down).
   - Automatic multi-angle face encoding generation with immediate roster reload.

5. **Institutional Attendance Management:**
   - Daily CSV schema: `Name, Date, Time, Status` (`Attendance_YYYY-MM-DD.csv`).
   - Strict once-per-student-per-day enforcement.
   - Instant real-time UI updates via polling / SSE with audio chimes.
   - Automatic high-resolution portrait thumbnail crops for every check-in.

6. **Multi-Format Export Engine:**
   - **CSV Export:** RFC 4180 standard daily & weekly roll-up.
   - **Excel (.xlsx) Export:** Styled headers, zebra rows, summary formulas via `openpyxl`.
   - **PDF Export:** Printable institutional attendance report with header logo and summary statistics via `reportlab`.

7. **System Diagnostics & Telemetry Suite:**
   - 10-point automated self-test runner (`diagnostics.py`).
   - Telemetry dashboard tracking CPU %, Memory MB, stream FPS, AI latency (ms).
   - Multi-target rotating loggers (`system.log`, `attendance.log`, `recognition.log`, `error.log`).

---

## 🛠️ Tech Stack

- **Backend:** Python 3.11, Flask 3.1.3, Werkzeug
- **Computer Vision & AI:** OpenCV 4.10, Dlib 19.24.1, face_recognition 1.3.0, NumPy
- **Data & Reports:** Pandas, openpyxl, ReportLab
- **Hardware Integration:** ESP32-CAM (AI-Thinker OV2640)
- **Frontend:** Vanilla HTML5, Modern CSS (Glassmorphism, Dark/Light Themes), JavaScript (ES6), Chart.js, Bootstrap Icons, Font Awesome 6

---

## 🚀 Quick Start Guide (Windows)

### 1. Automated Installation
Double-click `install.bat` or run:
```bash
python -m pip install -r requirements.txt
```

### 2. Start the Server
Double-click `start.bat` or run:
```bash
python app.py
```
Open your browser at: **`http://127.0.0.1:5000`**

### 3. Run Self-Diagnostics
Double-click `test.bat` or run:
```bash
python diagnostics.py
```

---

## ⚙️ Configuration (`config.py` / `.env`)

You can customize camera streams and thresholds in `.env` or `config.py`:
```ini
CAMERA_URL=http://192.168.18.142:81/stream
RECOGNITION_TOLERANCE=0.45
FRAME_SKIP=3
PROCESS_SCALE=0.5
ANTI_SPOOFING_ENABLED=True
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

---

## 📁 Project Directory Structure

```
FaceAttendance/
├── app.py                     # Primary Flask Web Server & API Gateway
├── config.py                  # Unified Configuration & Constants
├── camera_stream.py           # Resilient ESP32-CAM MJPEG Stream Engine
├── face_engine.py             # AI Recognition & HUD Drawing Engine
├── anti_spoofing.py           # Multi-Factor Liveness & Anti-Spoofing Tracker
├── attendance_manager.py      # Daily Attendance Records & Thumbnail Store
├── unknown_manager.py         # Unknown Face Auto-Capture & Conversion
├── analytics_engine.py        # Trend Aggregation & KPI Analytics
├── reports_generator.py       # CSV, Excel (.xlsx), & PDF Report Exporter
├── health_monitor.py          # Real-Time Telemetry & Hardware Resource Monitor
├── logger_util.py             # Multi-Target Rotating File Logger
├── startup_checker.py         # 10-Point Pre-Flight Server Verifier
├── diagnostics.py             # 10-Point Automated Test Suite
├── requirements.txt           # Production Dependencies & Pre-Built Dlib Wheel
├── start.bat                  # One-Click Windows Launch Script
├── install.bat                # One-Click Dependency Installer
├── test.bat                   # One-Click Diagnostic Test Runner
├── TEST_REPORT.md             # 10/10 Diagnostic Test Verification Report
├── templates/                 # Glassmorphic Responsive HTML5 Templates
│   ├── index.html             # Live Camera Dashboard & Attendance Panel
│   ├── register.html          # Student Registration 20-Shot Wizard
│   ├── students.html          # Student Directory & Roster Management
│   ├── analytics.html         # Interactive Attendance Graphs & Heatmaps
│   ├── unknown_faces.html     # Unknown Visitors Gallery & Conversion Tool
│   ├── reports.html           # Multi-Format Report Exporter
│   ├── diagnostics.html       # Automated Health & Diagnostics Dashboard
│   └── login.html             # Secure Administrator Authentication
├── static/                    # Frontend Styles, Scripts & Assets
│   ├── css/style.css          # Ultra-Premium Modern Glassmorphic Design System
│   ├── js/dashboard.js        # Real-time Stream & Attendance Polling
│   ├── js/register.js         # Interactive Capture Flow & Progress Bar
│   ├── js/analytics.js        # Chart.js Visualizations & KPI Counters
│   ├── js/diagnostics.js      # Diagnostic Test Runner & Console View
│   └── js/theme.js            # Dark/Light Mode Theme Switcher
├── known_faces/               # Registered Student Photo Repositories
├── attendance/                # Daily Attendance CSV Logs & Crop Thumbnails
├── unknown_faces/             # Auto-Captured Unknown Visitor Crops & metadata.json
├── reports/                   # Generated Excel & PDF Report Files
└── logs/                      # Rotating System, Attendance & Recognition Logs
```

---

## 🔒 Security & Admin Access
Default Administrator Credentials:
- **Username:** `admin`
- **Password:** `admin`

Protected operations (deleting student records, clearing attendance logs, downloading internal audit logs) require admin login.

---

## 📊 Diagnostic Test Status
✅ **10 / 10 Automated System Tests Passed** (See [TEST_REPORT.md](file:///c:/Users/amand/Downloads/medein%20labs/FaceAttendance/TEST_REPORT.md) for full execution traces).
