import json
import os
from typing import Dict, List, Optional, Any


class KeyMapper:
    def __init__(self, keymap_path: str):
        self.keymap_path = keymap_path
        self.layout_name = "default"
        self.plane_size = [1000, 600]
        self.keys: List[Dict[str, Any]] = []
        self.load_keymap()

    def load_keymap(self) -> bool:
        if not os.path.exists(self.keymap_path):
            return False
        try:
            with open(self.keymap_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.layout_name = data.get("layout_name", "custom")
            self.plane_size = data.get("plane_size", [1000, 600])
            self.keys = data.get("keys", [])
            return True
        except Exception:
            return False

    def save_keymap(self, layout_name: str, keys: List[Dict[str, Any]], plane_size: Optional[List[int]] = None) -> bool:
        data = {
            "layout_name": layout_name,
            "plane_size": plane_size or self.plane_size,
            "keys": keys
        }
        try:
            os.makedirs(os.path.dirname(self.keymap_path), exist_ok=True)
            with open(self.keymap_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.layout_name = layout_name
            self.keys = keys
            if plane_size:
                self.plane_size = plane_size
            return True
        except Exception:
            return False

    def find_key_at_point(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        """
        Point-in-Rectangle collision check against all defined keys.
        bbox format: [x1, y1, x2, y2]
        """
        for key in self.keys:
            bbox = key.get("bbox")
            if not bbox or len(bbox) != 4:
                continue
            x1, y1, x2, y2 = bbox
            if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
                return key
        return None

    def get_keys(self) -> List[Dict[str, Any]]:
        return self.keys

