"""
sound_manager.py — membungkus pygame.mixer untuk semua audio dalam game.

Efek suara (SFX) adalah klip pendek sekali putar yang dimuat sebagai objek pygame.mixer.Sound.
Musik latar (BGM) menggunakan pygame.mixer.music yang melakukan streaming dari disk
alih-alih memuat seluruh file ke memori — lebih baik untuk file audio panjang.

SoundManager secara diam-diam terdegradasi jika perangkat audio tidak tersedia atau ada
file suara yang hilang; game berjalan dengan baik tanpa audio.
"""

import os
import pygame

# Memetakan nama event → jalur file untuk setiap efek suara sekali putar.
# main.py memanggil sounds.play("<name>") setelah setiap event algoritma.
SOUND_FILES = {
    "step":       "sounds/step.mp3",
    "mud":        "sounds/mud.mp3",
    "fire":       "sounds/fire.mp3",
    "regen":      "sounds/regen.mp3",
    "teleport":   "sounds/teleport.mp3",
    "key_pickup": "sounds/key.mp3",
    "wall_break": "sounds/wall_break.mp3",
    "goal":       "sounds/goal.mp3",
    "click":      "sounds/click.mp3",   # umpan balik tombol UI
}

BGM_PATH = "sounds/bg1.mp3"   # trek musik latar yang diulang


class SoundManager:
    def __init__(self):
        # Inisialisasi mixer hanya jika belum dimulai.
        # Jika init gagal (tidak ada perangkat audio), tandai bgm sebagai tidak tersedia dan lewati pemuatan.
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception:
                self._sounds = {}
                self._bgm_ok = False
                return
        self._sounds = {}
        self._bgm_ok = True
        # Muat setiap file SFX ke memori. File yang hilang atau tidak dapat dibaca dilewati secara diam-diam.
        for name, path in SOUND_FILES.items():
            if os.path.exists(path):
                try:
                    self._sounds[name] = pygame.mixer.Sound(path)
                except Exception:
                    pass   # file audio buruk — lewati tanpa crash

    def play(self, name):
        """Mainkan efek suara sekali putar berdasarkan nama. Tidak melakukan apa-apa jika tidak dimuat."""
        s = self._sounds.get(name)
        if s:
            s.play()

    # ── Musik latar ──────────────────────────────────────────────────────

    def play_bgm(self, path=BGM_PATH, loops=-1, volume=0.4):
        """
        Streaming dan ulangi trek musik latar.
        loops=-1 berarti ulangi tanpa batas.
        volume adalah 0,0–1,0; default 0,4 menjaga BGM lebih pelan dari SFX.
        """
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
        """Hentikan musik latar (dipanggil saat keluar)."""
        if not self._bgm_ok:
            return
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def set_bgm_volume(self, volume):
        """Sesuaikan volume BGM saat runtime. volume: 0,0 – 1,0"""
        if not self._bgm_ok:
            return
        try:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
        except Exception:
            pass
