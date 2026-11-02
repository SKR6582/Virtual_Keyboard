import numpy as np
from typing import Dict, List, Any
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score
from backend.ml.dataset import DatasetManager
from backend.ml.model import VirtualKeyboardMLModel


class ModelTrainer:
    def __init__(self, dataset_manager: DatasetManager, ml_model: VirtualKeyboardMLModel):
        self.dataset_manager = dataset_manager
        self.ml_model = ml_model

    def train(self) -> Dict[str, Any]:
        """
        Trains contact classifier, coordinate regressor, and direct key classifier.
        Saves resulting bundle to .pkl.
        """
        samples = self.dataset_manager.get_data()
        
        # If dataset has fewer than 10 samples, seed with baseline synthetic variations
        if len(samples) < 10:
            samples = self._generate_baseline_samples()

        X = []
        y_contact = []
        y_coord = []
        y_label = []

        for s in samples:
            X.append(s["feature_vector"])
            y_contact.append(s.get("is_pressed", 1))
            y_coord.append(s.get("target_xy", [500.0, 300.0]))
            y_label.append(s.get("key_label", "SPACE"))

        X = np.array(X, dtype=np.float32)
        y_contact = np.array(y_contact, dtype=np.int32)
        y_coord = np.array(y_coord, dtype=np.float32)
        y_label = np.array(y_label)

        # 1. Contact Classifier
        clf_contact = RandomForestClassifier(n_estimators=30, max_depth=8, random_state=42)
        clf_contact.fit(X, y_contact)
        contact_acc = float(accuracy_score(y_contact, clf_contact.predict(X)))

        # 2. Coordinate Regressor
        reg_coord = RandomForestRegressor(n_estimators=30, max_depth=8, random_state=42)
        reg_coord.fit(X, y_coord)

        # 3. Key Classifier
        clf_key = RandomForestClassifier(n_estimators=30, max_depth=8, random_state=42)
        clf_key.fit(X, y_label)
        key_acc = float(accuracy_score(y_label, clf_key.predict(X)))

        bundle = {
            "contact_classifier": clf_contact,
            "coord_regressor": reg_coord,
            "key_classifier": clf_key,
            "sample_count": len(samples),
            "contact_accuracy": contact_acc,
            "key_accuracy": key_acc
        }

        self.ml_model.save(bundle)

        return {
            "success": True,
            "sample_count": len(samples),
            "contact_accuracy": round(contact_acc * 100, 1),
            "key_accuracy": round(key_acc * 100, 1)
        }

    def _generate_baseline_samples(self) -> List[Dict[str, Any]]:
        """
        Generates realistic baseline training samples centered around each key.
        """
        synthetic = []
        keys = [
            ("UP", [500.0, 150.0]),
            ("LEFT", [380.0, 270.0]),
            ("DOWN", [500.0, 270.0]),
            ("RIGHT", [620.0, 270.0]),
            ("SPACE", [500.0, 410.0]),
            ("ENTER", [780.0, 270.0]),
            ("BACKSPACE", [780.0, 150.0])
        ]

        np.random.seed(42)
        for label, (cx, cy) in keys:
            # Positive touch samples
            for _ in range(12):
                vec = np.zeros(16, dtype=np.float32)
                vec[0] = (cx + np.random.uniform(-15, 15)) / 1000.0
                vec[1] = (cy + np.random.uniform(-15, 15)) / 600.0
                vec[2] = np.random.uniform(-0.05, 0.02)
                vec[3] = np.random.uniform(-0.025, -0.009)  # downward velocity
                vec[4] = np.random.uniform(0.65, 0.85)      # joint bent
                synthetic.append({
                    "key_label": label,
                    "target_xy": [cx, cy],
                    "feature_vector": vec.tolist(),
                    "is_pressed": 1
                })

            # Negative hover samples
            for _ in range(6):
                vec = np.zeros(16, dtype=np.float32)
                vec[0] = (cx + np.random.uniform(-30, 30)) / 1000.0
                vec[1] = (cy + np.random.uniform(-30, 30)) / 600.0
                vec[2] = np.random.uniform(0.08, 0.25)
                vec[3] = np.random.uniform(0.001, 0.02)     # upward or stationary
                vec[4] = np.random.uniform(0.92, 1.0)       # finger straight
                synthetic.append({
                    "key_label": "NONE",
                    "target_xy": [cx, cy],
                    "feature_vector": vec.tolist(),
                    "is_pressed": 0
                })

        return synthetic

