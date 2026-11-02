import time
from typing import Optional, Union
from pynput.keyboard import Controller, Key


class KeyInjector:
    SPECIAL_KEYS = {
        "up": Key.up,
        "down": Key.down,
        "left": Key.left,
        "right": Key.right,
        "space": Key.space,
        "enter": Key.enter,
        "return": Key.enter,
        "backspace": Key.backspace,
        "tab": Key.tab,
        "esc": Key.esc,
        "escape": Key.esc,
        "shift": Key.shift,
        "ctrl": Key.ctrl,
        "alt": Key.alt,
    }

    def __init__(self, debounce_seconds: float = 0.25):
        self.keyboard = Controller()
        self.debounce_seconds = debounce_seconds
        self.enabled = True
        self.last_press_time = 0.0
        self.last_key_pressed: Optional[str] = None

    def set_enabled(self, enabled: bool):
        self.enabled = enabled

    def _resolve_key(self, key_code: str) -> Union[Key, str]:
        normalized = key_code.lower().strip()
        if normalized in self.SPECIAL_KEYS:
            return self.SPECIAL_KEYS[normalized]
        if len(key_code) == 1:
            return key_code
        return key_code

    def press_and_release(self, key_code: str) -> bool:
        """
        Executes an OS key press and release event if debounce interval is satisfied.
        """
        now = time.time()
        if (now - self.last_press_time) < self.debounce_seconds:
            return False

        self.last_press_time = now
        self.last_key_pressed = key_code

        if not self.enabled:
            return True

        target_key = self._resolve_key(key_code)
        try:
            self.keyboard.press(target_key)
            time.sleep(0.02)
            self.keyboard.release(target_key)
            return True
        except Exception:
            return False

