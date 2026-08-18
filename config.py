import os

# ==============================================================================
#  AI Face Recognition Attendance System - Enterprise Configuration
# ==============================================================================

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")
KNOWN_FACES_FOLDER = KNOWN_FACES_DIR

ATTENDANCE_DIR = os.path.join(BASE_DIR, "attendance")
ATTENDANCE_FOLDER = ATTENDANCE_DIR

THUMBNAILS_DIR = os.path.join(ATTENDANCE_DIR, "thumbnails")

UNKNOWN_FACES_DIR = os.path.join(BASE_DIR, "unknown_faces")
UNKNOWN_FACES_FOLDER = UNKNOWN_FACES_DIR

REPORTS_DIR = os.path.join(BASE_DIR, "reports")
REPORTS_FOLDER = REPORTS_DIR

LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOGS_FOLDER = LOGS_DIR

ENCODINGS_FILE = os.path.join(BASE_DIR, "encodings.pkl")

# Camera Stream Configuration (ESP32-CAM & Local Fallback)
CAMERA_URL = "http://192.168.18.142/capture"
ESP32_STREAM_URL = CAMERA_URL
CAMERA_SOURCE = CAMERA_URL           # Default camera source (ESP32 URL or 0 for local webcam)
CAPTURE_MODE = True                  # True = poll /capture snapshots, False = MJPEG /stream
AUTO_RECONNECT = True                # Enable automated stream recovery on Wi-Fi dropouts
CAMERA_RECONNECT_INTERVAL = 1.5     # Seconds between reconnect attempts (faster for capture mode)
CAMERA_FPS_TARGET = 15               # Target streaming framerate
FRAME_WIDTH = 640                    # Streaming width
FRAME_HEIGHT = 480                   # Streaming height
JPEG_QUALITY = 80                    # MJPEG compression quality (1-100)
STREAM_READ_TIMEOUT = 5.0            # Seconds before triggering stream timeout recovery

# Face Recognition Configuration
RECOGNITION_TOLERANCE = 0.45        # Lower = stricter match, Higher = looser match
FRAME_SKIP = 3                      # Process recognition on every Nth frame
PROCESS_SCALE = 0.5                 # Downscaling factor for recognition processing (320x240)
DETECTION_MODEL = "hog"             # "hog" (Fast CPU) or "cnn" (GPU CUDA)
UNKNOWN_LABEL = "Unknown"

# Anti-Spoofing (Liveness Detection) Configuration
ANTI_SPOOFING_ENABLED = True
LIVENESS_EAR_THRESHOLD = 0.21       # Eye Aspect Ratio threshold for blink detection
LIVENESS_FRAMES_REQUIRED = 2        # Consecutive live frames required to verify liveness
TEXTURE_MIN_VARIANCE = 50.0         # Texture variance threshold (reject flat screens/photos)
MOTION_MIN_SHIFT = 0.6              # Minimum facial landmark shift for micro-motion check

# Unknown Face Management
UNKNOWN_LOG_RATE_LIMIT_SEC = 5.0    # Seconds between logging the same unknown face
UNKNOWN_CONFIDENCE_THRESHOLD = 0.45

# Student Registration Wizard Configuration
REGISTRATION_BURST_COUNT = 20       # Number of high-res frames to capture per student
REGISTRATION_MIN_VALID = 15         # Minimum required valid frames to finalize
BLUR_THRESHOLD = 60.0               # Minimum Laplacian variance for blur filtering
SIMILARITY_MIN_DIFF = 12.0          # Minimum pixel variation to avoid duplicate frames

# Attendance Settings
ATTENDANCE_DEBOUNCE_SEC = 10        # Cooldown before re-notifying UI for the same student on same day

# Logging Configuration
LOG_LEVEL = "INFO"                  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# Admin Security & Session Management
SECRET_KEY = "medein-labs-enterprise-face-attendance-secret-key"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Flask Server Settings
HOST = "0.0.0.0"
PORT = 5000
DEBUG = False

def ensure_directories():
    """Ensure all required project storage and logging folders exist."""
    for folder in [KNOWN_FACES_DIR, ATTENDANCE_DIR, THUMBNAILS_DIR, UNKNOWN_FACES_DIR, REPORTS_DIR, LOGS_DIR]:
        os.makedirs(folder, exist_ok=True)

if __name__ == "__main__":
    ensure_directories()
    print("All enterprise directories initialized successfully.")
