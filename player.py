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
BOT_FROZEN_COLOR = (30, 120, 160)

ANIM_TICKS_PER_FRAME = 8   # advance animation frame every 8 draw calls (~7.5 fps at 60 fps)


class Player:
    def __init__(self, row: int, col: int, tile_size: int, start_hp: int = 100):
        self.row       = row
        self.col       = col
        self.tile_size = tile_size
        self.keys      = 0
        self.hp        = start_hp
        self.steps     = 0
        self.freeze_frames_left = 0   # mud freeze countdown
        self.direction    = "down"    # last movement direction for sprite selection
        self.is_backtrack = False     # set by main.py when algorithm backtracks
        self.is_active    = False     # True while algorithm is stepping
        self.anim_frame   = 0         # current index into the active frame list
        self.anim_tick    = 0         # counts draw() calls; resets at ANIM_TICKS_PER_FRAME

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
        dr, dc = row - self.row, col - self.col
        if   dr < 0: self.direction = "up"
        elif dr > 0: self.direction = "down"
        elif dc < 0: self.direction = "left"
        elif dc > 0: self.direction = "right"
        self.row = row
        self.col = col

    def is_frozen(self) -> bool:
        return self.freeze_frames_left > 0

    def tick_freeze(self):
        if self.freeze_frames_left > 0:
            self.freeze_frames_left -= 1

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, sprites: dict = None, offset: tuple = (0, 0)):
        ts     = self.tile_size
        ox, oy = offset

        if sprites is not None:
            bot = sprites.get("bot", {})

            # Select animation set and horizontal flip
            if self.is_frozen():
                frames = bot.get("hit") or bot.get("idle")
                flip_x = False
            elif self.is_active:
                frames = bot.get("run") or bot.get("idle")
                # XOR: forward=face direction, backtrack=face opposite
                flip_x = (self.direction == "left") ^ self.is_backtrack
            else:
                frames = bot.get("idle") or bot.get("run")
                flip_x = (self.direction == "left")

            if frames:
                self.anim_tick += 1
                if self.anim_tick >= ANIM_TICKS_PER_FRAME:
                    self.anim_tick  = 0
                    self.anim_frame = (self.anim_frame + 1) % len(frames)

                frame = frames[self.anim_frame % len(frames)]
                if flip_x:
                    frame = pygame.transform.flip(frame, True, False)
                surface.blit(frame, (self.col * ts + ox, self.row * ts + oy))
                return

        # Fallback: colored rounded rect
        p     = BOT_PADDING
        x     = self.col * ts + ox + p
        y     = self.row * ts + oy + p
        w     = ts - p * 2
        h     = ts - p * 2
        color = BOT_FROZEN_COLOR if self.is_frozen() else BOT_COLOR
        rect  = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, color, rect, border_radius=4)
        pygame.draw.rect(surface, BOT_BORDER_COLOR, rect, 2, border_radius=4)