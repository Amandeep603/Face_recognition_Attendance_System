import os
import time
import psutil
import shutil
from datetime import datetime

import config
from logger_util import log_system

class HealthMonitor:
    """
    Real-time system health, resource telemetry, and performance tracking engine.
    """
    def __init__(self, camera_stream=None, face_engine=None, attendance_manager=None, unknown_manager=None, anti_spoofing=None):
        self.camera_stream = camera_stream
        self.face_engine = face_engine
        self.attendance_manager = attendance_manager
        self.unknown_manager = unknown_manager
        self.anti_spoofing = anti_spoofing
        
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())

    def get_uptime_seconds(self) -> float:
        return time.time() - self.start_time

    def get_uptime_formatted(self) -> str:
        sec = int(self.get_uptime_seconds())
        hours = sec // 3600
        minutes = (sec % 3600) // 60
        seconds = sec % 60
        return f"{hours}h {minutes}m {seconds}s"

    def get_system_resources(self) -> dict:
        """Collect host CPU, RAM, Disk, and Process memory stats."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # RAM
            mem = psutil.virtual_memory()
            ram_total_gb = round(mem.total / (1024 ** 3), 2)
            ram_used_gb = round(mem.used / (1024 ** 3), 2)
            ram_percent = mem.percent
            
            # Process RAM
            proc_mem_mb = round(self.process.memory_info().rss / (1024 * 1024), 2)

            # Disk
            disk = shutil.disk_usage(config.BASE_DIR)
            disk_total_gb = round(disk.total / (1024 ** 3), 2)
            disk_free_gb = round(disk.free / (1024 ** 3), 2)
            disk_used_percent = round((disk.used / disk.total) * 100, 1)

            return {
                "cpu_percent": cpu_percent,
                "ram_total_gb": ram_total_gb,
                "ram_used_gb": ram_used_gb,
                "ram_percent": ram_percent,
                "process_memory_mb": proc_mem_mb,
                "disk_total_gb": disk_total_gb,
                "disk_free_gb": disk_free_gb,
                "disk_used_percent": disk_used_percent
            }
        except Exception as e:
            return {
                "cpu_percent": 0.0,
                "ram_percent": 0.0,
                "process_memory_mb": 0.0,
                "disk_free_gb": 0.0,
                "error": str(e)
            }

    def _get_dir_size_and_count(self, dir_path: str):
        """Recursively calculate directory size in MB and file count."""
        total_size = 0
        file_count = 0
        if not os.path.exists(dir_path):
            return 0.0, 0
            
        for root, _, files in os.walk(dir_path):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass
        return round(total_size / (1024 * 1024), 2), file_count

    def get_storage_breakdown(self) -> dict:
        """Measure storage usage across data folders."""
        known_mb, known_cnt = self._get_dir_size_and_count(config.KNOWN_FACES_DIR)
        att_mb, att_cnt = self._get_dir_size_and_count(config.ATTENDANCE_DIR)
        unk_mb, unk_cnt = self._get_dir_size_and_count(config.UNKNOWN_FACES_DIR)
        rep_mb, rep_cnt = self._get_dir_size_and_count(config.REPORTS_DIR)
        logs_mb, logs_cnt = self._get_dir_size_and_count(config.LOGS_DIR)
        
        total_mb = round(known_mb + att_mb + unk_mb + rep_mb + logs_mb, 2)

        return {
            "total_mb": total_mb,
            "known_faces": {"size_mb": known_mb, "files": known_cnt},
            "attendance": {"size_mb": att_mb, "files": att_cnt},
            "unknown_faces": {"size_mb": unk_mb, "files": unk_cnt},
            "reports": {"size_mb": rep_mb, "files": rep_cnt},
            "logs": {"size_mb": logs_mb, "files": logs_cnt}
        }

    def get_full_health_snapshot(self) -> dict:
        """Returns comprehensive telemetry payload for dashboard & diagnostics."""
        resources = self.get_system_resources()
        storage = self.get_storage_breakdown()
        uptime = self.get_uptime_formatted()
        uptime_sec = int(self.get_uptime_seconds())

        camera_info = self.camera_stream.get_status_info() if self.camera_stream else {"status": "unattached"}
        
        # AI Engine stats
        enrolled_count = 0
        encodings_count = 0
        if self.face_engine:
            enrolled_count = len(self.face_engine.known_face_names_unique)
            encodings_count = len(self.face_engine.known_face_encodings)
        elif self.attendance_manager:
            enrolled_count = len(self.attendance_manager.get_registered_students())

        # Attendance stats
        today_present = 0
        if self.attendance_manager:
            today_records = self.attendance_manager.get_today_records()
            today_present = len(today_records)

        unknown_today = self.unknown_manager.get_unknown_count_today() if self.unknown_manager else 0
        spoofs_blocked = self.anti_spoofing.spoof_attempts_count if self.anti_spoofing else 0

        return {
            "status": "healthy" if camera_info.get("status") in ("online", "connecting") else "degraded",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": uptime,
            "uptime_seconds": uptime_sec,
            "resources": resources,
            "camera": camera_info,
            "ai_engine": {
                "enrolled_students": enrolled_count,
                "total_encodings": encodings_count,
                "frame_skip": config.FRAME_SKIP,
                "tolerance": config.RECOGNITION_TOLERANCE,
                "anti_spoofing_active": config.ANTI_SPOOFING_ENABLED
            },
            "attendance": {
                "present_today": today_present,
                "unknown_faces_today": unknown_today,
                "spoof_attempts_blocked": spoofs_blocked
            },
            "storage": storage
        }

if __name__ == "__main__":
    monitor = HealthMonitor()
    print("Health Snapshot:", monitor.get_full_health_snapshot())
