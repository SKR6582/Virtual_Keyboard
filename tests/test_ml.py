import unittest
import os
import shutil
import tempfile
import numpy as np
from backend.ml.dataset import DatasetManager
from backend.ml.model import VirtualKeyboardMLModel
from backend.ml.trainer import ModelTrainer


class TestMLPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.dataset_path = os.path.join(self.test_dir, "dataset.json")
        self.model_path = os.path.join(self.test_dir, "model.pkl")
        self.dataset_mgr = DatasetManager(self.dataset_path)
        self.ml_model = VirtualKeyboardMLModel(self.model_path, plane_width=1000, plane_height=600)
        self.trainer = ModelTrainer(self.dataset_mgr, self.ml_model)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_training_and_prediction(self):
        # 1. Check initial heuristic prediction before training
        dummy_vec = np.zeros(16, dtype=np.float32)
        dummy_vec[0] = 0.5
        dummy_vec[1] = 0.5
        pred_before = self.ml_model.predict(dummy_vec)
        self.assertEqual(pred_before["source"], "heuristic")
        self.assertAlmostEqual(pred_before["predicted_xy"][0], 500.0, delta=1.0)

        # 2. Train with baseline samples
        train_res = self.trainer.train()
        self.assertTrue(train_res["success"])
        self.assertTrue(os.path.exists(self.model_path))
        self.assertTrue(self.ml_model.is_trained)

        # 3. Predict with trained model
        pred_after = self.ml_model.predict(dummy_vec)
        self.assertEqual(pred_after["source"], "ml_model")
        self.assertIn("predicted_xy", pred_after)
        self.assertIn("key_label", pred_after)


if __name__ == "__main__":
    unittest.main()

