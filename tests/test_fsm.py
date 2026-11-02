import unittest
import time
from backend.engine.fsm import KeyStrikeFSM, StrikeState


class TestKeyStrikeFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = KeyStrikeFSM(z_velocity_thresh=-0.010, angle_thresh=150.0)

    def test_state_transitions_to_touch(self):
        # 1. Initial HOVER state
        is_strike, state = self.fsm.update(z_velocity=0.0, joint_angle=180.0)
        self.assertEqual(state, StrikeState.HOVER)
        self.assertFalse(is_strike)

        # 2. Downward thrust triggers DESCENDING
        is_strike, state = self.fsm.update(z_velocity=-0.015, joint_angle=140.0)
        self.assertEqual(state, StrikeState.DESCENDING)
        self.assertFalse(is_strike)

        # Allow time to pass for min state duration
        time.sleep(0.09)

        # 3. Contact occurs when downward speed decelerates / touches surface
        is_strike, state = self.fsm.update(z_velocity=-0.001, joint_angle=135.0)
        self.assertEqual(state, StrikeState.TOUCH)
        self.assertTrue(is_strike)


if __name__ == "__main__":
    unittest.main()

