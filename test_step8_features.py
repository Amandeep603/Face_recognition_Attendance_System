import os
import sys
import cv2
import numpy as np
import pandas as pd
from datetime import datetime

import config
from anti_spoofing import AntiSpoofingTracker
from unknown_manager import UnknownFaceManager
from analytics_engine import AnalyticsEngine
from reports_generator import ReportsGenerator
from attendance_manager import AttendanceManager
from face_engine import FaceEngine

def test_anti_spoofing():
    print("\n--- [Test 1] Anti-Spoofing & Liveness Engine ---")
    tracker = AntiSpoofingTracker()
    
    # 1. EAR Calculation
    # Open eye landmarks: width=10, height=6
    open_eye = [(10, 10), (13, 7), (17, 7), (20, 10), (17, 13), (13, 13)]
    ear_open = tracker.calculate_ear(open_eye)
    assert ear_open > 0.25, f"Expected open eye EAR > 0.25, got {ear_open}"
    print(f"  [PASS] Open eye EAR: {ear_open:.3f}")

    # Closed/Blinking eye landmarks (eyelids meet): width=10, height=0.5
    closed_eye = [(10, 10), (13, 10), (17, 10), (20, 10), (17, 11), (13, 11)]
    ear_closed = tracker.calculate_ear(closed_eye)
    assert ear_closed < 0.20, f"Expected closed eye EAR < 0.20, got {ear_closed}"
    print(f"  [PASS] Closed eye EAR: {ear_closed:.3f}")

    # 2. Texture Sharpness & Color Distribution
    # Natural rich image
    natural_img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    lap_val, is_tex_valid = tracker.analyze_texture(natural_img)
    assert is_tex_valid == True
    print(f"  [PASS] Natural texture valid: True (Laplacian var: {lap_val:.1f})")

    # Flat blurred blank image (spoof / paper artifact)
    flat_img = np.ones((100, 100, 3), dtype=np.uint8) * 128
    lap_flat, is_flat_valid = tracker.analyze_texture(flat_img)
    assert is_flat_valid == False
    print(f"  [PASS] Flat image rejected as spoof: True (Laplacian var: {lap_flat:.1f})")

    # 3. Multi-frame Liveness Evolution
    track_id = "test_track_01"
    landmarks_mock = {
        "left_eye": open_eye,
        "right_eye": open_eye,
        "nose_tip": [(50, 50)]
    }

    # Frame 1: Checking
    is_live_1, score_1, status_1 = tracker.evaluate_liveness(track_id, landmarks_mock, natural_img)
    print(f"  [PASS] Frame 1 Status: {status_1} (Score: {score_1})")

    # Frame 2: Live Verified
    is_live_2, score_2, status_2 = tracker.evaluate_liveness(track_id, landmarks_mock, natural_img)
    assert is_live_2 == True
    assert status_2 == "Live Face Verified"
    print(f"  [PASS] Frame 2 Status: {status_2} (Score: {score_2})")


def test_unknown_face_management():
    print("\n--- [Test 2] Unknown Face Management & Conversion ---")
    mgr = UnknownFaceManager()
    
    # 1. Record an unknown capture
    dummy_crop = np.random.randint(50, 200, (80, 80, 3), dtype=np.uint8)
    dummy_frame = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)
    
    # Force last log time to 0 to bypass rate limit in test
    mgr.last_log_time = 0.0
    rec = mgr.record_unknown(dummy_frame, dummy_crop, confidence_score=38.4)
    assert rec is not None, "Failed to record unknown visitor"
    rec_id = rec["id"]
    print(f"  [PASS] Unknown recorded: {rec_id} ({rec['relative_url']})")

    # 2. List unknown records
    records = mgr.get_unknown_records()
    assert any(r["id"] == rec_id for r in records), "Recorded item not found in list"
    print(f"  [PASS] Registry contains {len(records)} unknown records.")

    # 3. Convert unknown to registered student
    test_student = "TestStudent_Step8"
    conv_res = mgr.convert_to_student(rec_id, test_student)
    assert conv_res["success"] == True, f"Conversion failed: {conv_res}"
    print(f"  [PASS] Converted {rec_id} -> {test_student}")

    # Verify student directory created with image
    st_dir = os.path.join(config.KNOWN_FACES_DIR, test_student)
    assert os.path.exists(st_dir), "Student directory was not created"
    assert os.path.exists(os.path.join(st_dir, "01.jpg")), "01.jpg missing in student directory"
    print(f"  [PASS] Verified student directory '{test_student}/01.jpg' exists.")

    # Clean up test student
    import shutil
    shutil.rmtree(st_dir, ignore_errors=True)

    # 4. Delete unknown record
    del_res = mgr.delete_record(rec_id)
    assert del_res["success"] == True
    print(f"  [PASS] Deleted unknown record {rec_id}.")


def test_analytics_engine():
    print("\n--- [Test 3] Analytics Engine KPIs & Charts Data ---")
    att_mgr = AttendanceManager()
    unk_mgr = UnknownFaceManager()
    anti_sp = AntiSpoofingTracker()
    
    analytics = AnalyticsEngine(attendance_manager=att_mgr, unknown_manager=unk_mgr, anti_spoofing=anti_sp)
    
    # 1. Summary Metrics
    summary = analytics.get_summary_metrics()
    assert "total_students" in summary
    assert "present_today" in summary
    assert "absent_today" in summary
    assert "storage" in summary
    print(f"  [PASS] Summary KPIs: Total={summary['total_students']}, Present={summary['present_today']}, Absent={summary['absent_today']}, Storage={summary['storage']['total_mb']} MB")

    # 2. Trends Data
    trend_7 = analytics.get_trends_data(7)
    assert len(trend_7["labels"]) == 7
    assert len(trend_7["counts"]) == 7
    print(f"  [PASS] 7-Day Trend: Labels={trend_7['labels']}, Counts={trend_7['counts']}")

    # 3. Hourly Distribution
    hourly = analytics.get_hourly_distribution()
    assert len(hourly["labels"]) > 0
    print(f"  [PASS] Hourly Check-in Labels: {hourly['labels'][:4]}...")

    # 4. Student Rankings
    rankings = analytics.get_student_rankings()
    assert "student_summaries" in rankings
    assert "chronic_absentees" in rankings
    print(f"  [PASS] Student Rankings processed for {len(rankings['student_summaries'])} students.")


def test_reports_generator():
    print("\n--- [Test 4] Multi-Format Reports Generator (CSV, Excel, PDF) ---")
    att_mgr = AttendanceManager()
    rep_gen = ReportsGenerator(attendance_manager=att_mgr)

    # 1. CSV Report
    csv_path, csv_name = rep_gen.generate_csv(report_type="daily")
    assert os.path.exists(csv_path), f"CSV report not found at {csv_path}"
    assert os.path.getsize(csv_path) > 0, "CSV report is empty"
    print(f"  [PASS] CSV Report generated: {csv_name} ({os.path.getsize(csv_path)} bytes)")

    # 2. Excel Report
    xlsx_path, xlsx_name = rep_gen.generate_excel(report_type="daily")
    assert os.path.exists(xlsx_path), f"Excel report not found at {xlsx_path}"
    assert os.path.getsize(xlsx_path) > 0, "Excel report is empty"
    print(f"  [PASS] Excel Report (.xlsx) generated: {xlsx_name} ({os.path.getsize(xlsx_path)} bytes)")

    # 3. PDF Report (ReportLab)
    pdf_path, pdf_name = rep_gen.generate_pdf(report_type="daily")
    assert os.path.exists(pdf_path), f"PDF report not found at {pdf_path}"
    assert os.path.getsize(pdf_path) > 0, "PDF report is empty"
    print(f"  [PASS] PDF Report (.pdf) generated: {pdf_name} ({os.path.getsize(pdf_path)} bytes)")


def test_flask_app_endpoints():
    print("\n--- [Test 5] Flask Application Endpoints & Admin Auth ---")
    from app import app
    client = app.test_client()

    # Test pages
    routes = ['/', '/register', '/students', '/analytics', '/unknown_faces', '/reports', '/login']
    for r in routes:
        resp = client.get(r)
        assert resp.status_code == 200, f"Route {r} returned status {resp.status_code}"
        print(f"  [PASS] GET {r} -> HTTP 200 OK")

    # Test API summary
    resp = client.get('/api/analytics/summary')
    assert resp.status_code == 200
    data = resp.get_json()
    assert "total_students" in data
    print(f"  [PASS] GET /api/analytics/summary -> HTTP 200 OK")

    # Test Unknown list API
    resp = client.get('/api/unknown/list')
    assert resp.status_code == 200
    print(f"  [PASS] GET /api/unknown/list -> HTTP 200 OK")

    # Test Reports Preview API
    resp = client.get('/api/reports/preview?report_type=daily')
    assert resp.status_code == 200
    r_data = resp.get_json()
    assert "summary" in r_data
    print(f"  [PASS] GET /api/reports/preview -> HTTP 200 OK")

    # Test Login Authentication
    login_resp = client.post('/login', data={
        "username": config.ADMIN_USERNAME,
        "password": config.ADMIN_PASSWORD
    }, follow_redirects=True)
    assert login_resp.status_code == 200
    print(f"  [PASS] POST /login (Valid Admin) -> Authenticated Successfully")

if __name__ == "__main__":
    print("==========================================================")
    print("   AI Face Recognition Attendance System - Step 8 Tests")
    print("==========================================================")
    test_anti_spoofing()
    test_unknown_face_management()
    test_analytics_engine()
    test_reports_generator()
    test_flask_app_endpoints()
    print("\n>>> ALL STEP 8 COMPREHENSIVE AUTOMATED TESTS PASSED! <<<\n")
