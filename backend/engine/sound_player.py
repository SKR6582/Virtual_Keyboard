import os
import sys
import threading
import subprocess
from typing import Optional

try:
    import winsound
except ImportError:
    winsound = None


class SoundPlayer:
    def __init__(self, sound_path: str):
        self.sound_path = sound_path
        self.enabled = os.path.exists(sound_path)

    def play_click(self):
        if not self.enabled:
            return
        threading.Thread(target=self._play_sync, daemon=True).start()

    def _play_sync(self):
        try:
            if sys.platform == "win32" and winsound:
                winsound.PlaySound(self.sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif sys.platform == "darwin":
                # macOS built-in afplay
                subprocess.run(["afplay", "-q", "1", self.sound_path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Linux fallback
                subprocess.run(["aplay", "-q", self.sound_path],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

