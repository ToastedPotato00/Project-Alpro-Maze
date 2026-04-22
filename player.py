"""
player.py — Phase 4
Bot with full stat tracking: HP, keys, steps.
try_move() is still here for Phase 2 compatibility but algorithm.py
drives movement directly via set_position() in Phase 3+.
"""

import pygame
from tiles import is_passable

BOT_COLOR        = (50, 200, 255)
BOT_BORDER_COLOR = (10,  80, 120)
BOT_PADDING      = 4

# Mud freeze: bot flashes darker while frozen
BOT_FROZEN_COLOR = (30, 120, 160)


class Player:
    def __init__(self, row: int, col: int, tile_size: int):
        self.row       = row
        self.col       = col
        self.tile_size = tile_size
        self.keys      = 0
        self.hp        = 100
        self.steps     = 0
        self.freeze_frames_left = 0   # mud freeze countdown

    # ------------------------------------------------------------------
    def try_move(self, dr: int, dc: int, grid: list) -> bool:
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
        self.row = row
        self.col = col

    def is_frozen(self) -> bool:
        return self.freeze_frames_left > 0

    def tick_freeze(self):
        if self.freeze_frames_left > 0:
            self.freeze_frames_left -= 1

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface):
        ts = self.tile_size
        p  = BOT_PADDING
        x  = self.col * ts + p
        y  = self.row * ts + p
        w  = ts - p * 2
        h  = ts - p * 2

        color = BOT_FROZEN_COLOR if self.is_frozen() else BOT_COLOR
        rect  = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, BOT_BORDER_COLOR, rect, 2, border_radius=4)