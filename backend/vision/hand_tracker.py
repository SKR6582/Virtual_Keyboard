import time
import math
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import cv2
import mediapipe as mp


class HandTracker:
    def __init__(self, max_num_hands: int = 1, min_detection_confidence: float = 0.6,
                 min_tracking_confidence: float = 0.5, moving_average_window: int = 3):
        try:
            if hasattr(mp, 'solutions'):
                self.mp_hands = mp.solutions.hands
                self.mp_drawing = mp.solutions.drawing_utils
                self.mp_drawing_styles = mp.solutions.drawing_styles
            else:
                import mediapipe.python.solutions.hands as mp_hands
                import mediapipe.python.solutions.drawing_utils as mp_drawing
                import mediapipe.python.solutions.drawing_styles as mp_drawing_styles
                self.mp_hands = mp_hands
                self.mp_drawing = mp_drawing
                self.mp_drawing_styles = mp_drawing_styles
        except (AttributeError, ImportError) as e:
            raise RuntimeError(
                f"MediaPipe solutions API is not available in the current Python environment (mediapipe version: {getattr(mp, '__version__', 'unknown')}). "
                "Please run using Python 3.10-3.12 with 'mediapipe>=0.10.14,<1.0.0'."
            ) from e

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        self.window_size = moving_average_window
        # History queue for smoothing: deque of (x, y, z)
        self.index_tip_history: deque = deque(maxlen=moving_average_window)
        
        # Temporal velocity tracking
        self.last_z: Optional[float] = None
        self.last_time: Optional[float] = None
        self.z_velocity: float = 0.0

    @staticmethod
    def _compute_angle(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
        """
        Compute interior angle at p2 between p1-p2 and p3-p2 in degrees.
        """
        v1 = p1 - p2
        v2 = p3 - p2
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 < 1e-6 or norm2 < 1e-6:
            return 180.0
        cosine = np.dot(v1, v2) / (norm1 * norm2)
        cosine = np.clip(cosine, -1.0, 1.0)
        return float(np.degrees(np.arccos(cosine)))

    def process_frame(self, frame: np.ndarray) -> Tuple[Optional[Dict[str, Any]], np.ndarray]:
        """
        Processes a BGR image frame, extracts hand landmarks and kinetic metrics.
        Returns (feature_dict, annotated_frame).
        """
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)
        annotated = frame.copy()
        
        if not results.multi_hand_landmarks:
            self.index_tip_history.clear()
            self.last_z = None
            self.last_time = None
            self.z_velocity = 0.0
            return None, annotated

        # Use primary detected hand
        hand_landmarks = results.multi_hand_landmarks[0]
        self.mp_drawing.draw_landmarks(
            annotated,
            hand_landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style()
        )

        current_time = time.time()
        lms = hand_landmarks.landmark

        # Extract primary landmarks
        wrist = np.array([lms[0].x * w, lms[0].y * h, lms[0].z])
        index_mcp = np.array([lms[5].x * w, lms[5].y * h, lms[5].z])
        index_pip = np.array([lms[6].x * w, lms[6].y * h, lms[6].z])
        index_dip = np.array([lms[7].x * w, lms[7].y * h, lms[7].z])
        index_tip_raw = np.array([lms[8].x * w, lms[8].y * h, lms[8].z])
        thumb_tip = np.array([lms[4].x * w, lms[4].y * h, lms[4].z])

        # Moving average filter for index fingertip
        self.index_tip_history.append(index_tip_raw)
        smoothed_tip = np.mean(self.index_tip_history, axis=0)

        # Compute Z-velocity (dz / dt)
        current_z = float(smoothed_tip[2])
        if self.last_z is not None and self.last_time is not None:
            dt = current_time - self.last_time
            if dt > 0.001:
                # Raw dz/dt smoothed
                raw_vz = (current_z - self.last_z) / dt
                self.z_velocity = 0.6 * self.z_velocity + 0.4 * raw_vz
        else:
            self.z_velocity = 0.0

        self.last_z = current_z
        self.last_time = current_time

        # Compute PIP-DIP bending angle
        joint_angle = self._compute_angle(index_mcp, index_pip, index_dip)

        # Draw index fingertip circle
        tip_px = (int(smoothed_tip[0]), int(smoothed_tip[1]))
        cv2.circle(annotated, tip_px, 8, (0, 255, 255), -1)

        result_data = {
            "tip_pixel": (float(smoothed_tip[0]), float(smoothed_tip[1])),
            "tip_z": current_z,
            "z_velocity": float(self.z_velocity),
            "joint_angle": float(joint_angle),
            "wrist": wrist.tolist(),
            "index_mcp": index_mcp.tolist(),
            "thumb_tip": thumb_tip.tolist(),
            "raw_landmarks": [[lm.x, lm.y, lm.z] for lm in lms]
        }
        return result_data, annotated

    def close(self):
        self.hands.close()

