"""
player.py — bot yang digerakkan oleh algoritma melalui labirin.

Melacak semua status runtime: posisi, HP, kunci, langkah, hitung mundur beku,
arah pergerakan, dan status animasi.

algorithm.py menggerakkan bot murni melalui set_position() — tidak pernah
memanggil try_move() secara langsung. try_move() disimpan untuk kemungkinan penggunaan manual.
"""

import pygame
from tiles import is_passable

# ── Konstanta gambar cadangan (digunakan saat tidak ada sprite sheet yang dimuat) ──────────
BOT_COLOR        = (50, 200, 255)
BOT_BORDER_COLOR = (10,  80, 120)
BOT_PADDING      = 4
BOT_FROZEN_COLOR = (30, 120, 160)   # nuansa lebih gelap saat beku di lumpur

# Majukan animasi sprite satu frame setiap N panggilan draw().
# Pada 60 fps ini memberikan ~7,5 fps animasi, yang terlihat mulus tanpa berkedip.
ANIM_TICKS_PER_FRAME = 8


class Player:
    def __init__(self, row: int, col: int, tile_size: int, start_hp: int = 100):
        self.row       = row
        self.col       = col
        self.tile_size = tile_size
        self.keys      = 0           # jumlah kunci yang sedang dipegang
        self.hp        = start_hp    # poin nyawa; mencapai 0 memaksa mundur
        self.steps     = 0           # biaya langkah kumulatif (digunakan dalam penilaian)
        self.freeze_frames_left = 0  # hitung mundur yang diatur oleh tile lumpur; bot berhenti saat > 0
        self.direction    = "down"   # arah terakhir bergerak; memilih orientasi sprite yang benar
        self.is_backtrack = False    # True saat algoritma mundur (mempengaruhi pembalikan sprite)
        self.is_active    = False    # True saat algoritma berjalan (memicu animasi lari)
        self.anim_frame   = 0        # indeks ke dalam daftar frame saat ini
        self.anim_tick    = 0        # penghitung panggilan draw; wraps di ANIM_TICKS_PER_FRAME

    # ── Pergerakan ──────────────────────────────────────────────────────────────

    def try_move(self, dr: int, dc: int, grid: list) -> bool:
        """
        Coba gerakan satu langkah dengan delta (dr, dc).
        Memvalidasi batas dan kelayakan, menggunakan kunci jika memasuki dinding %.
        Mengembalikan True jika berhasil, False jika diblokir.
        Tidak digunakan oleh algorithm.py — disimpan untuk kompatibilitas bermain manual.
        """
        new_r = self.row + dr
        new_c = self.col + dc
        if not (0 <= new_r < len(grid) and 0 <= new_c < len(grid[0])):
            return False
        target = grid[new_r][new_c]
        if not is_passable(target, self.keys):
            return False
        if target == "%" and self.keys > 0:
            self.keys -= 1
            grid[new_r][new_c] = "."
        self.row = new_r
        self.col = new_c
        return True

    def set_position(self, row: int, col: int):
        """
        Teleportkan bot ke (row, col) dan perbarui arah berdasarkan delta.
        algorithm.py memanggil ini secara langsung alih-alih try_move() sehingga bisa
        menangani kelayakan dan konsumsi kunci sendiri sebelum bergerak.
        Arah digunakan oleh draw() untuk memilih orientasi sprite yang benar.
        """
        dr, dc = row - self.row, col - self.col
        if   dr < 0: self.direction = "up"
        elif dr > 0: self.direction = "down"
        elif dc < 0: self.direction = "left"
        elif dc > 0: self.direction = "right"
        self.row = row
        self.col = col

    def is_frozen(self) -> bool:
        """True saat bot terjebak pada tile lumpur (freeze_frames_left > 0)."""
        return self.freeze_frames_left > 0

    def tick_freeze(self):
        """Kurangi penghitung beku lumpur satu per satu setiap iterasi loop game."""
        if self.freeze_frames_left > 0:
            self.freeze_frames_left -= 1

    # ── Rendering ─────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, sprites: dict = None, offset: tuple = (0, 0)):
        """
        Gambar bot pada posisi grid saat ini.

        Logika pemilihan sprite:
          beku        → frame terkena (pose terpana)
          aktif+gerak → animasi lari, dibalik secara horizontal saat mundur
                        (flip_x XOR: menghadap kiri biasanya dibalik; mundur membalikkannya)
          diam        → animasi diam

        Kembali ke persegi panjang bulat sederhana jika tidak ada sprite yang dimuat.
        offset adalah translasi kamera yang diterapkan ke setiap panggilan draw (cx, cy dinegasikan).
        """
        ts     = self.tile_size
        ox, oy = offset

        if sprites is not None:
            bot = sprites.get("bot", {})

            # Pilih set animasi yang akan dimainkan berdasarkan status bot saat ini
            if self.is_frozen():
                frames = bot.get("hit") or bot.get("idle")
                flip_x = False
            elif self.is_active:
                frames = bot.get("run") or bot.get("idle")
                # Balik secara horizontal saat menghadap kiri; XOR dengan flag mundur agar
                # bot yang mundur tetap menghadap arah yang dituju, bukan asal usulnya
                flip_x = (self.direction == "left") ^ self.is_backtrack
            else:
                frames = bot.get("idle") or bot.get("run")
                flip_x = (self.direction == "left")

            if frames:
                # Majukan frame animasi pada interval tick yang tetap
                self.anim_tick += 1
                if self.anim_tick >= ANIM_TICKS_PER_FRAME:
                    self.anim_tick  = 0
                    self.anim_frame = (self.anim_frame + 1) % len(frames)

                frame = frames[self.anim_frame % len(frames)]
                if flip_x:
                    frame = pygame.transform.flip(frame, True, False)
                surface.blit(frame, (self.col * ts + ox, self.row * ts + oy))
                return

        # ── Cadangan: gambar persegi panjang berwarna sederhana ─────────────────────────
        p     = BOT_PADDING
        x     = self.col * ts + ox + p
        y     = self.row * ts + oy + p
        w     = ts - p * 2
        h     = ts - p * 2
        color = BOT_FROZEN_COLOR if self.is_frozen() else BOT_COLOR
        rect  = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, BOT_BORDER_COLOR, rect, 2, border_radius=4)