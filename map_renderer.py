"""
map_renderer.py
Reads a grid from map_loader and draws colored rectangles using tiles.py.
Phase 1: pure colored-rectangle rendering, no sprites.
"""

import pygame
from tiles import get_color, TILE_COLORS

# Small label font size (drawn inside large-enough tiles)
LABEL_MIN_TILE = 20
LABEL_COLOR    = (0, 0, 0, 120)   # semi-transparent black

# Border drawn around each tile to give grid definition
BORDER_COLOR = (0, 0, 0)
BORDER_WIDTH = 1


class MapRenderer:
    def __init__(self, grid: list, tile_size: int, sprites: dict = None):
        self.grid      = grid
        self.tile_size = tile_size
        self.sprites   = sprites
        self._font     = None

        if tile_size >= LABEL_MIN_TILE:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", max(10, tile_size // 3), bold=True)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, ticks: int = 0, offset: tuple = (0, 0)):
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
                    frames = tile_anims[symbol]
                    frame  = frames[(ticks // 200) % len(frames)]
                    surface.blit(frame, (x, y))
                elif symbol in tile_sprites:
                    surface.blit(tile_sprites[symbol], (x, y))
                else:
                    pygame.draw.rect(surface, get_color(symbol), rect)
                    pygame.draw.rect(surface, BORDER_COLOR, rect, BORDER_WIDTH)
                    if self._font and symbol not in ("#", "."):
                        self._draw_label(surface, symbol, x, y, ts)

    # ------------------------------------------------------------------
    def _draw_label(self, surface, symbol, x, y, ts):
        label_surf = self._font.render(symbol, True, (255, 255, 255))
        lw, lh     = label_surf.get_size()
        cx         = x + (ts - lw) // 2
        cy         = y + (ts - lh) // 2
        surface.blit(label_surf, (cx, cy))

    # ------------------------------------------------------------------
    def set_tile_size(self, ts: int):
        self.tile_size = ts
        if ts >= LABEL_MIN_TILE:
            self._font = pygame.font.SysFont("monospace", max(10, ts // 3), bold=True)
        else:
            self._font = None

    # ------------------------------------------------------------------
    def update_grid(self, grid: list):
        """Allow external code to swap in a modified grid (e.g. after a wall break)."""
        self.grid = grid