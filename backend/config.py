import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Camera Configuration
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_FPS = 30
CAMERA_FOURCC = 'MJPG'
MAX_PROBE_CAMERAS = 4

# WebSocket Configuration
WS_HOST = '127.0.0.1'
WS_PORT = 8765

# ArUco Marker Configuration (DICT_4X4_50)
ARUCO_DICT_ID = 0  # cv2.aruco.DICT_4X4_50
ARUCO_CORNER_IDS = [0, 1, 2, 3]  # [Top-Left, Top-Right, Bottom-Right, Bottom-Left]

# Paths
KEYMAP_PATH = os.path.join(BASE_DIR, 'config', 'keymap.json')
MODEL_PATH = os.path.join(BASE_DIR, 'config', 'virtual_keyboard_model.pkl')
DATASET_PATH = os.path.join(BASE_DIR, 'config', 'training_data.json')
SOUND_PATH = os.path.join(BASE_DIR, 'assets', 'sounds', 'click.wav')

# Physical & Gesture Engine Parameters
MOVING_AVERAGE_FRAMES = 3
Z_VELOCITY_PRESS_THRESHOLD = -0.008
JOINT_BEND_ANGLE_THRESHOLD = 155.0  # degrees
DEBOUNCE_SECONDS = 0.25  # 250ms cooldown
PREVIEW_JPEG_QUALITY = 65

