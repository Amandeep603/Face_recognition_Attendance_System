import sys
import time

def test_environment():
    print("=" * 60)
    print("  AI Face Recognition Attendance System - Environment Check")
    print("=" * 60)
    
    # Test 1: Python Version
    print(f"[1/6] Python Version: {sys.version.split()[0]} ({sys.platform})")
    
    # Test 2: OpenCV
    try:
        import cv2
        print(f"[2/6] OpenCV (cv2) ......... OK (v{cv2.__version__})")
    except ImportError as e:
        print(f"[2/6] OpenCV (cv2) ......... FAILED ({e})")
        return False

    # Test 3: NumPy
    try:
        import numpy as np
        print(f"[3/6] NumPy ................ OK (v{np.__version__})")
    except ImportError as e:
        print(f"[3/6] NumPy ................ FAILED ({e})")
        return False

    # Test 4: dlib & face_recognition
    try:
        import dlib
        import face_recognition
        print(f"[4/6] dlib ................. OK (v{dlib.__version__})")
        print(f"      face_recognition ..... OK (v{face_recognition.__version__})")
        
        # Test synthetic face location inference to ensure model weights work
        dummy_img = np.zeros((300, 300, 3), dtype=np.uint8)
        _ = face_recognition.face_locations(dummy_img, model="hog")
        print(f"      HOG Face Detector .... OK (Model loaded & verified)")
    except ImportError as e:
        print(f"[4/6] face_recognition ..... FAILED ({e})")
        return False
    except Exception as e:
        print(f"[4/6] Model Execution ...... FAILED ({e})")
        return False

    # Test 5: Flask & Pandas & OpenPyXL
    try:
        import flask
        import pandas as pd
        import openpyxl
        print(f"[5/6] Flask ................ OK (v{flask.__version__})")
        print(f"      Pandas ............... OK (v{pd.__version__})")
        print(f"      openpyxl ............. OK (v{openpyxl.__version__})")
    except ImportError as e:
        print(f"[5/6] Web & Data Packages .. FAILED ({e})")
        return False

    # Test 6: Stream URL verification (non-blocking)
    stream_url = "http://192.168.43.105/capture"
    print(f"[6/6] Checking Stream URL .. {stream_url}")
    try:
        cap = cv2.VideoCapture(stream_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        time.sleep(0.5)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print("      ESP32-CAM Stream ..... ONLINE & RECEIVING FRAMES")
            else:
                print("      ESP32-CAM Stream ..... CONNECTED (Waiting for frame)")
        else:
            print("      ESP32-CAM Stream ..... OFFLINE / TIMEOUT (Ensure ESP32-CAM is powered & on Wi-Fi)")
        cap.release()
    except Exception as e:
        print(f"      ESP32-CAM Stream Check: {e}")

    print("\n" + "=" * 60)
    print("  RESULT: All core libraries installed & verified successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)
