import os
import joblib
import numpy as np
from typing import Dict, Optional, Tuple, Any


class VirtualKeyboardMLModel:
    def __init__(self, model_path: str, plane_width: int = 1000, plane_height: int = 600):
        self.model_path = model_path
        self.plane_width = plane_width
        self.plane_height = plane_height
        
        self.contact_classifier = None
        self.coord_regressor = None
        self.key_classifier = None
        self.is_trained = False
        
        self.load()

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            self.is_trained = False
            return False
        try:
            bundle = joblib.load(self.model_path)
            self.contact_classifier = bundle.get("contact_classifier")
            self.coord_regressor = bundle.get("coord_regressor")
            self.key_classifier = bundle.get("key_classifier")
            self.is_trained = True
            return True
        except Exception:
            self.is_trained = False
            return False

    def save(self, bundle: Dict[str, Any]) -> bool:
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            joblib.dump(bundle, self.model_path)
            self.contact_classifier = bundle.get("contact_classifier")
            self.coord_regressor = bundle.get("coord_regressor")
            self.key_classifier = bundle.get("key_classifier")
            self.is_trained = True
            return True
        except Exception:
            return False

    def predict(self, feature_vector: np.ndarray) -> Dict[str, Any]:
        """
        Given a 16-D feature vector, predict touch contact, (X, Y) coordinates, and target key.
        """
        X = np.array(feature_vector, dtype=np.float32).reshape(1, -1)

        if not self.is_trained:
            # Fallback heuristic prediction when ML model has not been trained yet
            norm_x = float(feature_vector[0])
            norm_y = float(feature_vector[1])
            z_vel = float(feature_vector[3])
            angle_norm = float(feature_vector[4])
            
            pred_x = norm_x * self.plane_width
            pred_y = norm_y * self.plane_height
            is_contact = (z_vel < -0.008 or angle_norm < 0.85)

            return {
                "is_contact": is_contact,
                "predicted_xy": (pred_x, pred_y),
                "key_label": None,
                "confidence": 0.70,
                "source": "heuristic"
            }

        # Predict using trained scikit-learn models
        is_contact = False
        contact_prob = 0.5
        if self.contact_classifier is not None:
            contact_pred = self.contact_classifier.predict(X)[0]
            is_contact = bool(contact_pred == 1)
            if hasattr(self.contact_classifier, "predict_proba"):
                probs = self.contact_classifier.predict_proba(X)[0]
                contact_prob = float(probs[1]) if len(probs) > 1 else float(probs[0])

        pred_xy = (float(feature_vector[0] * self.plane_width), float(feature_vector[1] * self.plane_height))
        if self.coord_regressor is not None:
            reg_out = self.coord_regressor.predict(X)[0]
            pred_xy = (float(reg_out[0]), float(reg_out[1]))

        key_label = None
        key_conf = contact_prob
        if self.key_classifier is not None:
            key_label = str(self.key_classifier.predict(X)[0])
            if hasattr(self.key_classifier, "predict_proba"):
                key_probs = self.key_classifier.predict_proba(X)[0]
                key_conf = float(np.max(key_probs))

        return {
            "is_contact": is_contact,
            "predicted_xy": pred_xy,
            "key_label": key_label,
            "confidence": key_conf,
            "source": "ml_model"
        }

