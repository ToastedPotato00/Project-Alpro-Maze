"""
ui.py — Phase 6
Clean, final HUD layout:
  - HP bar (pixel art style, color-shifts green→yellow→red)
  - Key counter with icon glyph
  - Step counter
  - Status panel (right-aligned, color-coded)
  - Speed slider (left-click drag to adjust algorithm step delay)
  - Restart / Quit hint text
"""

import pygame

# ── Layout ────────────────────────────────────────────────────────────────────
HUD_HEIGHT   = 60
HUD_BG       = (12, 12, 18)
HUD_BORDER   = (40, 40, 55)
PADDING      = 10

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT_MAIN    = 16
FONT_LABEL   = 12

# ── HP bar ────────────────────────────────────────────────────────────────────
HP_BAR_W     = 100
HP_BAR_H     = 12
HP_SEGMENT_W = 4     # each segment in the pixelated bar
HP_GAP       = 1
HP_COL_HI    = (60,  210,  80)
HP_COL_MID   = (220, 180,  40)
HP_COL_LO    = (220,  50,  40)
HP_COL_BG    = (35,  35,  45)

# ── Colors ────────────────────────────────────────────────────────────────────
TEXT_COLOR   = (190, 190, 200)
LABEL_COLOR  = (100, 100, 120)
KEY_COLOR    = (240, 200,  40)
STEP_COLOR   = (120, 190, 255)
DIVIDER_COL  = (40,  40,  55)

STATUS_COLORS = {
    "idle":         (120, 120, 140),
    "exploring":    ( 80, 210,  80),
    "backtracking": (220, 150,  50),
    "found":        (255, 215,  40),
    "no_solution":  (210,  55,  55),
    "checkpoint":   (100, 220, 255),
    "candidate":    (255, 160,  40),
    "replaying":    ( 80, 210, 255),
}
STATUS_LABELS = {
    "idle":         "Waiting...",
    "exploring":    "Exploring...",
    "backtracking": "Backtracking...",
    "found":        "Goal Reached!",
    "no_solution":  "No Solution Found",
    "checkpoint":   "Checkpoint!",
    "candidate":    "Candidate found!",
    "replaying":    "Replaying best...",
}

# ── Speed slider ──────────────────────────────────────────────────────────────
SLIDER_W       = 70
SLIDER_H       = 6
SLIDER_KNOB_R  = 6
SLIDER_COL_BG  = (40, 40, 55)
SLIDER_COL_FG  = (80, 160, 255)
SLIDER_COL_KNB = (160, 210, 255)
SPEED_MIN      = 0.01   # seconds (fast)
SPEED_MAX      = 0.50   # seconds (slow)


class HUD:
    def __init__(self, screen_w: int, screen_h: int):
        pygame.font.init()
        self.font       = pygame.font.SysFont("monospace", FONT_MAIN, bold=True)
        self.font_sm    = pygame.font.SysFont("monospace", FONT_LABEL)
        self.screen_w   = screen_w
        self.screen_h   = screen_h
        self.hud_y      = screen_h - HUD_HEIGHT

        # Speed slider state (0=fast, 1=slow)
        self._slider_frac   = 0.2   # default: near fast end
        self._dragging      = False
        self._slider_rect   = None  # set on first draw

    # ── Public: query current step delay ─────────────────────────────────────
    @property
    def step_delay(self) -> float:
        return SPEED_MIN + self._slider_frac * (SPEED_MAX - SPEED_MIN)

    # ── Mouse events (call from main loop) ───────────────────────────────────
    def handle_event(self, event):
        if self._slider_rect is None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._slider_rect.collidepoint(event.pos):
                self._dragging = True
                self._update_slider(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            self._update_slider(event.pos[0])

    def _update_slider(self, mouse_x: int):
        rx = self._slider_rect.x
        rw = self._slider_rect.width
        self._slider_frac = max(0.0, min(1.0, (mouse_x - rx) / rw))

    # ── Draw ─────────────────────────────────────────────────────────────────
    def draw(self, surface: pygame.Surface, player, status: str,
             algo_label: str = "Classic DFS", score=None,
             diff_label: str = "Medium") -> tuple:
        hud_rect = pygame.Rect(0, self.hud_y, self.screen_w, HUD_HEIGHT)
        pygame.draw.rect(surface, HUD_BG, hud_rect)
        pygame.draw.line(surface, HUD_BORDER,
                         (0, self.hud_y), (self.screen_w, self.hud_y), 2)

        cy = self.hud_y + HUD_HEIGHT // 2

        # ── Zone 1: HP (anchored left) ───────────────────────────────────────
        x = PADDING
        lbl = self.font_sm.render("HP", True, LABEL_COLOR)
        surface.blit(lbl, (x, cy - lbl.get_height() // 2))
        x += lbl.get_width() + 6
        x = self._draw_hp_bar(surface, player.hp, x, cy)
        hp_txt = self.font.render(str(max(0, player.hp)), True, TEXT_COLOR)
        surface.blit(hp_txt, (x, cy - hp_txt.get_height() // 2))

        # ── Zone 2: KEYS + STEPS (fixed anchor x=185) ────────────────────────
        self._draw_divider(surface, 183, cy)
        x = 193
        k_lbl = self.font_sm.render("KEYS", True, LABEL_COLOR)
        k_val = self.font.render(str(player.keys), True, KEY_COLOR)
        surface.blit(k_lbl, (x, cy - k_lbl.get_height() // 2))
        x += k_lbl.get_width() + 5
        surface.blit(k_val, (x, cy - k_val.get_height() // 2))
        x += k_val.get_width() + PADDING * 2

        s_lbl = self.font_sm.render("STEPS", True, LABEL_COLOR)
        s_val = self.font.render(str(player.steps), True, STEP_COLOR)
        surface.blit(s_lbl, (x, cy - s_lbl.get_height() // 2))
        x += s_lbl.get_width() + 5
        surface.blit(s_val, (x, cy - s_val.get_height() // 2))

        # ── Zone 3: Speed slider (fixed anchor x=348) ────────────────────────
        self._draw_divider(surface, 346, cy)
        x = 356
        sp_lbl = self.font_sm.render("SPEED", True, LABEL_COLOR)
        surface.blit(sp_lbl, (x, cy - sp_lbl.get_height() // 2))
        x += sp_lbl.get_width() + 6
        x = self._draw_slider(surface, x, cy)

        # ── Zone 4: ALGO + DIFF dropdown trigger buttons ─────────────────────
        self._draw_divider(surface, x + 4, cy)
        btn_x  = x + 14
        abtn_w = 185
        dbtn_w = 130
        abtn_h = HUD_HEIGHT - 16
        btn_gap = 6

        algo_btn = pygame.Rect(btn_x, self.hud_y + 8, abtn_w, abtn_h)
        pygame.draw.rect(surface, (40, 40, 62), algo_btn, border_radius=6)
        pygame.draw.rect(surface, (65, 65, 92), algo_btn, 1, border_radius=6)
        al_surf  = self.font_sm.render(f"{algo_label}  ▼", True, (160, 195, 240))
        surface.blit(al_surf, al_surf.get_rect(center=algo_btn.center))

        diff_btn = pygame.Rect(btn_x + abtn_w + btn_gap, self.hud_y + 8, dbtn_w, abtn_h)
        pygame.draw.rect(surface, (40, 40, 62), diff_btn, border_radius=6)
        pygame.draw.rect(surface, (65, 65, 92), diff_btn, 1, border_radius=6)
        df_surf  = self.font_sm.render(f"{diff_label}  ▼", True, (200, 160, 240))
        surface.blit(df_surf, df_surf.get_rect(center=diff_btn.center))

        # ── Zone 5: Status + [score] + hint (right-anchored, vertically centred) ──
        slabel     = STATUS_LABELS.get(status, status)
        scolor     = STATUS_COLORS.get(status, TEXT_COLOR)
        stxt       = self.font.render(slabel, True, scolor)
        score_surf = (self.font_sm.render(f"Score: {score}", True, (200, 200, 150))
                      if score is not None else None)
        hint       = self.font_sm.render("R restart   ESC menu", True, (80, 80, 105))

        line_gap = 4
        lines    = [stxt] + ([score_surf] if score_surf else []) + [hint]
        block_h  = sum(l.get_height() for l in lines) + line_gap * (len(lines) - 1)
        block_top = self.hud_y + (HUD_HEIGHT - block_h) // 2

        max_w = max(l.get_width() for l in lines)
        pygame.draw.rect(surface, scolor,
                         (self.screen_w - max_w - PADDING - 6, block_top, 3, block_h),
                         border_radius=1)
        y = block_top
        for l in lines:
            surface.blit(l, (self.screen_w - l.get_width() - PADDING, y))
            y += l.get_height() + line_gap

        return algo_btn, diff_btn

    # ── Internal draw helpers ─────────────────────────────────────────────────

    def _draw_divider(self, surface, x, cy):
        pygame.draw.line(surface, DIVIDER_COL,
                         (x, self.hud_y + 8), (x, self.hud_y + HUD_HEIGHT - 8), 1)
        return x + PADDING

    def _draw_hp_bar(self, surface, hp: int, x: int, cy: int):
        hp_frac = max(0.0, min(1.0, hp / 100.0))

        if hp_frac > 0.5:
            bar_color = HP_COL_HI
        elif hp_frac > 0.25:
            bar_color = HP_COL_MID
        else:
            bar_color = HP_COL_LO

        bar_y = cy - HP_BAR_H // 2

        # Background
        pygame.draw.rect(surface, HP_COL_BG,
                         (x, bar_y, HP_BAR_W, HP_BAR_H), border_radius=2)

        # Segmented fill
        filled_w  = int(HP_BAR_W * hp_frac)
        seg_total = HP_SEGMENT_W + HP_GAP
        sx        = x
        while sx + HP_SEGMENT_W <= x + filled_w:
            pygame.draw.rect(surface, bar_color,
                             (sx, bar_y + 1, HP_SEGMENT_W, HP_BAR_H - 2))
            sx += seg_total

        # Outline
        pygame.draw.rect(surface, (60, 60, 75),
                         (x, bar_y, HP_BAR_W, HP_BAR_H), 1, border_radius=2)

        return x + HP_BAR_W + 5

    def _draw_slider(self, surface, x, cy):
        sw = SLIDER_W
        sh = SLIDER_H
        sy = cy - sh // 2

        track_rect = pygame.Rect(x, sy, sw, sh)
        self._slider_rect = pygame.Rect(x, cy - SLIDER_KNOB_R,
                                        sw, SLIDER_KNOB_R * 2)

        # Track background
        pygame.draw.rect(surface, SLIDER_COL_BG, track_rect, border_radius=3)

        # Filled portion (left = fast = small frac)
        filled = int(sw * self._slider_frac)
        if filled > 0:
            pygame.draw.rect(surface, SLIDER_COL_FG,
                             (x, sy, filled, sh), border_radius=3)

        # Knob
        kx = x + filled
        pygame.draw.circle(surface, SLIDER_COL_KNB, (kx, cy), SLIDER_KNOB_R)
        pygame.draw.circle(surface, (60, 100, 160), (kx, cy), SLIDER_KNOB_R, 1)

        # Endpoint tick marks instead of text labels
        pygame.draw.line(surface, LABEL_COLOR, (x, cy - 4), (x, cy + 4), 1)
        pygame.draw.line(surface, LABEL_COLOR, (x + sw, cy - 4), (x + sw, cy + 4), 1)

        return x + sw + 6