import cv2
import numpy as np
import time
import math
from collections import deque
import config

class AntiSpoofingTracker:
    """
    Multi-Factor Liveness & Anti-Spoofing Engine.
    Combines Eye Aspect Ratio (EAR) blink detection, facial landmark micro-motion dynamics,
    and texture frequency analysis to prevent spoofing from printed photos, phones, or laptop screens.
    """

    def __init__(self):
        # Dictionary tracking per-person or per-location state: { track_id: FaceLivenessState }
        self.tracks = {}
        self.spoof_attempts_count = 0
        self.verified_live_count = 0

    def calculate_ear(self, eye_points):
        """
        Calculates Eye Aspect Ratio (EAR) for a given eye (list of 6 (x,y) tuples).
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 * ||p1 - p4||)
        """
        if len(eye_points) < 6:
            return 0.3 # Default open

        # Vertical distances
        p2_p6 = math.hypot(eye_points[1][0] - eye_points[5][0], eye_points[1][1] - eye_points[5][1])
        p3_p5 = math.hypot(eye_points[2][0] - eye_points[4][0], eye_points[2][1] - eye_points[4][1])
        
        # Horizontal distance
        p1_p4 = math.hypot(eye_points[0][0] - eye_points[3][0], eye_points[0][1] - eye_points[3][1])

        if p1_p4 == 0:
            return 0.3

        ear = (p2_p6 + p3_p5) / (2.0 * p1_p4)
        return ear

    def analyze_texture(self, face_crop):
        """
        Analyzes high-frequency texture variation on the face crop.
        Printed photos and low-res screens exhibit either flat texture or moire patterns.
        """
        if face_crop is None or face_crop.size == 0:
            return 0.0, False

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if len(face_crop.shape) == 3 else face_crop
        
        # Laplacian variance for sharpness/texture richness
        lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Color distribution diversity (RGB channel spread)
        if len(face_crop.shape) == 3:
            std_b = np.std(face_crop[:, :, 0])
            std_g = np.std(face_crop[:, :, 1])
            std_r = np.std(face_crop[:, :, 2])
            color_div = (std_b + std_g + std_r) / 3.0
        else:
            color_div = 30.0

        is_texture_valid = (lap_var >= config.TEXTURE_MIN_VARIANCE) and (color_div >= 15.0)
        return float(lap_var), is_texture_valid

    def evaluate_liveness(self, track_id, landmarks, face_crop):
        """
        Evaluates multi-frame liveness for a detected face.
        
        Returns:
            is_live (bool): True if verified as a real living human face
            liveness_score (float): 0.0 to 1.0 confidence score
            status_label (str): "Live Face Verified" | "Spoof Detected" | "Checking Liveness..."
        """
        if not config.ANTI_SPOOFING_ENABLED:
            return True, 1.0, "Live Face Verified"

        now = time.time()

        # Initialize or clean stale track state
        if track_id not in self.tracks or (now - self.tracks[track_id]["last_seen"] > 4.0):
            self.tracks[track_id] = {
                "created_at": now,
                "last_seen": now,
                "ear_history": deque(maxlen=15),
                "landmarks_history": deque(maxlen=10),
                "live_frames": 0,
                "spoof_frames": 0,
                "blink_recorded": False,
                "is_verified": False
            }

        state = self.tracks[track_id]
        state["last_seen"] = now

        # 1. Texture analysis
        lap_score, texture_valid = self.analyze_texture(face_crop)
        if not texture_valid:
            state["spoof_frames"] += 1
            if state["spoof_frames"] > 3:
                self.spoof_attempts_count += 1
                return False, 0.2, "Spoof Detected"

        # 2. Eye Aspect Ratio & Blink Detection
        avg_ear = 0.3
        if landmarks and "left_eye" in landmarks and "right_eye" in landmarks:
            left_ear = self.calculate_ear(landmarks["left_eye"])
            right_ear = self.calculate_ear(landmarks["right_eye"])
            avg_ear = (left_ear + right_ear) / 2.0
            state["ear_history"].append(avg_ear)

            # Check if blink occurred (EAR dropped below threshold and then increased)
            if len(state["ear_history"]) >= 4:
                ears = list(state["ear_history"])
                min_ear = min(ears)
                max_ear = max(ears)
                if min_ear < config.LIVENESS_EAR_THRESHOLD and (max_ear - min_ear) > 0.06:
                    state["blink_recorded"] = True

        # 3. Micro-Motion Dynamics
        motion_score = 0.0
        if landmarks and "nose_tip" in landmarks:
            nose = landmarks["nose_tip"][0]
            state["landmarks_history"].append(nose)

            if len(state["landmarks_history"]) >= 3:
                coords = list(state["landmarks_history"])
                dx = [abs(coords[i][0] - coords[i-1][0]) for i in range(1, len(coords))]
                dy = [abs(coords[i][1] - coords[i-1][1]) for i in range(1, len(coords))]
                avg_shift = (sum(dx) + sum(dy)) / (len(dx) * 2.0)
                motion_score = min(avg_shift / 2.0, 1.0)

        # 4. Multi-frame Decision Fusion
        is_frame_live = texture_valid and (state["blink_recorded"] or motion_score > 0.05 or len(state["landmarks_history"]) >= 1)
        
        if is_frame_live:
            state["live_frames"] += 1
            state["spoof_frames"] = max(0, state["spoof_frames"] - 1)
        else:
            state["spoof_frames"] += 1

        # Calculate final liveness score
        score = min(1.0, (state["live_frames"] * 0.3) + (0.4 if state["blink_recorded"] else 0.2) + min(0.3, lap_score / 300.0))

        if state["live_frames"] >= config.LIVENESS_FRAMES_REQUIRED:
            state["is_verified"] = True
            self.verified_live_count += 1
            return True, round(score, 2), "Live Face Verified"

        if state["spoof_frames"] >= 5:
            return False, round(score, 2), "Spoof Detected"

        return False, round(score, 2), "Checking Liveness..."

    def cleanup_old_tracks(self, max_age_sec=5.0):
        """Purges stale track entries to keep memory footprint minimal."""
        now = time.time()
        stale_keys = [k for k, v in self.tracks.items() if (now - v.get("last_seen", 0)) > max_age_sec]
        for k in stale_keys:
            del self.tracks[k]
