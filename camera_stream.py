import cv2
import time
import threading
import numpy as np
import urllib.request
import config

class CameraStream:
    """
    Multithreaded Camera Stream reader supporting two modes:
    
    1. CAPTURE MODE (config.CAPTURE_MODE = True):
       Polls ESP32-CAM /capture endpoint repeatedly for JPEG snapshots.
       Best for firmware that doesn't expose port 81 MJPEG stream.
       
    2. STREAM MODE (config.CAPTURE_MODE = False):
       Opens a persistent cv2.VideoCapture on an MJPEG /stream URL.
       Best for standard AI-Thinker CameraWebServer firmware.
    
    Features: auto-reconnection, FPS calculation, latency tracking, placeholder frames.
    """
    def __init__(self, source=config.CAMERA_SOURCE):
        self.source = source
        self.cap = None
        self.current_frame = None
        self.last_frame_time = 0
        self.fps = 0.0
        self.latency_ms = 0
        self.status = "connecting"  # "online", "connecting", "offline", "reconnecting"
        self.error_message = ""
        
        self.is_running = False
        self.lock = threading.Lock()
        self.thread = None
        
        # Frame counters for smoothed FPS
        self._fps_count = 0
        self._fps_start_time = time.time()

    def start(self):
        """Start the background stream capture thread."""
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print(f"[CameraStream] Started stream thread for source: {self.source}")

    def stop(self):
        """Stop stream capture and release video capture resources."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self._release_cap()
        print("[CameraStream] Stopped stream thread.")

    def set_source(self, new_source):
        """Dynamically switch camera source (e.g. ESP32 URL or webcam index)."""
        with self.lock:
            if self.source == new_source:
                return
            print(f"[CameraStream] Switching source from {self.source} to {new_source}")
            self.source = new_source
            self._release_cap()
            self.status = "connecting"
            self.error_message = ""

    def _release_cap(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    # =========================================================================
    #  CAPTURE MODE: Poll /capture endpoint for individual JPEG snapshots
    # =========================================================================
    def _capture_snapshot(self):
        """Fetch a single JPEG frame from the ESP32-CAM /capture endpoint via HTTP."""
        try:
            start_read = time.time()
            req = urllib.request.Request(self.source)
            req.add_header('User-Agent', 'ESP32-CAM-Client/1.0')
            with urllib.request.urlopen(req, timeout=config.STREAM_READ_TIMEOUT) as resp:
                img_bytes = resp.read()
            
            read_latency = (time.time() - start_read) * 1000
            
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if frame is not None and frame.size > 0:
                return frame, int(read_latency)
            return None, 0
        except Exception as e:
            self.error_message = str(e)
            return None, 0

    def _capture_loop_snapshot(self):
        """Capture loop for CAPTURE MODE: repeatedly polls /capture."""
        consecutive_failures = 0
        
        while self.is_running:
            frame, latency = self._capture_snapshot()
            
            if frame is not None:
                consecutive_failures = 0
                now = time.time()
                
                with self.lock:
                    self.current_frame = frame
                    self.last_frame_time = now
                    self.status = "online"
                    self.latency_ms = latency
                    self.error_message = ""
                
                # Update FPS calculation
                self._fps_count += 1
                elapsed = now - self._fps_start_time
                if elapsed >= 1.0:
                    self.fps = round(self._fps_count / elapsed, 1)
                    self._fps_count = 0
                    self._fps_start_time = now
                
                # Target ~10-15 FPS for capture mode (each request takes ~100-200ms)
                time.sleep(0.01)
            else:
                consecutive_failures += 1
                if consecutive_failures > 3:
                    with self.lock:
                        self.status = "reconnecting"
                        self.fps = 0.0
                    print(f"[CameraStream] Capture endpoint unreachable. Retrying in {config.CAMERA_RECONNECT_INTERVAL}s...")
                    time.sleep(config.CAMERA_RECONNECT_INTERVAL)
                else:
                    time.sleep(0.3)

    # =========================================================================
    #  STREAM MODE: Standard MJPEG cv2.VideoCapture
    # =========================================================================
    def _connect(self):
        """Attempt connection to MJPEG camera stream."""
        self._release_cap()
        try:
            src = int(self.source) if isinstance(self.source, str) and self.source.isdigit() else self.source
            self.cap = cv2.VideoCapture(src)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            if self.cap.isOpened():
                self.status = "online"
                self.error_message = ""
                print(f"[CameraStream] Connected successfully to: {self.source}")
                return True
            else:
                self.status = "offline"
                self.error_message = f"Failed to open video source: {self.source}"
                return False
        except Exception as e:
            self.status = "offline"
            self.error_message = str(e)
            return False

    def _capture_loop_stream(self):
        """Capture loop for STREAM MODE: reads from cv2.VideoCapture."""
        consecutive_failures = 0
        
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                self.status = "connecting"
                success = self._connect()
                if not success:
                    time.sleep(config.CAMERA_RECONNECT_INTERVAL)
                    continue

            start_read = time.time()
            ret, frame = self.cap.read()
            read_latency = (time.time() - start_read) * 1000

            if ret and frame is not None:
                consecutive_failures = 0
                now = time.time()
                
                with self.lock:
                    self.current_frame = frame
                    self.last_frame_time = now
                    self.status = "online"
                    self.latency_ms = int(read_latency)
                
                # Update FPS calculation
                self._fps_count += 1
                elapsed = now - self._fps_start_time
                if elapsed >= 1.0:
                    self.fps = round(self._fps_count / elapsed, 1)
                    self._fps_count = 0
                    self._fps_start_time = now

                time.sleep(0.005)
            else:
                consecutive_failures += 1
                if consecutive_failures > 5:
                    with self.lock:
                        self.status = "reconnecting"
                        self.fps = 0.0
                    print(f"[CameraStream] Stream connection lost. Retrying in {config.CAMERA_RECONNECT_INTERVAL}s...")
                    self._release_cap()
                    time.sleep(config.CAMERA_RECONNECT_INTERVAL)    
                else:
                    time.sleep(0.1)

    # =========================================================================
    #  UNIFIED ENTRY POINT
    # =========================================================================
    def _capture_loop(self):
        """Route to the correct capture loop based on config.CAPTURE_MODE."""
        use_capture = getattr(config, 'CAPTURE_MODE', False)
        mode_name = "CAPTURE (snapshot polling)" if use_capture else "STREAM (MJPEG)"
        print(f"[CameraStream] Mode: {mode_name} | Source: {self.source}")
        
        if use_capture:
            self._capture_loop_snapshot()
        else:
            self._capture_loop_stream()

    def get_frame(self):
        """Return the latest frame or a placeholder if offline."""
        with self.lock:
            if self.current_frame is not None and self.status == "online":
                return self.current_frame.copy()
            else:
                return self._generate_placeholder_frame()

    def get_raw_frame_nowait(self):
        """Return raw frame without copying, or None if offline."""
        with self.lock:
            if self.current_frame is not None and self.status == "online":
                return self.current_frame
            return None

    def get_status_info(self):
        """Return dictionary with camera diagnostics."""
        with self.lock:
            return {
                "status": self.status,
                "fps": self.fps,
                "latency_ms": self.latency_ms,
                "source": str(self.source),
                "mode": "capture" if getattr(config, 'CAPTURE_MODE', False) else "stream",
                "last_seen": int(time.time() - self.last_frame_time) if self.last_frame_time > 0 else -1,
                "error": self.error_message
            }

    def _generate_placeholder_frame(self, width=640, height=480):
        """Generate a sleek dark-themed placeholder frame when camera is offline."""
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Gradient background
        for y in range(height):
            c = int(15 + (y / height) * 20)
            frame[y, :] = (c + 15, c, c)
            
        # Draw status text
        if self.status == "connecting" or self.status == "reconnecting":
            title = "Connecting to ESP32-CAM..."
            subtitle = f"Target: {self.source}"
            color = (0, 200, 255) # Yellow/Amber
        else:
            title = "Camera Offline"
            subtitle = "Check Wi-Fi / IP connection"
            color = (80, 80, 240) # Red/Coral

        # Overlay text
        cv2.putText(frame, title, (int(width * 0.15), int(height * 0.45)),
                    cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2, cv2.LINE_AA)
        cv2.putText(frame, subtitle, (int(width * 0.15), int(height * 0.55)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Status: {self.status.upper()}", (int(width * 0.15), int(height * 0.65)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)
        
        return frame
