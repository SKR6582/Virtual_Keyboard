import unittest
import numpy as np
from backend.vision.feature_extractor import MultiViewFeatureExtractor


class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = MultiViewFeatureExtractor(plane_width=1000, plane_height=600)

    def test_single_camera_extraction(self):
        primary_track = {
            "tip_pixel": (500.0, 300.0),
            "tip_z": -0.02,
            "z_velocity": -0.012,
            "joint_angle": 145.0,
            "wrist": [500.0, 500.0, 0.0]
        }
        warped_coords = (500.0, 300.0)

        vec = self.extractor.extract_vector(primary_track, warped_coords)
        self.assertEqual(len(vec), 16)
        self.assertAlmostEqual(vec[0], 0.5, delta=0.01)
        self.assertAlmostEqual(vec[1], 0.5, delta=0.01)
        self.assertAlmostEqual(vec[2], -0.02, delta=0.01)
        self.assertAlmostEqual(vec[3], -0.012, delta=0.001)

    def test_multi_camera_extraction(self):
        primary_track = {
            "tip_pixel": (500.0, 300.0),
            "tip_z": 0.01,
            "z_velocity": 0.0,
            "joint_angle": 180.0,
            "wrist": [500.0, 500.0, 0.0]
        }
        warped_coords = (500.0, 300.0)
        secondary_tracks = {
            1: {"tip_pixel": (600.0, 400.0)},
            2: {"tip_pixel": (650.0, 420.0)}
        }

        vec = self.extractor.extract_vector(primary_track, warped_coords, secondary_tracks)
        self.assertEqual(len(vec), 16)
        # Cam 1 flag should be 1.0
        self.assertEqual(vec[5], 1.0)
        # Cam 2 flag should be 1.0
        self.assertEqual(vec[8], 1.0)
        # Cam 3 flag should be 0.0 (not provided)
        self.assertEqual(vec[11], 0.0)


if __name__ == "__main__":
    unittest.main()

