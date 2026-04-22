"""
ui.py — Phase 4
Draws the HUD: HP bar, key counter, step counter, status panel.
All plain text + colored rectangles — no sprites yet.
"""

import pygame

# Layout
HUD_HEIGHT   = 40
HUD_BG       = (15, 15, 20)
FONT_SIZE    = 16

# HP bar
HP_BAR_W     = 120
HP_BAR_H     = 14
HP_COLOR_HI  = (60,  200, 80)
HP_COLOR_MID = (220, 180, 40)
HP_COLOR_LO  = (220,  50, 40)
HP_BG        = (50,  50,  50)

# Text colors
TEXT_COLOR   = (200, 200, 200)
KEY_COLOR    = (240, 200,  40)
STEP_COLOR   = (140, 200, 255)

STATUS_COLORS = {
    "idle":         (180, 180, 180),
    "exploring":    (100, 220, 100),
    "backtracking": (220, 160,  60),
    "found":        (255, 220,  40),
    "no_solution":  (220,  60,  60),
}

STATUS_LABELS = {
    "idle":         "Waiting...",
    "exploring":    "Exploring...",
    "backtracking": "Backtracking...",
    "found":        "Goal Found!",
    "no_solution":  "No Solution Found",
}


class HUD:
    def __init__(self, screen_w: int, screen_h: int):
        pygame.font.init()
        self.font     = pygame.font.SysFont("monospace", FONT_SIZE, bold=True)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.y        = screen_h - HUD_HEIGHT

    def draw(self, surface: pygame.Surface, player, status: str):
        # Background bar
        pygame.draw.rect(surface, HUD_BG,
                         (0, self.y, self.screen_w, HUD_HEIGHT))
        pygame.draw.line(surface, (50, 50, 60),
                         (0, self.y), (self.screen_w, self.y), 1)

        cy = self.y + HUD_HEIGHT // 2   # vertical center of HUD

        x = 10

        # --- HP bar ---
        label = self.font.render("HP", True, TEXT_COLOR)
        surface.blit(label, (x, cy - label.get_height() // 2))
        x += label.get_width() + 6

        hp_frac = max(0.0, min(1.0, player.hp / 100.0))
        if hp_frac > 0.5:
            bar_color = HP_COLOR_HI
        elif hp_frac > 0.25:
            bar_color = HP_COLOR_MID
        else:
            bar_color = HP_COLOR_LO

        bar_y = cy - HP_BAR_H // 2
        pygame.draw.rect(surface, HP_BG,
                         (x, bar_y, HP_BAR_W, HP_BAR_H))
        pygame.draw.rect(surface, bar_color,
                         (x, bar_y, int(HP_BAR_W * hp_frac), HP_BAR_H))
        pygame.draw.rect(surface, (80, 80, 80),
                         (x, bar_y, HP_BAR_W, HP_BAR_H), 1)

        hp_num = self.font.render(f"{max(0, player.hp)}", True, TEXT_COLOR)
        surface.blit(hp_num, (x + HP_BAR_W + 4, cy - hp_num.get_height() // 2))
        x += HP_BAR_W + hp_num.get_width() + 16

        # --- Key counter ---
        key_txt = self.font.render(f"Keys: {player.keys}", True, KEY_COLOR)
        surface.blit(key_txt, (x, cy - key_txt.get_height() // 2))
        x += key_txt.get_width() + 20

        # --- Step counter ---
        step_txt = self.font.render(f"Steps: {player.steps}", True, STEP_COLOR)
        surface.blit(step_txt, (x, cy - step_txt.get_height() // 2))

        # --- Status (right-aligned) ---
        slabel = STATUS_LABELS.get(status, status)
        scolor = STATUS_COLORS.get(status, TEXT_COLOR)
        stxt   = self.font.render(slabel, True, scolor)
        surface.blit(stxt, (self.screen_w - stxt.get_width() - 10,
                             cy - stxt.get_height() // 2))