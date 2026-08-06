import os
import csv
import cv2
import time
import shutil
import threading
from datetime import datetime
import pandas as pd
import config
from logger_util import log_attendance, log_error, log_system

class AttendanceManager:
    """
    Manages daily attendance records in CSV format (Name, Date, Time, Status),
    face thumbnail crops, thread-safe file locking, stats aggregation,
    Excel/CSV exports, and student directory.
    """
    def __init__(self):
        config.ensure_directories()
        self.lock = threading.Lock()
        self.marked_today = set()
        self.unknown_detections_today = 0
        self.last_unknown_time = 0
        self.last_recognition_time = None
        self.last_marked_notification = None
        self._current_date = ""
        self._load_today_state()

    def _get_today_date_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def _get_csv_path(self, date_str=None):
        if not date_str:
            date_str = self._get_today_date_str()
        return os.path.join(config.ATTENDANCE_DIR, f"Attendance_{date_str}.csv")

    def _get_thumbnails_dir(self, date_str=None):
        if not date_str:
            date_str = self._get_today_date_str()
        dir_path = os.path.join(config.THUMBNAILS_DIR, date_str)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def _load_today_state(self):
        """Load already marked students for today into memory."""
        with self.lock:
            today = self._get_today_date_str()
            if today != self._current_date:
                self._current_date = today
                self.marked_today.clear()
                self.unknown_detections_today = 0

            csv_path = self._get_csv_path(today)
            if os.path.exists(csv_path):
                try:
                    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            name = row.get("Name")
                            if name:
                                self.marked_today.add(name)
                except Exception as e:
                    print(f"[AttendanceManager] Error loading today CSV: {e}")

    def mark_attendance(self, name, frame=None, face_location=None, confidence=None):
        """
        Mark attendance for a recognized student (strictly once per student per day).
        Thread-safe write to CSV and auto-saves thumbnail crop.
        """
        if not name or name == config.UNKNOWN_LABEL:
            return {"status": "skipped", "reason": "Invalid or unknown name"}

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        with self.lock:
            self.last_recognition_time = time_str

            # Strict check: only mark once per day
            if name in self.marked_today:
                return {"status": "already_marked", "name": name, "time": time_str, "confidence": confidence}

            csv_path = self._get_csv_path(date_str)
            file_exists = os.path.exists(csv_path)

            # Save face thumbnail if available
            thumbnail_filename = f"{name}.jpg"
            if frame is not None and face_location is not None:
                try:
                    top, right, bottom, left = face_location
                    h, w, _ = frame.shape
                    # Add 15% margin for a clean portrait thumbnail
                    pad_h = int((bottom - top) * 0.15)
                    pad_w = int((right - left) * 0.15)
                    y1 = max(0, top - pad_h)
                    y2 = min(h, bottom + pad_h)
                    x1 = max(0, left - pad_w)
                    x2 = min(w, right + pad_w)

                    face_crop = frame[y1:y2, x1:x2]
                    if face_crop.size > 0:
                        thumb_dir = self._get_thumbnails_dir(date_str)
                        thumb_path = os.path.join(thumb_dir, thumbnail_filename)
                        # Resize thumbnail to standard size 120x120
                        resized_crop = cv2.resize(face_crop, (120, 120))
                        cv2.imwrite(thumb_path, resized_crop)
                except Exception as e:
                    print(f"[AttendanceManager] Error saving thumbnail for {name}: {e}")

            # Append to CSV: Name, Date, Time, Status
            try:
                with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Name", "Date", "Time", "Status"])
                    writer.writerow([name, date_str, time_str, "Present"])
                
                self.marked_today.add(name)
                self.last_marked_notification = {
                    "name": name,
                    "date": date_str,
                    "time": time_str,
                    "status": "Present",
                    "confidence": confidence,
                    "thumbnail": f"/thumbnail/{date_str}/{name}.jpg",
                    "timestamp": time.time()
                }
                log_attendance(f"Marked attendance for '{name}' at {time_str} (Confidence: {confidence}%)")
                print(f"[AttendanceManager] SUCCESS: Marked attendance for '{name}' at {time_str} (Confidence: {confidence}%)")
                return {
                    "status": "success",
                    "name": name,
                    "time": time_str,
                    "date": date_str,
                    "confidence": confidence,
                    "thumbnail": f"/thumbnail/{date_str}/{name}.jpg"
                }
            except Exception as e:
                log_error(f"Failed to write attendance CSV for {name}", e)
                print(f"[AttendanceManager] Failed to write CSV: {e}")
                return {"status": "error", "message": str(e)}

    def record_unknown_detection(self):
        """Track unknown face detection with debouncing."""
        now = time.time()
        if now - self.last_unknown_time > 3.0:  # Debounce: count at most once every 3 seconds
            self.unknown_detections_today += 1
            self.last_unknown_time = now

    def get_records_by_date(self, date_str=None):
        """Return list of attendance records for any specified date (newest first)."""
        if not date_str:
            date_str = self._get_today_date_str()
        
        csv_path = self._get_csv_path(date_str)
        records = []

        if os.path.exists(csv_path):
            with self.lock:
                try:
                    with open(csv_path, mode="r", newline="", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            name = row.get("Name", "")
                            records.append({
                                "name": name,
                                "date": row.get("Date", date_str),
                                "time": row.get("Time", ""),
                                "status": row.get("Status", "Present"),
                                "thumbnail": f"/thumbnail/{date_str}/{name}.jpg"
                            })
                except Exception as e:
                    print(f"[AttendanceManager] Error reading records for {date_str}: {e}")
        
        # Reverse to show newest records at the top
        records.reverse()
        return records

    def get_today_records(self):
        """Return list of today's attendance records."""
        return self.get_records_by_date(self._get_today_date_str())

    def get_registered_students(self):
        """List all registered students in known_faces/ directory."""
        students = []
        if os.path.exists(config.KNOWN_FACES_DIR):
            for entry in sorted(os.listdir(config.KNOWN_FACES_DIR)):
                entry_path = os.path.join(config.KNOWN_FACES_DIR, entry)
                if os.path.isdir(entry_path):
                    images = [f for f in os.listdir(entry_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
                    sample_img = f"/student_photo/{entry}/{images[0]}" if images else None
                    students.append({
                        "name": entry,
                        "image_count": len(images),
                        "sample_image": sample_img,
                        "registered_on": datetime.fromtimestamp(os.path.getctime(entry_path)).strftime("%Y-%m-%d %H:%M")
                    })
                elif os.path.isfile(entry_path) and entry.lower().endswith(('.jpg', '.jpeg', '.png')):
                    name, _ = os.path.splitext(entry)
                    students.append({
                        "name": name,
                        "image_count": 1,
                        "sample_image": f"/student_photo/{entry}",
                        "registered_on": datetime.fromtimestamp(os.path.getctime(entry_path)).strftime("%Y-%m-%d %H:%M")
                    })
        return students

    def get_stats(self):
        """Return system statistics for live dashboard."""
        registered = len(self.get_registered_students())
        today_records = self.get_today_records()
        present = len(self.marked_today)

        return {
            "total_registered": registered,
            "present_today": present,
            "absent_today": max(0, registered - present),
            "unknown_detections": self.unknown_detections_today,
            "last_recognition_time": self.last_recognition_time or "--:--:--",
            "recent_records": today_records[:20],  # Latest 20 records
            "all_records_count": len(today_records),
            "date": self._get_today_date_str()
        }

    def reset_today_attendance(self):
        """Clear today's attendance CSV and reset marked cache."""
        today = self._get_today_date_str()
        csv_path = self._get_csv_path(today)
        with self.lock:
            if os.path.exists(csv_path):
                try:
                    os.remove(csv_path)
                except Exception as e:
                    print(f"[AttendanceManager] Failed to remove CSV: {e}")
            
            thumb_dir = self._get_thumbnails_dir(today)
            if os.path.exists(thumb_dir):
                try:
                    shutil.rmtree(thumb_dir)
                    os.makedirs(thumb_dir, exist_ok=True)
                except Exception as e:
                    print(f"[AttendanceManager] Failed to remove thumbnails: {e}")

            self.marked_today.clear()
            self.unknown_detections_today = 0
            self.last_marked_notification = None
            self.last_recognition_time = None
        return {"status": "success", "message": "Today's attendance has been reset."}

    def delete_student(self, name):
        """Delete student from known_faces/ folder."""
        student_dir = os.path.join(config.KNOWN_FACES_DIR, name)
        single_file = os.path.join(config.KNOWN_FACES_DIR, f"{name}.jpg")
        
        deleted = False
        with self.lock:
            if os.path.exists(student_dir) and os.path.isdir(student_dir):
                shutil.rmtree(student_dir)
                deleted = True
            elif os.path.exists(single_file):
                os.remove(single_file)
                deleted = True

        return {"status": "success" if deleted else "not_found", "name": name}

    def export_excel(self, date_str=None):
        """Generate formatted Excel file (.xlsx) from attendance records with CSV fallback."""
        if not date_str:
            date_str = self._get_today_date_str()
        csv_path = self._get_csv_path(date_str)
        
        if not os.path.exists(csv_path):
            df = pd.DataFrame(columns=["Name", "Date", "Time", "Status"])
        else:
            df = pd.read_csv(csv_path)

        excel_path = os.path.join(config.ATTENDANCE_DIR, f"Attendance_{date_str}.xlsx")
        
        try:
            with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Attendance")
                worksheet = writer.sheets["Attendance"]
                for col in worksheet.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = col[0].column_letter
                    worksheet.column_dimensions[col_letter].width = max(max_len + 4, 14)
            return excel_path
        except Exception as e:
            print(f"[AttendanceManager] Excel export error: {e}. Fallback to CSV.")
            return csv_path
