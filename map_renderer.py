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
    def __init__(self, grid: list, tile_size: int):
        self.grid      = grid
        self.tile_size = tile_size
        self._font     = None

        if tile_size >= LABEL_MIN_TILE:
            pygame.font.init()
            self._font = pygame.font.SysFont("monospace", max(10, tile_size // 3), bold=True)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        ts = self.tile_size

        for r, row in enumerate(self.grid):
            for c, symbol in enumerate(row):
                x = c * ts
                y = r * ts

                color = get_color(symbol)
                rect  = pygame.Rect(x, y, ts, ts)

                # Fill tile
                pygame.draw.rect(surface, color, rect)

                # Grid border
                pygame.draw.rect(surface, BORDER_COLOR, rect, BORDER_WIDTH)

                # Symbol label (only for non-floor, non-wall tiles)
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
    def update_grid(self, grid: list):
        """Allow external code to swap in a modified grid (e.g. after a wall break)."""
        self.grid = grid