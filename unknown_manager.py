import os
import cv2
import json
import time
import shutil
import threading
from datetime import datetime
import config

class UnknownFaceManager:
    """
    Manages automatic capture, logging, gallery listing, deletion,
    and student conversion for unrecognized face visitors.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.registry_file = os.path.join(config.UNKNOWN_FACES_DIR, "unknown_registry.json")
        self.last_log_time = 0.0
        self._ensure_registry()

    def _ensure_registry(self):
        """Ensures registry JSON file exists."""
        os.makedirs(config.UNKNOWN_FACES_DIR, exist_ok=True)
        if not os.path.exists(self.registry_file):
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _load_registry(self):
        """Loads metadata registry from JSON."""
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_registry(self, records):
        """Saves metadata registry to JSON."""
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    def record_unknown(self, raw_frame, face_crop, confidence_score=0.0):
        """
        Rate-limited auto-logging of an unknown face detection.
        Saves face crop to unknown_faces/YYYY-MM-DD/unknown_XXX.jpg
        """
        now = time.time()
        # Rate-limiting check
        if (now - self.last_log_time) < config.UNKNOWN_LOG_RATE_LIMIT_SEC:
            return None

        if face_crop is None or face_crop.size == 0:
            return None

        with self.lock:
            self.last_log_time = now
            date_str = datetime.now().strftime("%Y-%m-%d")
            time_str = datetime.now().strftime("%H:%M:%S")
            date_dir = os.path.join(config.UNKNOWN_FACES_DIR, date_str)
            os.makedirs(date_dir, exist_ok=True)

            # Count existing images today
            existing_imgs = [f for f in os.listdir(date_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            next_idx = len(existing_imgs) + 1
            filename = f"unknown_{next_idx:03d}.jpg"
            img_path = os.path.join(date_dir, filename)

            # Save cropped face image
            cv2.imwrite(img_path, face_crop)

            record_id = f"unk_{date_str.replace('-', '')}_{next_idx:03d}"
            record = {
                "id": record_id,
                "date": date_str,
                "time": time_str,
                "filename": filename,
                "relative_url": f"/unknown_photo/{date_str}/{filename}",
                "confidence": round(confidence_score, 1),
                "status": "unresolved",
                "timestamp": now
            }

            registry = self._load_registry()
            registry.insert(0, record) # Most recent first
            self._save_registry(registry)

            print(f"[UnknownFaceManager] Logged unknown visitor: {record_id} at {time_str}")
            return record

    def get_unknown_records(self, date_filter=None):
        """Returns list of unknown visitor records, optionally filtered by date (YYYY-MM-DD)."""
        with self.lock:
            records = self._load_registry()
            if date_filter:
                return [r for r in records if r.get("date") == date_filter]
            return records

    def get_unknown_count_today(self):
        """Returns total unknown visitors detected today."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_records = self.get_unknown_records(date_filter=today_str)
        return len(today_records)

    def delete_record(self, record_id):
        """Deletes an unknown record and its associated image file."""
        with self.lock:
            records = self._load_registry()
            target_record = next((r for r in records if r.get("id") == record_id), None)
            if not target_record:
                return {"success": False, "message": "Record not found."}

            # Remove image file
            date_str = target_record.get("date")
            filename = target_record.get("filename")
            if date_str and filename:
                img_path = os.path.join(config.UNKNOWN_FACES_DIR, date_str, filename)
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception as e:
                        print(f"[UnknownFaceManager] Failed to remove image: {e}")

            updated_records = [r for r in records if r.get("id") != record_id]
            self._save_registry(updated_records)
            return {"success": True, "message": f"Unknown record {record_id} deleted successfully."}

    def convert_to_student(self, record_id, student_name):
        """
        Converts an unknown face capture into a registered student.
        Copies the image to known_faces/student_name/01.jpg and updates record status.
        """
        with self.lock:
            safe_name = "".join(c for c in student_name if c.isalnum() or c in (' ', '_', '-')).strip()
            if not safe_name:
                return {"success": False, "message": "Invalid student name."}

            records = self._load_registry()
            target_record = next((r for r in records if r.get("id") == record_id), None)
            if not target_record:
                return {"success": False, "message": "Record not found."}

            source_img = os.path.join(config.UNKNOWN_FACES_DIR, target_record["date"], target_record["filename"])
            if not os.path.exists(source_img):
                return {"success": False, "message": "Source unknown face image not found on disk."}

            student_dir = os.path.join(config.KNOWN_FACES_DIR, safe_name)
            os.makedirs(student_dir, exist_ok=True)
            dest_img = os.path.join(student_dir, "01.jpg")

            shutil.copy2(source_img, dest_img)

            # Update record status in registry
            target_record["status"] = f"converted_to_{safe_name}"
            self._save_registry(records)

            return {
                "success": True,
                "message": f"Converted record {record_id} into student '{safe_name}'.",
                "student_name": safe_name
            }
