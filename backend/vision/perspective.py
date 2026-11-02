import cv2
import numpy as np
from typing import List, Tuple, Optional


class PerspectiveCorrector:
    def __init__(self, plane_width: int = 1000, plane_height: int = 600):
        self.plane_width = plane_width
        self.plane_height = plane_height
        
        # Destination rectangle: [Top-Left, Top-Right, Bottom-Right, Bottom-Left]
        self.dst_pts = np.float32([
            [0, 0],
            [plane_width, 0],
            [plane_width, plane_height],
            [0, plane_height]
        ])
        
        self.matrix: Optional[np.ndarray] = None
        self.inverse_matrix: Optional[np.ndarray] = None
        self.is_calibrated: bool = False
        self.detected_corners: Optional[np.ndarray] = None
        
        # Initialize ArUco detector (DICT_4X4_50)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        try:
            self.detector_params = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.detector_params)
            self._use_new_api = True
        except AttributeError:
            self.detector_params = cv2.aruco.DetectorParameters_create()
            self._use_new_api = False

    def detect_markers(self, frame: np.ndarray) -> Tuple[List[np.ndarray], Optional[np.ndarray]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        if self._use_new_api:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.detector_params)
        return corners, ids

    def calibrate_from_markers(self, frame: np.ndarray, target_ids: List[int] = [0, 1, 2, 3]) -> bool:
        """
        Calibrate perspective transform from 4 corner markers:
        ID 0: Top-Left, ID 1: Top-Right, ID 2: Bottom-Right, ID 3: Bottom-Left
        """
        corners, ids = self.detect_markers(frame)
        if ids is None or len(ids) < 4:
            return False

        id_to_corner = {}
        for i, marker_id in enumerate(ids.flatten()):
            if marker_id in target_ids:
                # Use center of the marker
                marker_corners = corners[i][0]
                center = np.mean(marker_corners, axis=0)
                id_to_corner[int(marker_id)] = center

        if all(marker_id in id_to_corner for marker_id in target_ids):
            src_pts = np.float32([id_to_corner[marker_id] for marker_id in target_ids])
            self.detected_corners = src_pts
            self.matrix = cv2.getPerspectiveTransform(src_pts, self.dst_pts)
            self.inverse_matrix = cv2.getPerspectiveTransform(self.dst_pts, src_pts)
            self.is_calibrated = True
            return True
        return False

    def set_manual_corners(self, corners: List[Tuple[float, float]]):
        """Set 4 corners manually: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]"""
        if len(corners) == 4:
            src_pts = np.float32(corners)
            self.detected_corners = src_pts
            self.matrix = cv2.getPerspectiveTransform(src_pts, self.dst_pts)
            self.inverse_matrix = cv2.getPerspectiveTransform(self.dst_pts, src_pts)
            self.is_calibrated = True

    def warp_image(self, frame: np.ndarray) -> np.ndarray:
        if not self.is_calibrated or self.matrix is None:
            return cv2.resize(frame, (self.plane_width, self.plane_height))
        return cv2.warpPerspective(frame, self.matrix, (self.plane_width, self.plane_height))

    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a 2D coordinate from camera frame to normalized keyboard plane"""
        if not self.is_calibrated or self.matrix is None:
            return float(x), float(y)
        
        pt = np.array([[[x, y]]], dtype=np.float32)
        warped_pt = cv2.perspectiveTransform(pt, self.matrix)
        out_x, out_y = warped_pt[0][0]
        return float(out_x), float(out_y)

    def draw_debug(self, frame: np.ndarray) -> np.ndarray:
        output = frame.copy()
        if self.is_calibrated and self.detected_corners is not None:
            pts = self.detected_corners.astype(int)
            cv2.polylines(output, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            for idx, pt in enumerate(pts):
                cv2.circle(output, tuple(pt), 6, (0, 0, 255), -1)
                cv2.putText(output, str(idx), (pt[0] + 8, pt[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        return output

