import numpy as np
from typing import Dict, List, Optional, Any


class MultiViewFeatureExtractor:
    """
    Constructs a standardized multimodal feature vector from 1 to 4 camera viewpoints.
    Standardized 16-dimensional vector:
      [0]:  Warped X (normalized 0.0 to 1.0)
      [1]:  Warped Y (normalized 0.0 to 1.0)
      [2]:  Normalized Z depth
      [3]:  Z velocity (dz / dt)
      [4]:  Joint bend angle (0.0 to 1.0, mapped from 0 to 180 deg)
      [5]:  Cam 1 detected flag (1.0 or 0.0)
      [6]:  Cam 1 tip X
      [7]:  Cam 1 tip Y
      [8]:  Cam 2 detected flag (1.0 or 0.0)
      [9]:  Cam 2 tip X
      [10]: Cam 2 tip Y
      [11]: Cam 3 detected flag (1.0 or 0.0)
      [12]: Cam 3 tip X
      [13]: Cam 3 tip Y
      [14]: Fingertip to wrist delta X (normalized)
      [15]: Fingertip to wrist delta Y (normalized)
    """
    VECTOR_DIM = 16

    def __init__(self, plane_width: int = 1000, plane_height: int = 600):
        self.plane_width = plane_width
        self.plane_height = plane_height

    def extract_vector(
        self,
        primary_tracking: Optional[Dict[str, Any]],
        warped_coords: Optional[tuple],
        secondary_trackings: Optional[Dict[int, Optional[Dict[str, Any]]]] = None
    ) -> np.ndarray:
        vec = np.zeros(self.VECTOR_DIM, dtype=np.float32)

        if primary_tracking is None:
            return vec

        # Primary camera features
        if warped_coords is not None:
            wx, wy = warped_coords
            vec[0] = float(np.clip(wx / max(1.0, self.plane_width), 0.0, 1.0))
            vec[1] = float(np.clip(wy / max(1.0, self.plane_height), 0.0, 1.0))
        else:
            tip_x, tip_y = primary_tracking["tip_pixel"]
            vec[0] = float(np.clip(tip_x / 1920.0, 0.0, 1.0))
            vec[1] = float(np.clip(tip_y / 1080.0, 0.0, 1.0))

        vec[2] = float(primary_tracking.get("tip_z", 0.0))
        vec[3] = float(primary_tracking.get("z_velocity", 0.0))
        angle = primary_tracking.get("joint_angle", 180.0)
        vec[4] = float(np.clip(angle / 180.0, 0.0, 1.0))

        # Secondary cameras (indices 1, 2, 3)
        if secondary_trackings:
            cam_slots = [(1, 5), (2, 8), (3, 11)]
            for cam_id, start_idx in cam_slots:
                sec_track = secondary_trackings.get(cam_id)
                if sec_track is not None:
                    vec[start_idx] = 1.0
                    tip = sec_track.get("tip_pixel", (0.0, 0.0))
                    vec[start_idx + 1] = float(np.clip(tip[0] / 1920.0, 0.0, 1.0))
                    vec[start_idx + 2] = float(np.clip(tip[1] / 1080.0, 0.0, 1.0))

        # Wrist relative direction
        wrist = primary_tracking.get("wrist")
        tip_px = primary_tracking.get("tip_pixel")
        if wrist is not None and tip_px is not None:
            dx = (tip_px[0] - wrist[0]) / 500.0
            dy = (tip_px[1] - wrist[1]) / 500.0
            vec[14] = float(np.clip(dx, -1.0, 1.0))
            vec[15] = float(np.clip(dy, -1.0, 1.0))

        return vec

