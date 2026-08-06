import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

import config

# Ensure logs directory exists
os.makedirs(config.LOGS_DIR, exist_ok=True)

# Common Formatter
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

def _create_rotating_handler(filename, max_bytes=5 * 1024 * 1024, backup_count=3):
    filepath = os.path.join(config.LOGS_DIR, filename)
    handler = RotatingFileHandler(filepath, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    handler.setFormatter(formatter)
    return handler

# 1. System Logger (Application lifecycle, health, connections)
system_logger = logging.getLogger("system")
system_logger.setLevel(logging.INFO)
if not system_logger.handlers:
    system_logger.addHandler(_create_rotating_handler("system.log"))
    # Also attach stdout stream handler for console feedback
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    system_logger.addHandler(console_handler)

# 2. Recognition Logger (Face detection, recognition, confidence, unknown, spoof)
recognition_logger = logging.getLogger("recognition")
recognition_logger.setLevel(logging.INFO)
if not recognition_logger.handlers:
    recognition_logger.addHandler(_create_rotating_handler("recognition.log"))

# 3. Attendance Logger (Check-in entries, duplicate prevention)
attendance_logger = logging.getLogger("attendance")
attendance_logger.setLevel(logging.INFO)
if not attendance_logger.handlers:
    attendance_logger.addHandler(_create_rotating_handler("attendance.log"))

# 4. Errors Logger (Exceptions, tracebacks, network timeouts)
errors_logger = logging.getLogger("errors")
errors_logger.setLevel(logging.WARNING)
if not errors_logger.handlers:
    errors_logger.addHandler(_create_rotating_handler("errors.log"))

# ----------------- Convenience Logging API -----------------

def log_system(message: str, level: str = "INFO"):
    """Log system lifecycle, camera state, or configuration change."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    system_logger.log(lvl, message)

def log_recognition(message: str, level: str = "INFO"):
    """Log face detection, confidence score, spoof check, or visitor detection."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    recognition_logger.log(lvl, message)

def log_attendance(message: str, level: str = "INFO"):
    """Log successful check-in or duplicate debouncing."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    attendance_logger.log(lvl, message)

def log_error(message: str, exc: Exception = None):
    """Log error or exception traceback."""
    if exc:
        errors_logger.error(f"{message} - Exception: {str(exc)}", exc_info=True)
        system_logger.error(f"{message} - {str(exc)}")
    else:
        errors_logger.error(message)
        system_logger.error(message)

def get_recent_logs(log_name: str = "system", max_lines: int = 50):
    """Read the last N lines from the requested log file for dashboard/diagnostics."""
    filename = f"{log_name}.log" if not log_name.endswith(".log") else log_name
    filepath = os.path.join(config.LOGS_DIR, filename)
    
    if not os.path.exists(filepath):
        return []
        
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            return [l.strip() for l in lines[-max_lines:]]
    except Exception as e:
        return [f"Failed to read log {filename}: {str(e)}"]

if __name__ == "__main__":
    log_system("Logger initialized successfully.")
    log_recognition("Sample recognition log.")
    log_attendance("Sample attendance log.")
    print("Logs initialized in:", config.LOGS_DIR)
