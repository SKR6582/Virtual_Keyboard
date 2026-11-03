import asyncio
import base64
import json
import os
import sys
import time
from typing import Dict, Any, Set
import cv2
import websockets

from backend.config import (
    WS_HOST, WS_PORT, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS,
    MAX_PROBE_CAMERAS, KEYMAP_PATH, MODEL_PATH, DATASET_PATH,
    SOUND_PATH, PREVIEW_JPEG_QUALITY, DEBOUNCE_SECONDS
)
from backend.camera.manager import CameraManager
from backend.vision.perspective import PerspectiveCorrector
from backend.vision.hand_tracker import HandTracker
from backend.vision.feature_extractor import MultiViewFeatureExtractor
from backend.engine.key_mapper import KeyMapper
from backend.engine.fsm import KeyStrikeFSM
from backend.engine.sound_player import SoundPlayer
from backend.input.key_injector import KeyInjector
from backend.ml.dataset import DatasetManager
from backend.ml.model import VirtualKeyboardMLModel
from backend.ml.trainer import ModelTrainer


class VirtualKeyboardBackend:
    def __init__(self):
        self.camera_mgr = CameraManager(CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS)
        self.key_mapper = KeyMapper(KEYMAP_PATH)
        self.plane_size = self.key_mapper.plane_size
        
        self.perspective = PerspectiveCorrector(self.plane_size[0], self.plane_size[1])
        self.hand_tracker = HandTracker()
        self.feature_extractor = MultiViewFeatureExtractor(self.plane_size[0], self.plane_size[1])
        
        self.fsm = KeyStrikeFSM()
        self.sound_player = SoundPlayer(SOUND_PATH)
        self.key_injector = KeyInjector(debounce_seconds=DEBOUNCE_SECONDS)
        
        self.dataset_mgr = DatasetManager(DATASET_PATH)
        self.ml_model = VirtualKeyboardMLModel(MODEL_PATH, self.plane_size[0], self.plane_size[1])
        self.trainer = ModelTrainer(self.dataset_mgr, self.ml_model)
        
        self.connected_clients: Set[Any] = set()
        self.is_collecting = False
        self.collect_target_key = "UP"
        self.running = True

    def initialize(self):
        connected_cam_count = self.camera_mgr.scan_and_initialize(MAX_PROBE_CAMERAS)
        print(f"Cameras initialized: {connected_cam_count} active camera(s). Primary camera: {self.camera_mgr.primary_camera_index}")
        # Attempt auto-calibration from first available frame
        primary_frame = self.camera_mgr.get_primary_frame()
        if primary_frame is not None:
            calibrated = self.perspective.calibrate_from_markers(primary_frame)
            if calibrated:
                print("ArUco 4-corner perspective transform calibrated.")

    def process_cycle(self) -> Dict[str, Any]:
        frames = self.camera_mgr.get_frames()
        if not frames:
            return {}

        primary_frame = self.camera_mgr.get_primary_frame()
        if primary_frame is None:
            return {}

        active_ids = self.camera_mgr.get_active_camera_ids()

        # Auto-calibrate if not calibrated yet
        if not self.perspective.is_calibrated:
            self.perspective.calibrate_from_markers(primary_frame)

        # Hand tracking on primary camera
        track_info, annotated_primary = self.hand_tracker.process_frame(primary_frame)
        annotated_primary = self.perspective.draw_debug(annotated_primary)

        # Track secondary cameras if present
        secondary_tracks = {}
        for cam_id in active_ids:
            if cam_id != self.camera_mgr.primary_camera_index and cam_id in frames:
                s_track, _ = self.hand_tracker.process_frame(frames[cam_id])
                secondary_tracks[cam_id] = s_track

        warped_coords = None
        current_key = None
        strike_occurred = False
        ml_prediction = {}

        if track_info is not None:
            tip_x, tip_y = track_info["tip_pixel"]
            warped_x, warped_y = self.perspective.transform_point(tip_x, tip_y)
            warped_coords = (warped_x, warped_y)

            # Build 16-D feature vector
            feat_vec = self.feature_extractor.extract_vector(track_info, warped_coords, secondary_tracks)

            # ML prediction
            ml_prediction = self.ml_model.predict(feat_vec)

            # Physics-based FSM evaluation
            fsm_strike, fsm_state = self.fsm.update(track_info["z_velocity"], track_info["joint_angle"])

            # Map point to defined key
            detected_key_def = self.key_mapper.find_key_at_point(warped_x, warped_y)
            if detected_key_def:
                current_key = detected_key_def["label"]

            # Strike determination: FSM trigger OR (ML contact & confidence > 0.8)
            should_strike = fsm_strike or (ml_prediction.get("is_contact") and ml_prediction.get("confidence", 0.0) > 0.82)

            if should_strike and detected_key_def:
                key_code = detected_key_def.get("key_code", detected_key_def["label"])
                injected = self.key_injector.press_and_release(key_code)
                if injected:
                    self.sound_player.play_click()
                    strike_occurred = True
                    # Visual feedback on camera frame
                    cv2.circle(annotated_primary, (int(tip_x), int(tip_y)), 24, (0, 255, 0), -1)
                    cv2.putText(annotated_primary, f"HIT: {current_key}", (int(tip_x) + 15, int(tip_y) - 15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 3)

            # If currently in data collection mode, save sample
            if self.is_collecting and (fsm_strike or ml_prediction.get("is_contact")):
                self.dataset_mgr.add_sample(
                    key_label=self.collect_target_key,
                    target_xy=[warped_x, warped_y],
                    feature_vector=feat_vec.tolist(),
                    is_pressed=1
                )

        # Encode primary frame for UI preview (resized to conserve bandwidth)
        h, w = annotated_primary.shape[:2]
        preview_h = 360
        preview_w = int(w * (preview_h / h))
        small_frame = cv2.resize(annotated_primary, (preview_w, preview_h))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), PREVIEW_JPEG_QUALITY]
        _, buffer = cv2.imencode('.jpg', small_frame, encode_param)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')

        return {
            "type": "tick",
            "timestamp": time.time(),
            "active_cameras": len(active_ids),
            "primary_camera": self.camera_mgr.primary_camera_index,
            "is_simulation": self.camera_mgr.use_simulation,
            "calibrated": self.perspective.is_calibrated,
            "preview_frame": jpg_as_text,
            "fingertip_coords": {"x": warped_coords[0], "y": warped_coords[1]} if warped_coords else None,
            "current_key": current_key,
            "strike": strike_occurred,
            "strike_key": current_key if strike_occurred else None,
            "ml_info": ml_prediction,
            "os_input_enabled": self.key_injector.enabled,
            "dataset_stats": self.dataset_mgr.get_stats(),
            "keys": self.key_mapper.get_keys()
        }

    async def client_handler(self, websocket):
        self.connected_clients.add(websocket)
        try:
            available_cams = self.camera_mgr.probe_available_cameras(6)
            # Send initial configuration
            init_msg = json.dumps({
                "type": "init",
                "keys": self.key_mapper.get_keys(),
                "plane_size": self.key_mapper.plane_size,
                "dataset_stats": self.dataset_mgr.get_stats(),
                "os_input_enabled": self.key_injector.enabled,
                "available_cameras": available_cams,
                "primary_camera": self.camera_mgr.primary_camera_index,
                "is_simulation": self.camera_mgr.use_simulation
            })
            await websocket.send(init_msg)

            async for message in websocket:
                data = json.loads(message)
                action = data.get("action")

                if action == "switch_camera":
                    cam_idx = int(data.get("camera_index", 0))
                    success = self.camera_mgr.switch_primary_camera(cam_idx)
                    # Reset calibration on camera switch
                    self.perspective.is_calibrated = False
                    primary_frame = self.camera_mgr.get_primary_frame()
                    if primary_frame is not None:
                        self.perspective.calibrate_from_markers(primary_frame)
                    await websocket.send(json.dumps({
                        "type": "camera_switched",
                        "success": success,
                        "primary_camera": self.camera_mgr.primary_camera_index,
                        "is_simulation": self.camera_mgr.use_simulation
                    }))

                elif action == "refresh_cameras":
                    available_cams = self.camera_mgr.probe_available_cameras(6)
                    await websocket.send(json.dumps({
                        "type": "available_cameras",
                        "available_cameras": available_cams,
                        "primary_camera": self.camera_mgr.primary_camera_index
                    }))

                elif action == "start_collection":
                    self.is_collecting = True
                    self.collect_target_key = data.get("key_label", "UP")
                    await websocket.send(json.dumps({"type": "collection_status", "collecting": True, "target": self.collect_target_key}))

                elif action == "stop_collection":
                    self.is_collecting = False
                    await websocket.send(json.dumps({"type": "collection_status", "collecting": False}))

                elif action == "clear_dataset":
                    self.dataset_mgr.clear()
                    await websocket.send(json.dumps({"type": "dataset_cleared", "stats": {}}))

                elif action == "train_model":
                    res = self.trainer.train()
                    await websocket.send(json.dumps({"type": "train_result", "result": res}))

                elif action == "toggle_os_input":
                    enabled = bool(data.get("enabled", True))
                    self.key_injector.set_enabled(enabled)
                    await websocket.send(json.dumps({"type": "os_input_status", "enabled": enabled}))

                elif action == "calibrate_aruco":
                    frame = self.camera_mgr.get_primary_frame()
                    if frame is not None:
                        success = self.perspective.calibrate_from_markers(frame)
                        await websocket.send(json.dumps({"type": "calibration_result", "success": success}))

                elif action == "set_manual_corners":
                    corners = data.get("corners", [])
                    self.perspective.set_manual_corners(corners)
                    await websocket.send(json.dumps({"type": "calibration_result", "success": True}))

                elif action == "update_keymap":
                    keys = data.get("keys", [])
                    self.key_mapper.save_keymap("custom", keys)
                    await websocket.send(json.dumps({"type": "keymap_updated", "keys": keys}))

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.remove(websocket)

    async def broadcast_loop(self):
        target_frame_time = 1.0 / 30.0
        while self.running:
            start_time = time.time()
            if self.connected_clients:
                cycle_data = self.process_cycle()
                if cycle_data:
                    payload = json.dumps(cycle_data)
                    dead_clients = set()
                    for client in list(self.connected_clients):
                        try:
                            await client.send(payload)
                        except Exception:
                            dead_clients.add(client)
                    self.connected_clients -= dead_clients
            
            elapsed = time.time() - start_time
            sleep_time = max(0.001, target_frame_time - elapsed)
            await asyncio.sleep(sleep_time)

    async def start(self):
        self.initialize()
        print(f"Starting WebSocket server on ws://{WS_HOST}:{WS_PORT}")
        async with websockets.serve(self.client_handler, WS_HOST, WS_PORT):
            await self.broadcast_loop()

    def shutdown(self):
        self.running = False
        self.camera_mgr.stop_all()
        self.hand_tracker.close()


def main():
    backend = VirtualKeyboardBackend()
    try:
        asyncio.run(backend.start())
    except KeyboardInterrupt:
        backend.shutdown()


if __name__ == "__main__":
    main()

