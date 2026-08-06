import os
import cv2
import time
import base64
import json
import shutil
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, Response, request, jsonify, send_file, send_from_directory, session, redirect, url_for

import config
from camera_stream import CameraStream
from attendance_manager import AttendanceManager
from anti_spoofing import AntiSpoofingTracker
from unknown_manager import UnknownFaceManager
from analytics_engine import AnalyticsEngine
from reports_generator import ReportsGenerator
from face_engine import FaceEngine
from health_monitor import HealthMonitor
from diagnostics import SystemDiagnostics
from logger_util import log_system, log_error, get_recent_logs
import startup_checker

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
config.ensure_directories()

# Initialize core subsystems
camera = CameraStream(source=config.CAMERA_SOURCE)
camera.start()

attendance_manager = AttendanceManager()
unknown_manager = UnknownFaceManager()
anti_spoofing = AntiSpoofingTracker()
face_engine = FaceEngine(
    attendance_manager=attendance_manager,
    unknown_manager=unknown_manager,
    anti_spoofing=anti_spoofing
)
analytics_engine = AnalyticsEngine(
    attendance_manager=attendance_manager,
    unknown_manager=unknown_manager,
    anti_spoofing=anti_spoofing
)
reports_generator = ReportsGenerator(attendance_manager=attendance_manager)
health_monitor = HealthMonitor(
    camera_stream=camera,
    face_engine=face_engine,
    attendance_manager=attendance_manager,
    unknown_manager=unknown_manager,
    anti_spoofing=anti_spoofing
)

# In-memory registration session store
registration_sessions = {}

# ----------------- Auth Decorators -----------------

def admin_required(f):
    """Decorator requiring active administrator session for critical endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Admin authorization required."}), 401
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- Video Generator Helpers -----------------

def generate_annotated_stream():
    """Generates multipart MJPEG stream with AI face recognition and anti-spoofing overlays."""
    while True:
        raw_frame = camera.get_frame()
        if raw_frame is not None:
            if camera.status == "online":
                annotated = face_engine.process_frame(raw_frame)
            else:
                annotated = raw_frame

            ret, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)

def generate_raw_stream():
    """Generates clean un-annotated MJPEG stream for registration preview."""
    while True:
        raw_frame = camera.get_frame()
        if raw_frame is not None:
            ret, buffer = cv2.imencode('.jpg', raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)

# ----------------- Web UI Routes -----------------

@app.route('/')
def index():
    """Live Attendance Dashboard."""
    return render_template('index.html', camera_source=camera.source, is_admin=session.get('is_admin', False))

@app.route('/register')
def register_page():
    """Student Registration Wizard Page."""
    return render_template('register.html', is_admin=session.get('is_admin', False))

@app.route('/students')
def students_page():
    """Registered Students Management Page."""
    return render_template('students.html', is_admin=session.get('is_admin', False))

@app.route('/analytics')
def analytics_page():
    """Attendance Analytics & Insights Dashboard."""
    return render_template('analytics.html', is_admin=session.get('is_admin', False))

@app.route('/unknown_faces')
def unknown_faces_page():
    """Unknown Visitors Log Gallery."""
    return render_template('unknown_faces.html', is_admin=session.get('is_admin', False))

@app.route('/reports')
def reports_page():
    """Official Attendance Reports & Exporter."""
    return render_template('reports.html', is_admin=session.get('is_admin', False))

@app.route('/diagnostics')
def diagnostics_page():
    """Automated System Diagnostics & Health Suite Page."""
    return render_template('diagnostics.html', is_admin=session.get('is_admin', False))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    """Admin Login Portal."""
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session['is_admin'] = True
            session['admin_user'] = username
            next_url = request.args.get('next') or '/'
            return redirect(next_url)
        else:
            error = "Invalid administrator username or password."

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Sign out administrator session."""
    session.pop('is_admin', None)
    session.pop('admin_user', None)
    return redirect('/')

# ----------------- Streaming Endpoints -----------------

@app.route('/video_feed')
def video_feed():
    """Annotated live video feed endpoint."""
    return Response(generate_annotated_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/raw_feed')
def raw_feed():
    """Raw camera feed endpoint."""
    return Response(generate_raw_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ----------------- Static File Serves -----------------

@app.route('/thumbnail/<date_str>/<filename>')
def serve_thumbnail(date_str, filename):
    """Serve attendance face crop thumbnails."""
    thumb_dir = os.path.join(config.THUMBNAILS_DIR, date_str)
    return send_from_directory(thumb_dir, filename)

@app.route('/student_photo/<student_name>/<filename>')
def serve_student_photo(student_name, filename):
    """Serve student registration sample photos."""
    student_dir = os.path.join(config.KNOWN_FACES_DIR, student_name)
    return send_from_directory(student_dir, filename)

@app.route('/unknown_photo/<date_str>/<filename>')
def serve_unknown_photo(date_str, filename):
    """Serve unknown visitor face captures."""
    unknown_dir = os.path.join(config.UNKNOWN_FACES_DIR, date_str)
    return send_from_directory(unknown_dir, filename)

# ----------------- Real-time API Endpoints -----------------

@app.route('/api/stats')
@app.route('/api/attendance/stats')
def api_stats():
    """Returns aggregated real-time statistics for the dashboard."""
    stats = attendance_manager.get_stats()
    stats["camera"] = camera.get_status_info()
    stats["server_time"] = datetime.now().strftime("%H:%M:%S")
    stats["server_date"] = datetime.now().strftime("%A, %B %d, %Y")
    stats["last_marked"] = attendance_manager.last_marked_notification
    stats["unknown_faces_today"] = unknown_manager.get_unknown_count_today()
    stats["spoofs_blocked"] = anti_spoofing.spoof_attempts_count
    return jsonify(stats)

@app.route('/api/attendance/today')
def api_attendance_today():
    """Returns list of today's attendance records."""
    records = attendance_manager.get_today_records()
    return jsonify({
        "success": True,
        "date": attendance_manager._get_today_date_str(),
        "total": len(records),
        "records": records
    })

@app.route('/api/attendance/date/<date_str>')
def api_attendance_by_date(date_str):
    """Returns attendance records for a specific date (YYYY-MM-DD)."""
    records = attendance_manager.get_records_by_date(date_str)
    return jsonify({
        "success": True,
        "date": date_str,
        "total": len(records),
        "records": records
    })

@app.route('/api/stream/events')
def sse_events():
    """Server-Sent Events stream for real-time live attendance notifications."""
    def event_stream():
        last_check_time = time.time()
        last_marked_ts = 0
        while True:
            notif = attendance_manager.last_marked_notification
            if notif and notif.get("timestamp", 0) > last_marked_ts:
                last_marked_ts = notif["timestamp"]
                data = json.dumps({"type": "attendance_marked", "record": notif})
                yield f"data: {data}\n\n"

            if time.time() - last_check_time > 3.0:
                stats = attendance_manager.get_stats()
                stats["camera"] = camera.get_status_info()
                stats["unknown_faces_today"] = unknown_manager.get_unknown_count_today()
                stats["spoofs_blocked"] = anti_spoofing.spoof_attempts_count
                data = json.dumps({"type": "heartbeat", "stats": stats})
                yield f"data: {data}\n\n"
                last_check_time = time.time()

            time.sleep(0.5)

    return Response(event_stream(), mimetype="text/event-stream")

# ----------------- Registration Wizard APIs -----------------

@app.route('/api/register/start', methods=['POST'])
def register_start():
    """Initialize a new registration session for a student."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    overwrite = data.get("overwrite", False)
    
    if not name:
        return jsonify({"success": False, "message": "Student name is required."}), 400

    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    if not safe_name:
        return jsonify({"success": False, "message": "Invalid student name characters."}), 400

    student_dir = os.path.join(config.KNOWN_FACES_DIR, safe_name)
    
    if os.path.exists(student_dir) and not overwrite:
        existing_images = [f for f in os.listdir(student_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if len(existing_images) > 0:
            return jsonify({
                "success": False,
                "already_exists": True,
                "message": f"Student '{safe_name}' is already registered with {len(existing_images)} images. Overwrite?"
            })

    os.makedirs(student_dir, exist_ok=True)
    if overwrite:
        for f in os.listdir(student_dir):
            try:
                os.remove(os.path.join(student_dir, f))
            except Exception:
                pass

    registration_sessions[safe_name] = {
        "name": safe_name,
        "saved_crops": [],
        "sample_count": 0,
        "start_time": time.time(),
        "status": "capturing"
    }

    return jsonify({
        "success": True,
        "name": safe_name,
        "target_count": config.REGISTRATION_BURST_COUNT,
        "min_count": config.REGISTRATION_MIN_VALID
    })

@app.route('/api/register/status', methods=['GET'])
def register_status():
    """Returns current status of any active registration session."""
    name = request.args.get("name", "").strip()
    if not name or name not in registration_sessions:
        return jsonify({"active": False, "message": "No active registration session."})

    session_data = registration_sessions[name]
    return jsonify({
        "active": True,
        "name": name,
        "current_count": session_data["sample_count"],
        "target_count": config.REGISTRATION_BURST_COUNT,
        "status": session_data.get("status", "capturing")
    })

@app.route('/api/register/capture_sample', methods=['POST'])
def register_capture_sample():
    """Captures and validates a single frame from the live stream."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if name not in registration_sessions:
        return jsonify({"success": False, "message": "Registration session expired. Please restart."}), 400

    session_data = registration_sessions[name]
    raw_frame = camera.get_raw_frame_nowait()

    if raw_frame is None or camera.status != "online":
        return jsonify({"success": False, "message": "Camera is offline. Please check connection."})

    is_valid, message, face_crop, blur_score = face_engine.capture_registration_sample(
        raw_frame=raw_frame,
        student_name=name,
        sample_idx=session_data["sample_count"],
        previous_frames=session_data["saved_crops"]
    )

    if not is_valid:
        return jsonify({
            "success": False,
            "message": message,
            "blur_score": round(blur_score, 1),
            "current_count": session_data["sample_count"]
        })

    session_data["sample_count"] += 1
    session_data["saved_crops"].append(face_crop)
    
    img_filename = f"{session_data['sample_count']:02d}.jpg"
    img_path = os.path.join(config.KNOWN_FACES_DIR, name, img_filename)
    cv2.imwrite(img_path, raw_frame)

    thumb_small = cv2.resize(face_crop, (100, 100))
    _, buf = cv2.imencode('.jpg', thumb_small)
    thumb_b64 = base64.b64encode(buf).decode('utf-8')

    is_complete = (session_data["sample_count"] >= config.REGISTRATION_BURST_COUNT)
    if is_complete:
        session_data["status"] = "ready_to_finalize"

    return jsonify({
        "success": True,
        "message": f"Captured sample {session_data['sample_count']}/{config.REGISTRATION_BURST_COUNT}",
        "current_count": session_data["sample_count"],
        "target_count": config.REGISTRATION_BURST_COUNT,
        "blur_score": round(blur_score, 1),
        "is_complete": is_complete,
        "thumbnail": f"data:image/jpeg;base64,{thumb_b64}"
    })

@app.route('/api/register/cancel', methods=['POST'])
def register_cancel():
    """Cancels active registration and removes partial files if incomplete."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if name in registration_sessions:
        session_data = registration_sessions.pop(name)
        if session_data["sample_count"] < config.REGISTRATION_MIN_VALID:
            student_dir = os.path.join(config.KNOWN_FACES_DIR, name)
            if os.path.exists(student_dir):
                shutil.rmtree(student_dir, ignore_errors=True)
        return jsonify({"success": True, "message": f"Registration for '{name}' cancelled."})

    return jsonify({"success": True, "message": "No active session to cancel."})

@app.route('/api/register/finalize', methods=['POST'])
def register_finalize():
    """Finalizes student registration and rebuilds face encodings cache."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if name not in registration_sessions:
        return jsonify({"success": False, "message": "Session not found."}), 400

    session_data = registration_sessions[name]
    count = session_data["sample_count"]

    if count < config.REGISTRATION_MIN_VALID:
        return jsonify({
            "success": False,
            "message": f"Only {count} samples captured. Minimum {config.REGISTRATION_MIN_VALID} required."
        }), 400

    face_engine.load_known_faces(force_reload=True)
    del registration_sessions[name]

    return jsonify({
        "success": True,
        "message": f"Student '{name}' registered successfully with {count} face samples!",
        "name": name,
        "count": count
    })

# ----------------- Student Management APIs -----------------

@app.route('/api/students/list')
def api_students_list():
    """Returns list of registered students."""
    students = attendance_manager.get_registered_students()
    return jsonify({"students": students, "total": len(students)})

@app.route('/api/register/delete', methods=['POST'])
@app.route('/api/students/delete', methods=['POST'])
def api_students_delete():
    """Deletes a registered student and updates model encodings."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"success": False, "message": "Name is required."}), 400

    res = attendance_manager.delete_student(name)
    if res["status"] == "success":
        face_engine.load_known_faces(force_reload=True)
        return jsonify({"success": True, "message": f"Student '{name}' deleted successfully."})
    else:
        return jsonify({"success": False, "message": f"Student '{name}' not found."}), 404

# ----------------- Analytics APIs -----------------

@app.route('/api/analytics/summary')
def api_analytics_summary():
    """Returns KPI cards metrics for today."""
    return jsonify(analytics_engine.get_summary_metrics())

@app.route('/api/analytics/trends')
def api_analytics_trends():
    """Returns daily attendance counts over past N days."""
    days = int(request.args.get('days', 7))
    return jsonify(analytics_engine.get_trends_data(days=days))

@app.route('/api/analytics/hourly')
def api_analytics_hourly():
    """Returns check-in frequency distribution across hours of today."""
    return jsonify(analytics_engine.get_hourly_distribution())

@app.route('/api/analytics/rankings')
def api_analytics_rankings():
    """Returns punctuality leader, student breakdown, and chronic absentees."""
    return jsonify(analytics_engine.get_student_rankings())

# ----------------- Unknown Faces APIs -----------------

@app.route('/api/unknown/list')
def api_unknown_list():
    """Returns list of unknown visitor records, optionally filtered by date."""
    date_filter = request.args.get('date', None)
    records = unknown_manager.get_unknown_records(date_filter=date_filter)
    return jsonify(records)

@app.route('/api/unknown/delete', methods=['POST'])
def api_unknown_delete():
    """Deletes an unknown record and its image."""
    data = request.get_json() or {}
    record_id = data.get('record_id', '')
    res = unknown_manager.delete_record(record_id)
    return jsonify(res)

@app.route('/api/unknown/convert', methods=['POST'])
def api_unknown_convert():
    """Converts unknown face capture to registered student."""
    data = request.get_json() or {}
    record_id = data.get('record_id', '')
    student_name = data.get('student_name', '')
    res = unknown_manager.convert_to_student(record_id, student_name)
    if res.get("success"):
        face_engine.load_known_faces(force_reload=True)
    return jsonify(res)

# ----------------- Reports & Export APIs -----------------

@app.route('/api/reports/preview')
def api_reports_preview():
    """Returns report records and summary statistics for UI table preview."""
    report_type = request.args.get('report_type', 'daily')
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    student_name = request.args.get('student_name', None)

    records, summary = reports_generator.fetch_report_data(
        report_type=report_type,
        start_date=start_date,
        end_date=end_date,
        student_name=student_name
    )
    return jsonify({
        "records": records,
        "summary": summary
    })

@app.route('/api/reports/download')
def api_reports_download():
    """Generates and downloads attendance report in requested format (csv, xlsx, pdf)."""
    report_type = request.args.get('report_type', 'daily')
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)
    student_name = request.args.get('student_name', None)
    export_format = request.args.get('format', 'csv').lower()

    if export_format == 'xlsx' or export_format == 'excel':
        filepath, filename = reports_generator.generate_excel(
            report_type=report_type, start_date=start_date, end_date=end_date, student_name=student_name
        )
        return send_file(filepath, as_attachment=True, download_name=filename)
    elif export_format == 'pdf':
        filepath, filename = reports_generator.generate_pdf(
            report_type=report_type, start_date=start_date, end_date=end_date, student_name=student_name
        )
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        filepath, filename = reports_generator.generate_csv(
            report_type=report_type, start_date=start_date, end_date=end_date, student_name=student_name
        )
        return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/api/attendance/export/csv')
def export_csv_legacy():
    """Legacy export CSV endpoint."""
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    csv_path = attendance_manager._get_csv_path(date_str)
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            f.write("Name,Date,Time,Status\n")
    return send_file(csv_path, as_attachment=True, download_name=f"Attendance_{date_str}.csv")

@app.route('/api/attendance/export/excel')
def export_excel_legacy():
    """Legacy export Excel endpoint."""
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    excel_path = attendance_manager.export_excel(date_str)
    return send_file(excel_path, as_attachment=True, download_name=f"Attendance_{date_str}.xlsx")

@app.route('/api/attendance/reset', methods=['POST'])
def reset_attendance():
    """Reset today's attendance records."""
    res = attendance_manager.reset_today_attendance()
    return jsonify(res)

@app.route('/api/camera/source', methods=['POST'])
def update_camera_source():
    """Switch camera source (e.g. ESP32 URL or local webcam)."""
    data = request.get_json() or {}
    new_source = data.get("source", "").strip()
    if not new_source:
        return jsonify({"success": False, "message": "Source cannot be empty."}), 400

    camera.set_source(new_source)
    return jsonify({"success": True, "message": f"Camera source set to: {new_source}"})

# ----------------- Diagnostics & Health APIs -----------------

@app.route('/api/diagnostics/run', methods=['GET'])
def api_run_diagnostics():
    """Runs the 10-point end-to-end automated system diagnostics suite."""
    try:
        diag = SystemDiagnostics()
        report = diag.run_all()
        return jsonify({
            "status": "success",
            "report": report
        })
    except Exception as e:
        log_error("Failed to run diagnostics", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    """Returns real-time telemetry snapshot (CPU, Memory, FPS, Latency, Storage, Counters)."""
    try:
        data = health_monitor.get_full_health_snapshot()
        return jsonify({
            "status": "success",
            "health": data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logs/<log_name>', methods=['GET'])
@admin_required
def api_get_logs(log_name):
    """Fetch recent lines from system, attendance, or recognition logs."""
    try:
        lines = get_recent_logs(log_name, lines=60)
        return jsonify({
            "status": "success",
            "log": log_name,
            "lines": lines
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ----------------- Application Entry Point -----------------

if __name__ == '__main__':
    # 1. Run production pre-flight startup checklist
    startup_checker.run_startup_checklist()
    
    print(f"\n=======================================================")
    print(f"  AI Face Recognition Attendance System (Enterprise)")
    print(f"  Camera Source : {camera.source}")
    print(f"  Server URL    : http://127.0.0.1:{config.PORT}")
    print(f"  Anti-Spoofing : {'ENABLED' if config.ANTI_SPOOFING_ENABLED else 'DISABLED'}")
    print(f"=======================================================\n")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
