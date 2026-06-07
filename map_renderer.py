"""
map_renderer.py — menggambar grid labirin ke pygame Surface.

Prioritas rendering per tile:
  1. Sprite animasi (strip PNG kustom)   — tile_anims dict
  2. Sprite statis (irisan spritesheet)  — tile_sprites dict
  3. Persegi panjang berwarna cadangan   — get_color() dari tiles.py
     + label simbol digambar di atas untuk tile non-dinding/lantai (jika tile cukup besar)

Renderer menyimpan referensi ke grid, bukan salinannya.
algorithm.py mengubah grid secara langsung (kunci, dinding yang rusak) dan kemudian
memanggil update_grid() sehingga renderer mengambil perubahan pada gambar berikutnya.
"""

import pygame
from tiles import get_color, TILE_COLORS

# Gambar label simbol (mis. "F", "K") hanya jika tile cukup besar untuk dibaca.
LABEL_MIN_TILE = 20
LABEL_COLOR    = (0, 0, 0, 120)   # hitam semi-transparan (konstanta tidak digunakan, disimpan sebagai referensi)

# Garis grid digambar di sekitar tile warna cadangan untuk menunjukkan batas sel.
BORDER_COLOR = (0, 0, 0)
BORDER_WIDTH = 1


class MapRenderer:
    def __init__(self, grid: list, tile_size: int, sprites: dict = None):
        self.grid      = grid
        self.tile_size = tile_size
        self.sprites   = sprites   # dict yang dikembalikan oleh sprite_loader.load_sprites()
        self._font     = None

        # Inisialisasi font label hanya jika tile cukup besar untuk dapat dibaca.
        if tile_size >= LABEL_MIN_TILE:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", max(10, tile_size // 3), bold=True)

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, ticks: int = 0, offset: tuple = (0, 0)):
        """
        Gambar setiap tile di grid.

        ticks  — pygame.time.get_ticks() digunakan untuk memajukan animasi tile.
        offset — (ox, oy) translasi kamera; kurangi cam_x/cam_y untuk menggeser tampilan.
        """
        ts           = self.tile_size
        ox, oy       = offset
        tile_sprites = self.sprites.get("tiles", {}) if self.sprites else {}
        tile_anims   = self.sprites.get("tile_anims", {}) if self.sprites else {}

        for r, row in enumerate(self.grid):
            for c, symbol in enumerate(row):
                x    = c * ts + ox
                y    = r * ts + oy
                rect = pygame.Rect(x, y, ts, ts)

                if symbol in tile_anims:
                    # Tile animasi — siklus frame menggunakan waktu yang berlalu.
                    # Membagi ticks dengan 200 memberikan animasi ~5 fps terlepas dari FPS game.
                    frames = tile_anims[symbol]
                    frame  = frames[(ticks // 200) % len(frames)]
                    surface.blit(frame, (x, y))
                elif symbol in tile_sprites:
                    # Sprite statis dari spritesheet
                    surface.blit(tile_sprites[symbol], (x, y))
                else:
                    # Cadangan: persegi panjang berwarna + garis luar grid
                    pygame.draw.rect(surface, get_color(symbol), rect)
                    pygame.draw.rect(surface, BORDER_COLOR, rect, BORDER_WIDTH)
                    # Gambar karakter simbol pada tile non-trivial agar peta dapat dibaca
                    if self._font and symbol not in ("#", "."):
                        self._draw_label(surface, symbol, x, y, ts)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _draw_label(self, surface, symbol, x, y, ts):
        """Pusatkan karakter simbol tile di dalam persegi panjang tile."""
        label_surf = self._font.render(symbol, True, (255, 255, 255))
        lw, lh     = label_surf.get_size()
        cx         = x + (ts - lw) // 2
        cy         = y + (ts - lh) // 2
        surface.blit(label_surf, (cx, cy))

    def set_tile_size(self, ts: int):
        """Bangun ulang font ketika pengguna zoom masuk atau keluar dengan roda gulir."""
        self.tile_size = ts
        if ts >= LABEL_MIN_TILE:
            self._font = pygame.font.SysFont("monospace", max(10, ts // 3), bold=True)
        else:
            self._font = None   # tile terlalu kecil — lewati label sepenuhnya

    def update_grid(self, grid: list):
        """
        Tukar referensi grid baru (atau yang telah diubah).
        Dipanggil oleh algorithm.py setelah setiap perubahan grid di tempat (mengambil kunci, menghancurkan dinding)
        sehingga renderer segera mencerminkan status yang diperbarui.
        """
        self.grid = grid