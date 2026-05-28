import os
import pygame

SOUND_FILES = {
    "step":       "sounds/step.mp3",
    "mud":        "sounds/mud.mp3",
    "fire":       "sounds/fire.mp3",
    "regen":      "sounds/regen.mp3",
    "teleport":   "sounds/teleport.mp3",
    "key_pickup": "sounds/key.mp3",
    "wall_break": "sounds/wall_break.mp3",
    "goal":       "sounds/goal.mp3",
    "click":      "sounds/click.mp3",
}

BGM_PATH = "sounds/bg1.mp3"


class SoundManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                self._sounds = {}
                self._bgm_ok = False
                return
        self._sounds = {}
        self._bgm_ok = True
        for name, path in SOUND_FILES.items():
            if os.path.exists(path):
                try:
                    self._sounds[name] = pygame.mixer.Sound(path)
                except Exception:
                    pass

    def play(self, name):
        s = self._sounds.get(name)
        if s:
            s.play()

    # ── BGM ───────────────────────────────────────────────────────────────────

    def play_bgm(self, path=BGM_PATH, loops=-1, volume=0.4):
        if not self._bgm_ok:
            return
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
        except Exception:
            pass

    def stop_bgm(self):
        if not self._bgm_ok:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def set_bgm_volume(self, volume):
        """volume: 0.0 – 1.0"""
        if not self._bgm_ok:
            return
        try:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        except Exception:
            pass
