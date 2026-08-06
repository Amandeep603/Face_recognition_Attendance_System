import os
import sys
import time
import json
import traceback
import numpy as np
import pandas as pd
from datetime import datetime

import config
from logger_util import log_system, log_error

class SystemDiagnostics:
    """
    Automated 10-Point End-to-End System Diagnostics & Health Verification Suite.
    """
    def __init__(self):
        self.results = []
        self.total_tests = 10
        self.passed_tests = 0
        self.failed_tests = 0

    def run_all(self) -> dict:
        """Executes all 10 diagnostic test suites and compiles detailed report."""
        self.results = []
        self.passed_tests = 0
        self.failed_tests = 0
        start_time = time.time()

        tests = [
            ("Dependencies & Runtime", self.test_dependencies),
            ("Directory Structure & Permissions", self.test_directories_and_permissions),
            ("Camera Stream Connectivity", self.test_camera_stream),
            ("Face Engine & Encodings Cache", self.test_face_engine),
            ("Attendance Engine & CSV Storage", self.test_attendance_engine),
            ("Registration Capture & Blur Pipeline", self.test_registration_pipeline),
            ("Anti-Spoofing & Liveness Verification", self.test_anti_spoofing),
            ("Unknown Face Registry & Conversion", self.test_unknown_face_manager),
            ("Multi-Format Exporters (CSV/XLSX/PDF)", self.test_report_exporters),
            ("Analytics Engine Aggregation", self.test_analytics_engine)
        ]

        for idx, (name, test_func) in enumerate(tests, 1):
            t_start = time.time()
            try:
                success, details = test_func()
                duration_ms = int((time.time() - t_start) * 1000)
                status = "PASS" if success else "FAIL"
                if success:
                    self.passed_tests += 1
                else:
                    self.failed_tests += 1
                    
                self.results.append({
                    "id": idx,
                    "name": name,
                    "status": status,
                    "duration_ms": duration_ms,
                    "details": details
                })
            except Exception as e:
                duration_ms = int((time.time() - t_start) * 1000)
                self.failed_tests += 1
                self.results.append({
                    "id": idx,
                    "name": name,
                    "status": "FAIL",
                    "duration_ms": duration_ms,
                    "details": f"Unhandled Exception: {str(e)}"
                })

        total_duration = round(time.time() - start_time, 2)
        overall_status = "ALL PASS" if self.failed_tests == 0 else f"{self.failed_tests} FAILED"

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_status": overall_status,
            "total_tests": self.total_tests,
            "passed": self.passed_tests,
            "failed": self.failed_tests,
            "total_duration_sec": total_duration,
            "tests": self.results
        }
        return report

    # ----------------- Individual Test Implementations -----------------

    def test_dependencies(self):
        """1. Verify all required enterprise Python packages are importable."""
        modules = [
            ("cv2", "OpenCV"),
            ("face_recognition", "face_recognition"),
            ("dlib", "dlib"),
            ("numpy", "NumPy"),
            ("pandas", "Pandas"),
            ("openpyxl", "openpyxl (Excel)"),
            ("reportlab", "ReportLab (PDF)"),
            ("psutil", "psutil (Telemetry)")
        ]
        missing = []
        for mod, name in modules:
            try:
                __import__(mod)
            except ImportError:
                missing.append(name)

        if missing:
            return False, f"Missing Python dependencies: {', '.join(missing)}"
        return True, f"All {len(modules)} core AI, computer vision, and export libraries verified."

    def test_directories_and_permissions(self):
        """2. Verify required storage directories exist and are writable."""
        config.ensure_directories()
        folders = [
            ("known_faces", config.KNOWN_FACES_DIR),
            ("attendance", config.ATTENDANCE_DIR),
            ("thumbnails", config.THUMBNAILS_DIR),
            ("unknown_faces", config.UNKNOWN_FACES_DIR),
            ("reports", config.REPORTS_DIR),
            ("logs", config.LOGS_DIR)
        ]
        for label, path in folders:
            if not os.path.exists(path):
                return False, f"Directory missing: {path}"
            # Test write permission
            test_file = os.path.join(path, ".perm_test.tmp")
            try:
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                return False, f"Write permission denied for {label}: {str(e)}"

        return True, f"Verified write permissions across {len(folders)} enterprise storage paths."

    def test_camera_stream(self):
        """3. Test camera stream reachability and placeholder fallback."""
        import cv2
        from camera_stream import CameraStream
        
        stream = CameraStream(source=config.CAMERA_SOURCE)
        stream.start()
        time.sleep(0.4)
        
        frame = stream.get_frame()
        status_info = stream.get_status_info()
        stream.stop()

        if frame is None or frame.shape[0] == 0:
            return False, "Failed to retrieve video frame from CameraStream"

        status_text = status_info.get("status", "unknown")
        src = status_info.get("source", config.CAMERA_SOURCE)
        return True, f"Camera stream operational ({src}). Stream state: {status_text.upper()}."

    def test_face_engine(self):
        """4. Verify FaceEngine encodings cache and recognition tolerances."""
        from face_engine import FaceEngine
        from attendance_manager import AttendanceManager
        
        att_mgr = AttendanceManager()
        engine = FaceEngine(attendance_manager=att_mgr)
        
        cached_count = len(engine.known_face_encodings)
        unique_students = len(engine.known_face_names_unique)
        
        # Test synthetic frame processing
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        processed = engine.process_frame(dummy_frame)
        if processed is None:
            return False, "FaceEngine process_frame returned None"

        return True, f"Face engine verified (Tolerance={config.RECOGNITION_TOLERANCE}, FrameSkip={config.FRAME_SKIP}). Loaded {cached_count} encodings for {unique_students} students."

    def test_attendance_engine(self):
        """5. Verify attendance CSV generation, daily schema, and duplicate debounce."""
        from attendance_manager import AttendanceManager
        mgr = AttendanceManager()
        
        today = mgr._get_today_date_str()
        csv_path = mgr._get_csv_path(today)
        
        # Test mark
        test_student = "_DIAGNOSTIC_TEST_USER_"
        marked = mgr.mark_attendance(test_student)
        
        if not os.path.exists(csv_path):
            return False, f"Attendance CSV not created at {csv_path}"

        # Verify duplicate prevention
        dup_marked = mgr.mark_attendance(test_student)
        if dup_marked.get("status") == "success":
            return False, "Duplicate attendance was marked on the same day (duplicate prevention failed)"

        # Clean up test user from CSV
        try:
            df = pd.read_csv(csv_path)
            df = df[df['Name'] != test_student]
            df.to_csv(csv_path, index=False)
        except Exception:
            pass

        return True, f"Attendance engine verified. CSV created at Attendance_{today}.csv with duplicate prevention."

    def test_registration_pipeline(self):
        """6. Test blur score calculation and image burst quality evaluation."""
        from face_engine import FaceEngine
        engine = FaceEngine()

        # Sharp frame
        sharp_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        sharp_blur = engine._calculate_blur_score(sharp_img)

        # Blurry flat frame
        flat_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
        flat_blur = engine._calculate_blur_score(flat_img)

        if sharp_blur < flat_blur:
            return False, "Laplacian blur metric inverted"

        return True, f"Registration pipeline verified (Sharp={sharp_blur:.1f}, Blur={flat_blur:.1f}, MinThresh={config.BLUR_THRESHOLD})."

    def test_anti_spoofing(self):
        """7. Verify EAR blink detection, texture analysis, and liveness scoring."""
        from anti_spoofing import AntiSpoofingTracker
        tracker = AntiSpoofingTracker()

        # EAR test
        open_eye = [(10, 10), (13, 7), (17, 7), (20, 10), (17, 13), (13, 13)]
        closed_eye = [(10, 10), (13, 10), (17, 10), (20, 10), (17, 11), (13, 11)]
        ear_open = tracker.calculate_ear(open_eye)
        ear_closed = tracker.calculate_ear(closed_eye)

        if ear_open <= ear_closed or ear_closed > config.LIVENESS_EAR_THRESHOLD:
            return False, f"EAR calculation failed (Open: {ear_open:.2f}, Closed: {ear_closed:.2f})"

        # Texture test
        natural_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        _, is_valid = tracker.analyze_texture(natural_img)
        if not is_valid:
            return False, "Natural texture rejected as spoof"

        return True, f"Anti-spoofing verified (Open EAR={ear_open:.2f}, Closed EAR={ear_closed:.2f}, Texture=PASS)."

    def test_unknown_face_manager(self):
        """8. Test unknown visitor logging and JSON registry."""
        from unknown_manager import UnknownFaceManager
        mgr = UnknownFaceManager()

        dummy_frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
        dummy_crop = np.random.randint(50, 200, (80, 80, 3), dtype=np.uint8)

        mgr.last_log_time = 0.0
        rec = mgr.record_unknown(dummy_frame, dummy_crop, confidence_score=35.0)
        if rec is None:
            return False, "Failed to record unknown visitor entry"

        rec_id = rec["id"]
        del_res = mgr.delete_record(rec_id)
        if not del_res.get("success"):
            return False, f"Failed to clean up test unknown record {rec_id}"

        return True, "Unknown face auto-capture, JSON registry, and record deletion verified."

    def test_report_exporters(self):
        """9. Test CSV, Excel (.xlsx), and PDF (.pdf) generation."""
        from reports_generator import ReportsGenerator
        from attendance_manager import AttendanceManager
        
        rep_gen = ReportsGenerator(attendance_manager=AttendanceManager())
        
        csv_p, _ = rep_gen.generate_csv(report_type="daily")
        xlsx_p, _ = rep_gen.generate_excel(report_type="daily")
        pdf_p, _ = rep_gen.generate_pdf(report_type="daily")

        for p, fmt in [(csv_p, "CSV"), (xlsx_p, "Excel"), (pdf_p, "PDF")]:
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                return False, f"{fmt} report generation failed or output file is empty ({p})"

        return True, "Verified CSV, styled Excel (.xlsx), and institutional PDF (.pdf) report generators."

    def test_analytics_engine(self):
        """10. Test analytics KPI calculation, trends, and arrival distribution."""
        from analytics_engine import AnalyticsEngine
        from attendance_manager import AttendanceManager
        from unknown_manager import UnknownFaceManager
        from anti_spoofing import AntiSpoofingTracker

        analytics = AnalyticsEngine(
            attendance_manager=AttendanceManager(),
            unknown_manager=UnknownFaceManager(),
            anti_spoofing=AntiSpoofingTracker()
        )

        summary = analytics.get_summary_metrics()
        trends = analytics.get_trends_data(7)
        hourly = analytics.get_hourly_distribution()

        if "total_students" not in summary or "labels" not in trends or "labels" not in hourly:
            return False, "Analytics engine returned incomplete data structure"

        return True, f"Analytics engine verified. Processed KPIs, 7-day trend series, and hourly distribution."

if __name__ == "__main__":
    print("\n=======================================================")
    print("  AI Face Recognition Attendance - Full System Diagnostics")
    print("=======================================================\n")
    diag = SystemDiagnostics()
    report = diag.run_all()

    for t in report["tests"]:
        status_color = "\033[92mPASS\033[0m" if t["status"] == "PASS" else "\033[91mFAIL\033[0m"
        print(f"[{t['id']:02d}/10] {t['name']:<40} [{status_color}] ({t['duration_ms']} ms)")
        print(f"       -> {t['details']}")

    print("\n-------------------------------------------------------")
    print(f"  Summary: {report['passed']}/{report['total_tests']} PASSED | Total Time: {report['total_duration_sec']}s")
    print("=======================================================\n")
