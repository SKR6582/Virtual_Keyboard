import json
import os
from typing import Dict, List, Any


class DatasetManager:
    def __init__(self, dataset_path: str):
        self.dataset_path = dataset_path
        self.samples: List[Dict[str, Any]] = []
        self.load()

    def load(self) -> bool:
        if not os.path.exists(self.dataset_path):
            self.samples = []
            return False
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                self.samples = json.load(f)
            return True
        except Exception:
            self.samples = []
            return False

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.dataset_path), exist_ok=True)
            with open(self.dataset_path, "w", encoding="utf-8") as f:
                json.dump(self.samples, f, indent=2)
            return True
        except Exception:
            return False

    def add_sample(self, key_label: str, target_xy: List[float], feature_vector: List[float], is_pressed: int = 1):
        self.samples.append({
            "key_label": key_label,
            "target_xy": target_xy,
            "feature_vector": feature_vector,
            "is_pressed": is_pressed
        })
        self.save()

    def clear(self):
        self.samples = []
        self.save()

    def get_stats(self) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for s in self.samples:
            label = s.get("key_label", "UNKNOWN")
            stats[label] = stats.get(label, 0) + 1
        return stats

    def get_data(self) -> List[Dict[str, Any]]:
        return self.samples

