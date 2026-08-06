import os
import cv2
import time
import numpy as np
from datetime import datetime
from attendance_manager import AttendanceManager
import config

def test_attendance_pipeline():
    print("=" * 65)
    print("  Testing Attendance Manager & Real-Time Logic")
    print("=" * 65)

    am = AttendanceManager()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. Reset today for clean test run
    print("[1/5] Resetting test state...")
    am.reset_today_attendance()
    stats = am.get_stats()
    assert stats["present_today"] == 0, "Present count should be 0 after reset"
    print("      [OK] Reset verified.")

    # 2. Test First Attendance Marking
    print("\n[2/5] Testing attendance marking for student 'Amandeep'...")
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(dummy_frame, (100, 100), (300, 300), (255, 200, 100), -1)
    
    res1 = am.mark_attendance("Amandeep", dummy_frame, (100, 300, 300, 100), confidence=94.5)
    print(f"      Response: {res1}")
    assert res1["status"] == "success", f"Expected success, got {res1['status']}"
    
    # Check CSV content
    records = am.get_today_records()
    assert len(records) == 1, f"Expected 1 record, got {len(records)}"
    assert records[0]["name"] == "Amandeep"
    assert records[0]["status"] == "Present"
    print("      [OK] Attendance marked and CSV updated successfully.")

    # Check Thumbnail creation
    thumb_path = os.path.join(config.THUMBNAILS_DIR, today_str, "Amandeep.jpg")
    assert os.path.exists(thumb_path), f"Thumbnail not created at {thumb_path}"
    print(f"      [OK] Face thumbnail verified: {thumb_path}")

    # 3. Test Duplicate Blocking on the same day
    print("\n[3/5] Testing duplicate attendance prevention...")
    res2 = am.mark_attendance("Amandeep", dummy_frame, (100, 300, 300, 100), confidence=96.1)
    print(f"      Second attempt response: {res2}")
    assert res2["status"] == "already_marked", f"Duplicate entry was not blocked: {res2}"
    
    # Verify records count did not increase
    records_after = am.get_today_records()
    assert len(records_after) == 1, f"Duplicate was added to CSV! Count: {len(records_after)}"
    print("      [OK] Duplicate entry blocked successfully (strictly 1 per student per day).")

    # 4. Test Excel & CSV Export
    print("\n[4/5] Testing Excel (.xlsx) and CSV export...")
    csv_file = am._get_csv_path()
    assert os.path.exists(csv_file), "CSV file does not exist"
    print(f"      [OK] CSV Export verified: {csv_file}")

    excel_file = am.export_excel()
    assert os.path.exists(excel_file), "Excel file does not exist"
    print(f"      [OK] Excel (.xlsx) Export verified: {excel_file}")

    # 5. Test System Stats aggregation
    print("\n[5/5] Testing Stats API Aggregation...")
    stats = am.get_stats()
    print(f"      Stats: Total Registered={stats['total_registered']}, Present={stats['present_today']}, Absent={stats['absent_today']}")
    assert stats["present_today"] == 1
    assert len(stats["recent_records"]) == 1
    print("      [OK] Stats aggregation verified.")

    print("\n" + "=" * 65)
    print("  ALL ATTENDANCE LOGIC & INTEGRATION TESTS PASSED! (5/5)")
    print("=" * 65)

if __name__ == "__main__":
    test_attendance_pipeline()
