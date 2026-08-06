import cv2
import time
import sys
import config
from camera_stream import CameraStream
from face_engine import FaceEngine

def main():
    print("=" * 65)
    print("  ESP32-CAM AI Face Recognition Engine - Live Test")
    print("=" * 65)
    print(f"[*] Stream Source: {config.CAMERA_SOURCE}")
    print(f"[*] Recognition Tolerance: {config.RECOGNITION_TOLERANCE}")
    print(f"[*] Frame Skip: {config.FRAME_SKIP}")
    print(f"[*] Process Scale: {config.PROCESS_SCALE}x")
    print(f"[*] Attendance Marking: DISABLED (Recognition & Detection Test Mode)")
    print("=" * 65)

    # 1. Initialize Face Engine without AttendanceManager (Pure Recognition)
    engine = FaceEngine(attendance_manager=None)
    print(f"[*] Loaded {len(engine.known_face_names)} encodings ({len(set(engine.known_face_names))} unique enrolled students).")

    # 2. Start Threaded ESP32-CAM Stream with auto-reconnect
    stream = CameraStream(config.CAMERA_SOURCE)
    stream.start()

    print("\n[+] Connecting to ESP32-CAM stream... Press 'q' in the video window to quit.")

    fps = 0.0
    prev_time = time.time()

    try:
        while True:
            # Check connection status
            status = stream.get_status()
            frame = stream.get_frame()

            if frame is None:
                # Show waiting screen if camera is reconnecting
                waiting_frame = 255 * (time.time() % 1.0 > 0.5)
                # Create a black frame with message
                display = (0, 0, 0)
                time.sleep(0.03)
                continue

            # Process frame through Face Recognition Engine
            annotated_frame = engine.process_frame(frame)

            # Calculate FPS
            curr_time = time.time()
            fps = 0.9 * fps + 0.1 * (1.0 / max(0.001, curr_time - prev_time))
            prev_time = curr_time

            # Overlay FPS and Status on top-left
            status_color = (80, 200, 120) if status["is_connected"] else (70, 70, 240)
            cv2.putText(annotated_frame, f"ESP32-CAM: {'ONLINE' if status['is_connected'] else 'RECONNECTING'}", 
                        (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2, cv2.LINE_AA)
            cv2.putText(annotated_frame, f"FPS: {fps:.1f} | Latency: {status['latency_ms']}ms", 
                        (15, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(annotated_frame, "Press 'Q' to Exit", 
                        (15, annotated_frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)

            # Show window
            cv2.imshow("ESP32-CAM AI Face Recognition Test", annotated_frame)

            # Exit on Q key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q') or key == 27: # 27 is ESC
                print("\n[!] User pressed 'Q' / ESC. Exiting...")
                break

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user (Ctrl+C).")
    finally:
        print("[*] Stopping camera stream and closing windows...")
        stream.stop()
        cv2.destroyAllWindows()
        print("[✓] Clean exit completed.")

if __name__ == "__main__":
    main()
