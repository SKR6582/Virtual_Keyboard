import cv2
import threading
import time
import numpy as np
from typing import Dict, List, Optional, Tuple


class CameraWorker(threading.Thread):
    def __init__(self, camera_index: int, width: int = 1920, height: int = 1080, fps: int = 30):
        super().__init__(daemon=True)
        self.camera_index = camera_index
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.latest_frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.is_connected = False
        self.actual_width = 0
        self.actual_height = 0

    def start_camera(self) -> bool:
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            self.is_connected = False
            return False

        # Attempt to configure MJPEG 1080p
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        ret, frame = self.cap.read()
        if ret and frame is not None:
            self.actual_height, self.actual_width = frame.shape[:2]
            with self.lock:
                self.latest_frame = frame
            self.is_connected = True
            self.running = True
            self.start()
            return True
        else:
            self.cap.release()
            self.is_connected = False
            return False

    def run(self):
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self.lock:
                    self.latest_frame = frame
            else:
                time.sleep(0.01)

    def get_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.is_connected = False


class SyntheticCamera(threading.Thread):
    """
    Virtual camera emulator when physical cameras are not connected.
    Generates a mock keyboard surface with 4 corner ArUco markers and a moving pointer.
    """
    def __init__(self, camera_index: int, width: int = 1280, height: int = 720, fps: int = 30):
        super().__init__(daemon=True)
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.running = True
        self.is_connected = True
        self.actual_width = width
        self.actual_height = height
        
        self.latest_frame: Optional[np.ndarray] = None
        self.lock = threading.Lock()
        self.start()

    def run(self):
        t = 0.0
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker_imgs = [cv2.aruco.generateImageMarker(aruco_dict, i, 80) for i in range(4)]
        
        while self.running:
            frame = np.full((self.height, self.width, 3), 40, dtype=np.uint8)
            
            # Draw synthetic keyboard bounding rect
            x1, y1 = 200, 100
            x2, y2 = self.width - 200, self.height - 100
            cv2.rectangle(frame, (x1, y1), (x2, y2), (70, 70, 70), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (180, 180, 180), 2)
            
            # Place ArUco markers on 4 corners
            # ID 0: Top-Left
            frame[y1:y1+80, x1:x1+80] = cv2.cvtColor(marker_imgs[0], cv2.COLOR_GRAY2BGR)
            # ID 1: Top-Right
            frame[y1:y1+80, x2-80:x2] = cv2.cvtColor(marker_imgs[1], cv2.COLOR_GRAY2BGR)
            # ID 2: Bottom-Right
            frame[y2-80:y2, x2-80:x2] = cv2.cvtColor(marker_imgs[2], cv2.COLOR_GRAY2BGR)
            # ID 3: Bottom-Left
            frame[y2-80:y2, x1:x1+80] = cv2.cvtColor(marker_imgs[3], cv2.COLOR_GRAY2BGR)

            # Draw sample keys
            keys = [
                ("UP", (x1 + 350, y1 + 100, 80, 60)),
                ("LEFT", (x1 + 250, y1 + 180, 80, 60)),
                ("DOWN", (x1 + 350, y1 + 180, 80, 60)),
                ("RIGHT", (x1 + 450, y1 + 180, 80, 60)),
                ("SPACE", (x1 + 200, y1 + 260, 380, 60)),
            ]
            for label, (kx, ky, kw, kh) in keys:
                cv2.rectangle(frame, (kx, ky), (kx + kw, ky + kh), (100, 100, 100), -1)
                cv2.rectangle(frame, (kx, ky), (kx + kw, ky + kh), (220, 220, 220), 2)
                cv2.putText(frame, label, (kx + 15, ky + 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            # Draw status text
            cv2.putText(frame, f"CAM {self.camera_index} (Simulated 1080p stream)", (30, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)

            with self.lock:
                self.latest_frame = frame
                
            time.sleep(1.0 / self.fps)
            t += 1.0 / self.fps

    def get_frame(self) -> Optional[np.ndarray]:
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            return None

    def stop(self):
        self.running = False


class CameraManager:
    def __init__(self, target_width: int = 1920, target_height: int = 1080, fps: int = 30):
        self.target_width = target_width
        self.target_height = target_height
        self.target_fps = fps
        self.workers: Dict[int, Any] = {}
        self.use_simulation = False

    def scan_and_initialize(self, max_probe: int = 4) -> int:
        """
        Probe camera indices 0..max_probe-1 and start workers for opened cameras.
        If no physical camera is detected, initiates 1 synthetic camera for testing.
        """
        self.stop_all()
        connected_count = 0
        
        for idx in range(max_probe):
            worker = CameraWorker(idx, self.target_width, self.target_height, self.target_fps)
            if worker.start_camera():
                self.workers[idx] = worker
                connected_count += 1
            else:
                worker.stop()

        if connected_count == 0:
            # Fallback to simulated camera for development and testing
            self.use_simulation = True
            sim_cam = SyntheticCamera(0, self.target_width, self.target_height, self.target_fps)
            self.workers[0] = sim_cam
            connected_count = 1

        return connected_count

    def get_frames(self) -> Dict[int, np.ndarray]:
        """
        Returns a dict of {camera_id: frame} for all active cameras.
        """
        frames = {}
        for cam_id, worker in self.workers.items():
            frame = worker.get_frame()
            if frame is not None:
                frames[cam_id] = frame
        return frames

    def get_primary_frame(self) -> Optional[np.ndarray]:
        """Returns the frame from the lowest camera index (usually camera 0 / top-view)."""
        if not self.workers:
            return None
        min_id = min(self.workers.keys())
        return self.workers[min_id].get_frame()

    def get_active_camera_ids(self) -> List[int]:
        return sorted(list(self.workers.keys()))

    def stop_all(self):
        for worker in self.workers.values():
            worker.stop()
        self.workers.clear()

