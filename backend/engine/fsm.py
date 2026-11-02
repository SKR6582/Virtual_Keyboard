from enum import Enum
import time
from typing import Tuple


class StrikeState(Enum):
    HOVER = "HOVER"
    DESCENDING = "DESCENDING"
    TOUCH = "TOUCH"
    RELEASE = "RELEASE"


class KeyStrikeFSM:
    """
    Finite State Machine for physics-based key press determination:
    Tracks fingertip Z-velocity (dz/dt) and joint bending angle.
    """
    def __init__(self, z_velocity_thresh: float = -0.008, angle_thresh: float = 155.0):
        self.z_velocity_thresh = z_velocity_thresh
        self.angle_thresh = angle_thresh
        self.state = StrikeState.HOVER
        self.last_transition_time = time.time()
        self.min_state_duration = 0.05  # 50ms min duration

    def update(self, z_velocity: float, joint_angle: float) -> Tuple[bool, StrikeState]:
        """
        Updates state and returns (is_strike_moment, current_state).
        is_strike_moment is True only on the frame the TOUCH state is entered.
        """
        now = time.time()
        time_in_state = now - self.last_transition_time
        is_strike = False

        if self.state == StrikeState.HOVER:
            # Downward velocity and finger bending
            if z_velocity < self.z_velocity_thresh or joint_angle < self.angle_thresh:
                self.state = StrikeState.DESCENDING
                self.last_transition_time = now

        elif self.state == StrikeState.DESCENDING:
            # Transition to TOUCH when velocity slows down/rebounds near the surface
            if z_velocity >= (self.z_velocity_thresh * 0.3) or time_in_state > 0.08:
                self.state = StrikeState.TOUCH
                self.last_transition_time = now
                is_strike = True

        elif self.state == StrikeState.TOUCH:
            # Finger begins moving upwards or duration expired
            if z_velocity > 0.005 or time_in_state > 0.12:
                self.state = StrikeState.RELEASE
                self.last_transition_time = now

        elif self.state == StrikeState.RELEASE:
            if time_in_state > self.min_state_duration:
                self.state = StrikeState.HOVER
                self.last_transition_time = now

        return is_strike, self.state

