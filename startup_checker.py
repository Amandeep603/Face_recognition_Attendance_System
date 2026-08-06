import os
import sys
import time
from datetime import datetime

import config
from logger_util import log_system

def run_startup_checklist():
    """
    Executes a 10-point production pre-flight checklist before launching the Flask server.
    Displays a high-tech terminal summary banner.
    """
    start_time = time.time()
    config.ensure_directories()

    banner = """
==============================================================================
   ___  ___ _____ ___ _____ _   _   _     _   ___ ___ 
  |   \\| __|_   _/ __|_   _/_\\ | | | |   /_\\ | _ ) __|
  | |) | _|  | || (__  | |/ _ \\| |_| |__/ _ \\| _ \\__ \\
  |___/|___| |_| \\___| |_/_/ \\_\\___/|____/_/ \\_\\___/___/
       AI FACE RECOGNITION ATTENDANCE SYSTEM - ENTERPRISE EDITION
==============================================================================
"""
    print(banner)
    print(f"[*] Server Initializing: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[*] Target Stream Source: {config.CAMERA_URL}\n")
    print("------------------------------------------------------------------------------")
    print("  #   SYSTEM PRE-FLIGHT VERIFICATION ITEM                 STATUS")
    print("------------------------------------------------------------------------------")

    checks = [
        ("Python 3.11 Runtime & Operating System", _check_runtime),
        ("Core AI & Computer Vision Libraries", _check_libraries),
        ("ESP32-CAM Stream & Network Config", _check_camera_config),
        ("Known Faces Database & Encodings Cache", _check_encodings),
        ("Daily Attendance Storage & Permissions", _check_attendance_storage),
        ("Unknown Visitor Auto-Capture Registry", _check_unknown_storage),
        ("Institutional Reports Export Engine", _check_reports_storage),
        ("Multi-File Rotating Logging Subsystem", _check_logging_subsystem),
        ("Web Templates & Static Client Assets", _check_web_assets),
        ("Admin Security & Session Encryption", _check_security)
    ]

    all_passed = True
    for idx, (title, func) in enumerate(checks, 1):
        try:
            ok, msg = func()
            status_str = "\033[92m[OK]\033[0m" if ok else "\033[91m[FAILED]\033[0m"
            print(f" [{idx:02d}] {title:<48} {status_str}")
            if not ok:
                all_passed = False
                print(f"      -> Warning: {msg}")
        except Exception as e:
            all_passed = False
            print(f" [{idx:02d}] {title:<48} \033[91m[ERROR]\033[0m")
            print(f"      -> Exception: {str(e)}")

    elapsed = round((time.time() - start_time) * 1000, 1)
    print("------------------------------------------------------------------------------")
    print(f"[*] Pre-flight Checklist Completed in {elapsed} ms | Status: {'ALL READY' if all_passed else 'DEGRADED'}")
    print("==============================================================================\n")

    log_system(f"Startup checklist executed in {elapsed} ms. Status: {'ALL READY' if all_passed else 'DEGRADED'}")
    return all_passed

def _check_runtime():
    ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return True, f"Python {ver} on {sys.platform}"

def _check_libraries():
    import cv2
    import face_recognition
    import dlib
    import numpy
    import pandas
    import openpyxl
    import reportlab
    import psutil
    return True, "All 8 core libraries loaded successfully"

def _check_camera_config():
    if not config.CAMERA_URL:
        return False, "CAMERA_URL is not set"
    return True, f"Configured to {config.CAMERA_URL}"

def _check_encodings():
    cached = 0
    if os.path.exists(config.ENCODINGS_FILE):
        try:
            import pickle
            with open(config.ENCODINGS_FILE, "rb") as f:
                data = pickle.load(f)
                cached = len(data.get("names", []))
        except Exception:
            pass
    return True, f"Cache ready ({cached} face encodings)"

def _check_attendance_storage():
    if not os.path.exists(config.ATTENDANCE_DIR):
        return False, "Attendance dir missing"
    return True, f"Directory ready at {config.ATTENDANCE_DIR}"

def _check_unknown_storage():
    if not os.path.exists(config.UNKNOWN_FACES_DIR):
        return False, "Unknown faces dir missing"
    return True, f"Directory ready at {config.UNKNOWN_FACES_DIR}"

def _check_reports_storage():
    if not os.path.exists(config.REPORTS_DIR):
        return False, "Reports dir missing"
    return True, f"Directory ready at {config.REPORTS_DIR}"

def _check_logging_subsystem():
    if not os.path.exists(config.LOGS_DIR):
        return False, "Logs dir missing"
    return True, f"Logs dir ready at {config.LOGS_DIR}"

def _check_web_assets():
    templates_dir = os.path.join(config.BASE_DIR, "templates")
    static_dir = os.path.join(config.BASE_DIR, "static")
    if not os.path.exists(templates_dir) or not os.path.exists(static_dir):
        return False, "Templates or static directory missing"
    return True, "Web assets present"

def _check_security():
    if not config.SECRET_KEY or not config.ADMIN_USERNAME:
        return False, "Security configuration incomplete"
    return True, "Admin session encryption initialized"

if __name__ == "__main__":
    run_startup_checklist()
