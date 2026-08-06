import os
import cv2
import pickle
import time
import numpy as np
import face_recognition
import config
from anti_spoofing import AntiSpoofingTracker
from unknown_manager import UnknownFaceManager
from logger_util import log_recognition, log_error

class FaceEngine:
    """
    AI Face Recognition Engine with Anti-Spoofing Liveness Gating,
    Unknown Face Auto-Logging, frame-skipping, scale optimization,
    best-match matching, and dynamic HUD overlays.
    """
    def __init__(self, attendance_manager=None, unknown_manager=None, anti_spoofing=None):
        self.attendance_manager = attendance_manager
        self.unknown_manager = unknown_manager or UnknownFaceManager()
        self.anti_spoofing = anti_spoofing or AntiSpoofingTracker()
        
        self.known_face_encodings = []
        self.known_face_names = []
        
        # Frame skipping and caching state
        self.frame_count = 0
        self.last_face_locations = []
        self.last_face_names = []
        self.last_face_confidences = []
        self.last_liveness_statuses = []
        self.last_liveness_flags = []
        
        # Performance timing
        self.last_process_latency_ms = 0
        
        # Load known faces from storage or cache
        self.load_known_faces()

    @property
    def known_face_names_unique(self):
        """Return list of distinct registered student names."""
        return list(dict.fromkeys(self.known_face_names))

    def _calculate_blur_score(self, image):
        """Alias for check_blur sharpness score."""
        return self.check_blur(image)

    def load_known_faces(self, force_reload=False):
        """Load known face encodings from pickle cache or scan known_faces/ folder."""
        config.ensure_directories()
        
        if not force_reload and os.path.exists(config.ENCODINGS_FILE):
            try:
                with open(config.ENCODINGS_FILE, "rb") as f:
                    data = pickle.load(f)
                    self.known_face_encodings = data.get("encodings", [])
                    self.known_face_names = data.get("names", [])
                    print(f"[FaceEngine] Loaded {len(self.known_face_names)} encodings from cache ({len(set(self.known_face_names))} unique students).")
                    return
            except Exception as e:
                print(f"[FaceEngine] Failed to load cache: {e}. Rebuilding...")

        print("[FaceEngine] Scanning known_faces directory to build encodings...")
        encodings = []
        names = []

        if os.path.exists(config.KNOWN_FACES_DIR):
            for entry in os.listdir(config.KNOWN_FACES_DIR):
                entry_path = os.path.join(config.KNOWN_FACES_DIR, entry)
                
                # Case 1: Student is a folder with multiple images
                if os.path.isdir(entry_path):
                    student_name = entry
                    for img_file in os.listdir(entry_path):
                        if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                            img_path = os.path.join(entry_path, img_file)
                            enc = self._extract_encoding_from_file(img_path)
                            if enc is not None:
                                encodings.append(enc)
                                names.append(student_name)
                                
                # Case 2: Student is a single image file
                elif os.path.isfile(entry_path) and entry.lower().endswith(('.jpg', '.jpeg', '.png')):
                    student_name, _ = os.path.splitext(entry)
                    enc = self._extract_encoding_from_file(entry_path)
                    if enc is not None:
                        encodings.append(enc)
                        names.append(student_name)

        self.known_face_encodings = encodings
        self.known_face_names = names

        # Save to pickle cache
        try:
            with open(config.ENCODINGS_FILE, "wb") as f:
                pickle.dump({"encodings": encodings, "names": names}, f)
            print(f"[FaceEngine] Successfully cached {len(names)} encodings for {len(set(names))} students.")
        except Exception as e:
            print(f"[FaceEngine] Error saving encodings cache: {e}")

    def _extract_encoding_from_file(self, img_path):
        """Load image file and return first detected face encoding."""
        try:
            image = face_recognition.load_image_file(img_path)
            locations = face_recognition.face_locations(image, model=config.DETECTION_MODEL)
            if locations:
                encs = face_recognition.face_encodings(image, known_face_locations=locations)
                if encs:
                    return encs[0]
        except Exception as e:
            print(f"[FaceEngine] Could not process image {img_path}: {e}")
        return None

    def process_frame(self, frame):
        """
        Process a single video frame:
        - Downscales for fast recognition on every Nth frame
        - Evaluates anti-spoofing liveness (EAR blink + micro-motion + texture)
        - Computes best-match face_distance and confidence %
        - Gated Attendance: only marks attendance if liveness is verified
        - Unknown Logging: auto-captures unknown face visitors
        - Draws sleek modern UI overlays with liveness status badges
        """
        if frame is None:
            return frame

        self.frame_count += 1
        h, w, _ = frame.shape
        scale = config.PROCESS_SCALE

        # Run recognition & anti-spoofing evaluation every FRAME_SKIP frames
        if self.frame_count % config.FRAME_SKIP == 0:
            start_proc = time.time()
            small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Find all face locations and encodings
            small_locations = face_recognition.face_locations(rgb_small_frame, model=config.DETECTION_MODEL)
            small_encodings = face_recognition.face_encodings(rgb_small_frame, small_locations)
            small_landmarks = face_recognition.face_landmarks(rgb_small_frame, small_locations)

            face_locations = []
            face_names = []
            face_confidences = []
            liveness_statuses = []
            liveness_flags = []

            for (s_top, s_right, s_bottom, s_left), face_encoding, lms in zip(
                small_locations, small_encodings, small_landmarks
            ):
                # Scale back coordinates to original frame size
                orig_top = int(s_top / scale)
                orig_right = int(s_right / scale)
                orig_bottom = int(s_bottom / scale)
                orig_left = int(s_left / scale)
                face_locations.append((orig_top, orig_right, orig_bottom, orig_left))

                # Crop face region for anti-spoofing & unknown capturing
                face_crop = frame[max(0, orig_top):min(h, orig_bottom), max(0, orig_left):min(w, orig_right)]

                # 1. Anti-Spoofing Liveness Evaluation
                is_live = True
                status_label = "Live Face Verified"
                live_score = 1.0

                if config.ANTI_SPOOFING_ENABLED and self.anti_spoofing:
                    track_id = f"loc_{int(orig_left/80)}_{int(orig_top/80)}"
                    is_live, live_score, status_label = self.anti_spoofing.evaluate_liveness(
                        track_id=track_id, landmarks=lms, face_crop=face_crop
                    )

                liveness_statuses.append(status_label)
                liveness_flags.append(is_live)

                name = config.UNKNOWN_LABEL
                confidence = 0.0

                if len(self.known_face_encodings) > 0:
                    # Calculate face distances to all known faces
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_idx = np.argmin(face_distances)
                    best_distance = float(face_distances[best_match_idx])

                    if best_distance <= config.RECOGNITION_TOLERANCE:
                        name = self.known_face_names[best_match_idx]
                        confidence = round(max(50.0, min(99.0, (1.0 - (best_distance / (2 * config.RECOGNITION_TOLERANCE))) * 100)), 1)
                        
                        # Only mark attendance if Liveness is verified!
                        if is_live:
                            log_recognition(f"Recognized student '{name}' (Confidence: {confidence}%, Dist: {best_distance:.3f}) - Live Verified")
                            if self.attendance_manager:
                                self.attendance_manager.mark_attendance(
                                    name, frame, (orig_top, orig_right, orig_bottom, orig_left), confidence=confidence
                                )
                        else:
                            log_recognition(f"Recognized student '{name}' pending liveness verification ({status_label})", level="WARNING")
                    else:
                        name = config.UNKNOWN_LABEL
                        confidence = round(max(10.0, min(49.0, (1.0 - best_distance) * 100)), 1)
                        
                        # Auto-log unknown visitor if live
                        if is_live and self.unknown_manager and face_crop.size > 0:
                            log_recognition(f"Unknown visitor detected (Confidence: {confidence}%)", level="INFO")
                            self.unknown_manager.record_unknown(frame, face_crop, confidence_score=confidence)
                        
                        if self.attendance_manager:
                            self.attendance_manager.record_unknown_detection()
                else:
                    if self.unknown_manager and face_crop.size > 0 and is_live:
                        self.unknown_manager.record_unknown(frame, face_crop, confidence_score=0.0)
                    if self.attendance_manager:
                        self.attendance_manager.record_unknown_detection()

                face_names.append(name)
                face_confidences.append(confidence)

            self.last_face_locations = face_locations
            self.last_face_names = face_names
            self.last_face_confidences = face_confidences
            self.last_liveness_statuses = liveness_statuses
            self.last_liveness_flags = liveness_flags
            self.last_process_latency_ms = int((time.time() - start_proc) * 1000)

        # Draw modern HUD overlays using the latest evaluation state
        annotated_frame = self._draw_modern_overlay(
            frame, 
            self.last_face_locations, 
            self.last_face_names, 
            self.last_face_confidences,
            self.last_liveness_statuses,
            self.last_liveness_flags
        )
        return annotated_frame

    def _draw_modern_overlay(self, frame, locations, names, confidences, liveness_statuses, liveness_flags):
        """Render high-tech bounding boxes with liveness indicators."""
        out = frame.copy()

        for (top, right, bottom, left), name, conf, liveness_label, is_live in zip(
            locations, names, confidences, liveness_statuses, liveness_flags
        ):
            is_known = (name != config.UNKNOWN_LABEL)
            
            # Determine color scheme based on identification and anti-spoofing status
            if not is_live and "Spoof" in liveness_label:
                # Spoof detected - Red
                box_color = (40, 40, 240)
                bg_badge_color = (20, 20, 160)
            elif is_known and is_live:
                # Recognized & Live - Emerald Green
                box_color = (80, 210, 120)
                bg_badge_color = (25, 120, 60)
            elif is_known and not is_live:
                # Recognized but checking liveness - Amber/Orange
                box_color = (50, 170, 245)
                bg_badge_color = (30, 100, 180)
            else:
                # Unknown visitor - Cyan/Violet
                box_color = (240, 130, 70)
                bg_badge_color = (160, 70, 30)

            # Draw sleek corner brackets
            corner_len = int(min(right - left, bottom - top) * 0.22)
            thickness = 2
            
            # Main rectangle
            cv2.rectangle(out, (left, top), (right, bottom), box_color, 1)
            
            # Corner accents
            cv2.line(out, (left, top), (left + corner_len, top), box_color, thickness + 2)
            cv2.line(out, (left, top), (left, top + corner_len), box_color, thickness + 2)
            cv2.line(out, (right, top), (right - corner_len, top), box_color, thickness + 2)
            cv2.line(out, (right, top), (right, top + corner_len), box_color, thickness + 2)
            cv2.line(out, (left, bottom), (left + corner_len, bottom), box_color, thickness + 2)
            cv2.line(out, (left, bottom), (left, bottom - corner_len), box_color, thickness + 2)
            cv2.line(out, (right, bottom), (right - corner_len, bottom), box_color, thickness + 2)
            cv2.line(out, (right, bottom), (right, bottom - corner_len), box_color, thickness + 2)

            # Primary Name Badge Text
            label_text = f"{name} ({conf}%)" if is_known else "Unknown Visitor"
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_DUPLEX, 0.52, 1)
            
            badge_top = max(0, top - text_h - 14)
            badge_bottom = top
            badge_left = left
            badge_right = min(out.shape[1], left + max(text_w + 16, 150))

            cv2.rectangle(out, (badge_left, badge_top), (badge_right, badge_bottom), bg_badge_color, -1)
            cv2.rectangle(out, (badge_left, badge_top), (badge_right, badge_bottom), box_color, 1)
            cv2.putText(out, label_text, (badge_left + 8, badge_bottom - 5),
                        cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

            # Secondary Liveness HUD badge below the face box
            live_badge_top = bottom
            live_badge_bottom = min(out.shape[0], bottom + 20)
            live_badge_right = min(out.shape[1], left + 140)

            liveness_bg = (20, 100, 50) if is_live else ((20, 20, 140) if "Spoof" in liveness_label else (30, 80, 140))
            cv2.rectangle(out, (left, live_badge_top), (live_badge_right, live_badge_bottom), liveness_bg, -1)
            cv2.rectangle(out, (left, live_badge_top), (live_badge_right, live_badge_bottom), box_color, 1)
            cv2.putText(out, liveness_label, (left + 6, live_badge_bottom - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

        return out

    def check_blur(self, image):
        """Calculate image sharpness using Laplacian variance."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def capture_registration_sample(self, raw_frame, student_name, sample_idx, previous_frames):
        """
        Validates a single frame for registration:
        - Exactly 1 face present
        - Sharpness > BLUR_THRESHOLD
        - Diversity: not duplicate of previous frame
        Returns (success, message, face_crop, score)
        """
        if raw_frame is None:
            return False, "No camera frame", None, 0.0

        # Check blur
        blur_score = self.check_blur(raw_frame)
        if blur_score < config.BLUR_THRESHOLD:
            return False, f"Image too blurry (Score: {int(blur_score)} < {int(config.BLUR_THRESHOLD)}). Hold still.", None, blur_score

        # Check face detection
        rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb_frame, model="hog")
        
        if len(locations) == 0:
            return False, "No face detected in view. Center your face.", None, blur_score
        elif len(locations) > 1:
            return False, "Multiple faces detected. Ensure only one person is in view.", None, blur_score

        top, right, bottom, left = locations[0]
        h, w, _ = raw_frame.shape
        face_crop = raw_frame[max(0, top):min(h, bottom), max(0, left):min(w, right)]

        # Duplicate / diversity check against previous captured crops
        if previous_frames and face_crop.size > 0:
            small_curr = cv2.resize(face_crop, (64, 64))
            for prev in previous_frames:
                small_prev = cv2.resize(prev, (64, 64))
                diff = np.mean(np.abs(small_curr.astype("float") - small_prev.astype("float")))
                if diff < config.SIMILARITY_MIN_DIFF:
                    return False, "Pose is too similar. Turn head slightly (Left/Right/Up/Down).", None, blur_score

        return True, "Valid sample", face_crop, blur_score
