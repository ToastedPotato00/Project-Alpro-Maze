import os
import pygame

SOUND_FILES = {
    "step":       "sounds/step.wav",
    "mud":        "sounds/mud.wav",
    "fire":       "sounds/fire.wav",
    "regen":      "sounds/regen.wav",
    "teleport":   "sounds/teleport.wav",
    "key_pickup": "sounds/key_pickup.wav",
    "wall_break": "sounds/wall_break.wav",
    "goal":       "sounds/goal.wav",
}


class SoundManager:
    def __init__(self):
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                self._sounds = {}
                return
        self._sounds = {}
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
