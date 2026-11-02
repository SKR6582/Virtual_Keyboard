import unittest
import numpy as np
import cv2
from backend.vision.perspective import PerspectiveCorrector


class TestPerspectiveCorrector(unittest.TestCase):
    def setUp(self):
        self.corrector = PerspectiveCorrector(plane_width=1000, plane_height=600)

    def test_manual_calibration_and_transform(self):
        # Define 4 corners representing a tilted quadrangle
        corners = [(100.0, 50.0), (900.0, 70.0), (850.0, 550.0), (120.0, 530.0)]
        self.corrector.set_manual_corners(corners)
        self.assertTrue(self.corrector.is_calibrated)

        # Top-left corner should map near (0, 0)
        out_x, out_y = self.corrector.transform_point(100.0, 50.0)
        self.assertAlmostEqual(out_x, 0.0, delta=2.0)
        self.assertAlmostEqual(out_y, 0.0, delta=2.0)

        # Bottom-right corner should map near (1000, 600)
        out_x, out_y = self.corrector.transform_point(850.0, 550.0)
        self.assertAlmostEqual(out_x, 1000.0, delta=2.0)
        self.assertAlmostEqual(out_y, 600.0, delta=2.0)

    def test_warp_image_shape(self):
        test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        corners = [(100.0, 50.0), (900.0, 70.0), (850.0, 550.0), (120.0, 530.0)]
        self.corrector.set_manual_corners(corners)
        
        warped = self.corrector.warp_image(test_frame)
        self.assertEqual(warped.shape, (600, 1000, 3))


if __name__ == "__main__":
    unittest.main()

