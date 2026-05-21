"""
main.py — with start screen and Map Editor button
"""

import math
import os
import pygame
import sys
import time
import copy

from map_loader    import load_map, find_tile
from map_renderer  import MapRenderer
from player        import Player
from algorithm     import backtracking_backtrack, backtracking_chained, backtracking_optimize
from ui            import HUD, HUD_HEIGHT
from map_editor    import run_editor
from sprite_loader import load_sprites
from tiles         import DIFF_CONFIGS
from sound_manager import SoundManager

WINDOW_TITLE = "MazeCrawler"
SCREEN_W     = 1440
SCREEN_H     = 700
FPS          = 120

MENU_BG_MAP      = "assets/Bg.txt"        # swap filename to change start screen background
MAP_SELECT_BG    = "assets/bg.png"   # background image for map picker (leave blank path to use solid colour)

TRAIL_COLOR  = (80,  160, 255)
TRAIL_ALPHA  = 55
BT_ALPHA     = 30

# ── Colours ───────────────────────────────────────────────────────────────────
BG         = (18,  18,  24)
TEXT       = (200, 200, 210)
TEXT_DIM   = (100, 100, 120)
BTN_BG     = (35,  35,  50)
BTN_HOV    = (50,  50,  75)
BTN_ACT    = (60,  120, 200)
ACCENT_HOV = (110, 185, 255)
BORDER     = (50,  50,  70)

# ── Dungeon Gold palette (shared across all menu screens) ─────────────────────
DG_BG       = (20,  15,  10)
DG_TEXT     = (235, 210, 140)
DG_TEXT_DIM = (130, 100,  55)
DG_BTN_BG   = (38,  28,  18)
DG_BTN_HOV  = (62,  46,  26)
DG_PLAY_BG  = (130,  90,  22)
DG_PLAY_HOV = (168, 120,  38)
DG_BORDER   = (120,  85,  25)


# ── Simple button (local, avoids circular import) ─────────────────────────────
class Btn:
    def __init__(self, rect, label, font,
                 color=BTN_BG, hover=BTN_HOV, tc=TEXT, border_color=None, pop=False):
        self.rect         = pygame.Rect(rect)
        self.label        = label
        self.font         = font
        self.color        = color
        self.hover        = hover
        self.tc           = tc
        self.border_color = border_color if border_color is not None else BORDER
        self.pop          = pop
        self._hov         = False

    def update(self, mp): self._hov = self.rect.collidepoint(mp)

    def draw(self, s):
        draw_rect = self.rect.inflate(12, 8) if (self._hov and self.pop) else self.rect
        pygame.draw.rect(s, self.hover if self._hov else self.color,
                         draw_rect, border_radius=8)
        pygame.draw.rect(s, self.border_color, draw_rect, 1, border_radius=8)
        lbl = self.font.render(self.label, True, self.tc)
        s.blit(lbl, lbl.get_rect(center=draw_rect.center))

    def clicked(self, e):
        return (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                and self.rect.collidepoint(e.pos))


# ── Algorithm picker ─────────────────────────────────────────────────────────
ALGOS = [
    ("classic",  "Classic Backtracking",  "First valid path"),
    ("chained",  "Chained Backtracking",  "All goals in sequence"),
    ("optimize", "Optimize Backtracking", "Best scored path"),
]
ALGO_LABELS = {k: name for k, name, _ in ALGOS}

# ── Difficulty picker ─────────────────────────────────────────────────────────
DIFFS = [
    ("easy",     "Easy",     "Half penalty"),
    ("medium",   "Medium",   "Default"),
    ("hard",     "Hard",     "x1.5 penalty"),
    ("hardcore", "Hardcore", "Start 1 HP, x2 penalty"),
]
DIFF_LABELS = {k: name for k, name, _ in DIFFS}

# ── Speed picker ──────────────────────────────────────────────────────────────
SPEEDS = [
    ("fast",   "Fast",   "0.01s / step",  0.01),
    ("normal", "Normal", "0.25s / step",  0.25),
    ("slow",   "Slow",   "0.50s / step",  0.50),
]
SPEED_DELAYS = {k: d for k, _, _, d in SPEEDS}
SPEED_LABELS = {k: n for k, n, _, _ in SPEEDS}


class AlgoDropdown:
    PANEL_W = 230
    ROW_H   = 44

    def __init__(self, default):
        pygame.font.init()
        self.current  = default
        self.open     = False
        self._pending = None
        self._panel   = None
        self._fn      = pygame.font.SysFont("monospace", 13, bold=True)
        self._fs      = pygame.font.SysFont("monospace", 11)

    @property
    def label(self):
        return ALGO_LABELS.get(self.current, self.current)

    @property
    def pending_algo(self):
        return self._pending is not None

    def consume(self):
        a, self._pending = self._pending, None
        return a

    def handle_event(self, event, btn_rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if btn_rect and btn_rect.collidepoint(pos):
            self.open = not self.open
            return True
        if self.open and self._panel and self._panel.collidepoint(pos):
            idx = (pos[1] - self._panel.y) // self.ROW_H
            if 0 <= idx < len(ALGOS):
                key = ALGOS[idx][0]
                if key != self.current:
                    self.current  = key
                    self._pending = key
                self.open = False
            return True
        if self.open:
            self.open = False
        return False

    def draw(self, surface, btn_rect):
        if not self.open:
            self._panel = None
            return
        ph = len(ALGOS) * self.ROW_H
        px = btn_rect.x
        py = btn_rect.y - ph - 4
        self._panel = pygame.Rect(px, py, self.PANEL_W, ph)
        pygame.draw.rect(surface, (18, 18, 28), self._panel, border_radius=8)
        pygame.draw.rect(surface, (60, 60, 85), self._panel, 1, border_radius=8)
        mp = pygame.mouse.get_pos()
        for i, (key, name, desc) in enumerate(ALGOS):
            rr       = pygame.Rect(px, py + i * self.ROW_H, self.PANEL_W, self.ROW_H)
            active   = (key == self.current)
            if active:
                pygame.draw.rect(surface, (45, 90, 175), rr, border_radius=4)
            elif rr.collidepoint(mp):
                pygame.draw.rect(surface, (35, 35, 58), rr, border_radius=4)
            nc = (255,255,255) if active else (185,185,205)
            dc = (160,200,255) if active else (95,95,115)
            ds = desc
            surface.blit(self._fn.render(name, True, nc),
                         (px + 10, py + i * self.ROW_H + 5))
            surface.blit(self._fs.render(ds,   True, dc),
                         (px + 10, py + i * self.ROW_H + 23))


# ── Difficulty dropdown ───────────────────────────────────────────────────────
class DiffDropdown:
    PANEL_W = 210
    ROW_H   = 44

    def __init__(self, default="medium"):
        pygame.font.init()
        self.current  = default
        self.open     = False
        self._pending = None
        self._panel   = None
        self._fn      = pygame.font.SysFont("monospace", 13, bold=True)
        self._fs      = pygame.font.SysFont("monospace", 11)

    @property
    def label(self):
        return DIFF_LABELS.get(self.current, self.current)

    @property
    def pending_diff(self):
        return self._pending is not None

    def consume(self):
        d, self._pending = self._pending, None
        return d

    def handle_event(self, event, btn_rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if btn_rect and btn_rect.collidepoint(pos):
            self.open = not self.open
            return True
        if self.open and self._panel and self._panel.collidepoint(pos):
            idx = (pos[1] - self._panel.y) // self.ROW_H
            if 0 <= idx < len(DIFFS):
                key = DIFFS[idx][0]
                if key != self.current:
                    self.current  = key
                    self._pending = key
                self.open = False
            return True
        if self.open:
            self.open = False
        return False

    def draw(self, surface, btn_rect):
        if not self.open:
            self._panel = None
            return
        ph = len(DIFFS) * self.ROW_H
        px = btn_rect.x
        py = btn_rect.y - ph - 4
        self._panel = pygame.Rect(px, py, self.PANEL_W, ph)
        pygame.draw.rect(surface, (18, 18, 28), self._panel, border_radius=8)
        pygame.draw.rect(surface, (60, 60, 85), self._panel, 1, border_radius=8)
        mp = pygame.mouse.get_pos()
        for i, (key, name, desc) in enumerate(DIFFS):
            rr     = pygame.Rect(px, py + i * self.ROW_H, self.PANEL_W, self.ROW_H)
            active = (key == self.current)
            if active:
                pygame.draw.rect(surface, (90, 45, 175), rr, border_radius=4)
            elif rr.collidepoint(mp):
                pygame.draw.rect(surface, (35, 35, 58), rr, border_radius=4)
            nc = (255, 255, 255) if active else (185, 185, 205)
            dc = (200, 160, 255) if active else (95,  95,  115)
            surface.blit(self._fn.render(name, True, nc),
                         (px + 10, py + i * self.ROW_H + 5))
            surface.blit(self._fs.render(desc, True, dc),
                         (px + 10, py + i * self.ROW_H + 23))


# ── Speed dropdown ────────────────────────────────────────────────────────────
class SpeedDropdown:
    PANEL_W = 190
    ROW_H   = 44

    def __init__(self, default="normal"):
        pygame.font.init()
        self.current = default
        self.open    = False
        self._panel  = None
        self._fn     = pygame.font.SysFont("monospace", 13, bold=True)
        self._fs     = pygame.font.SysFont("monospace", 11)

    @property
    def label(self):
        return SPEED_LABELS.get(self.current, self.current)

    @property
    def delay(self):
        return SPEED_DELAYS.get(self.current, 0.25)

    def handle_event(self, event, btn_rect):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False
        pos = event.pos
        if btn_rect and btn_rect.collidepoint(pos):
            self.open = not self.open
            return True
        if self.open and self._panel and self._panel.collidepoint(pos):
            idx = (pos[1] - self._panel.y) // self.ROW_H
            if 0 <= idx < len(SPEEDS):
                self.current = SPEEDS[idx][0]
                self.open    = False
            return True
        if self.open:
            self.open = False
        return False

    def draw(self, surface, btn_rect):
        if not self.open:
            self._panel = None
            return
        ph = len(SPEEDS) * self.ROW_H
        px = btn_rect.x
        py = btn_rect.y - ph - 4
        self._panel = pygame.Rect(px, py, self.PANEL_W, ph)
        pygame.draw.rect(surface, (18, 18, 28), self._panel, border_radius=8)
        pygame.draw.rect(surface, (60, 60, 85), self._panel, 1, border_radius=8)
        mp = pygame.mouse.get_pos()
        for i, (key, name, desc, _) in enumerate(SPEEDS):
            rr     = pygame.Rect(px, py + i * self.ROW_H, self.PANEL_W, self.ROW_H)
            active = (key == self.current)
            if active:
                pygame.draw.rect(surface, (45, 140, 90), rr, border_radius=4)
            elif rr.collidepoint(mp):
                pygame.draw.rect(surface, (35, 35, 58), rr, border_radius=4)
            nc = (255, 255, 255) if active else (185, 185, 205)
            dc = (160, 255, 200) if active else (95,  95,  115)
            surface.blit(self._fn.render(name, True, nc),
                         (px + 10, py + i * self.ROW_H + 5))
            surface.blit(self._fs.render(desc, True, dc),
                         (px + 10, py + i * self.ROW_H + 23))


# ── Start / map-select screen ─────────────────────────────────────────────────
def start_screen(screen):
    pygame.font.init()
    font_lg = pygame.font.Font("assets/font.ttf", 64)
    font_md = pygame.font.Font("assets/font.ttf", 22)
    clock   = pygame.time.Clock()

    # ── Compute window size from map (fit by height, width follows) ──────────
    try:
        grid_master_bg, _ = load_map(MENU_BG_MAP)
        _bg_ok = True
    except Exception:
        grid_master_bg = None
        _bg_ok = False

    if _bg_ok:
        _bg_cols = len(grid_master_bg[0])
        _bg_rows = len(grid_master_bg)
        ts_bg    = max(ZOOM_MIN, min(ZOOM_MAX, SCREEN_H // _bg_rows))
        menu_w   = _bg_cols * ts_bg
        menu_h   = SCREEN_H
    else:
        ts_bg  = None
        menu_w = SCREEN_W
        menu_h = SCREEN_H

    screen = pygame.display.set_mode((menu_w, menu_h))
    cx     = menu_w // 2

    BG_STEP_DELAY = 0.10
    _bg = {}

    def reset_bg():
        if not _bg_ok:
            return
        grid   = copy.deepcopy(grid_master_bg)
        starts = find_tile(grid, "S")
        goals  = find_tile(grid, "G")
        sp = starts[0] if starts else (1, 1)
        gp = goals[0]  if goals  else (_bg_rows - 2, _bg_cols - 2)
        player   = Player(sp[0], sp[1], ts_bg)
        sprites  = load_sprites(ts_bg)
        renderer = MapRenderer(grid, ts_bg, sprites=sprites)
        gen      = backtracking_backtrack(grid, player, sp, gp)
        world_h  = _bg_rows * ts_bg
        cam_y    = -(menu_h - world_h) // 2 if world_h <= menu_h else 0
        _bg.update(
            grid=grid, player=player, sprites=sprites,
            renderer=renderer, gen=gen,
            offset=(0, -cam_y), last_step=time.time(),
        )

    reset_bg()

    overlay = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 145))

    # ── Title — per-character for wave animation ─────────────────────────────
    TITLE_TEXT  = "MazeCrawler"
    TITLE_COLOR = (235, 210, 140)
    char_surfs  = [font_lg.render(ch, True, TITLE_COLOR) for ch in TITLE_TEXT]
    char_widths = [s.get_width() for s in char_surfs]
    char_h      = char_surfs[0].get_height()
    t_scale     = 0.0
    t_vel       = 0.0

    # Burst constants
    BURST_CYCLE   = 2.5   # seconds per full cycle (motion + rest)
    BURST_FRAC    = 0.15  # fraction of cycle that is active (≈0.375s of motion)
    BURST_STAGGER = 0.04  # cycle-fraction offset between adjacent letters
    BURST_AMP     = 9     # pixels of upward travel

    # ── Button layout ────────────────────────────────────────────────────────
    BTN_W, BTN_H, BTN_GAP = 280, 58, 14
    TITLE_TO_BTNS          = 32
    total_btns_h           = 3 * BTN_H + 2 * BTN_GAP
    block_h                = char_h + TITLE_TO_BTNS + total_btns_h
    block_top              = (menu_h - block_h) // 2
    title_cy               = block_top + char_h // 2
    btns_top               = block_top + char_h + TITLE_TO_BTNS

    BTN_DEFS = ["Play", "Map Editor", "Quit"]
    btn_offsets = [-float(menu_h)] * 3
    btn_started = [False] * 3
    btn_done    = [False] * 3
    BTN_STAGGER = 0.75   # seconds between each button starting to drop in

    btns = [
        Btn((cx - BTN_W // 2, 0, BTN_W, BTN_H), lbl, font_md,
            color=DG_BTN_BG, hover=DG_PLAY_HOV, tc=DG_TEXT,
            border_color=DG_BORDER, pop=True)
        for lbl in BTN_DEFS
    ]

    title_settled  = False
    title_settle_t = None

    while True:
        now = time.time()
        mp  = pygame.mouse.get_pos()

        for i, b in enumerate(btns):
            b.rect.y = btns_top + i * (BTN_H + BTN_GAP) + int(btn_offsets[i])
        for b in btns:
            b.update(mp)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "quit"
            if btns[0].clicked(event): return "play"
            if btns[1].clicked(event): return "editor"
            if btns[2].clicked(event): return "quit"

        # ── Advance background bot ───────────────────────────────────────────
        if _bg_ok and _bg and now - _bg["last_step"] >= BG_STEP_DELAY:
            try:
                kind, r, c, extra = next(_bg["gen"])
                _bg["last_step"] = now
                p = _bg["player"]
                if kind == "move":
                    p.is_active    = True
                    p.is_backtrack = False
                    _bg["renderer"].update_grid(_bg["grid"])
                elif kind == "backtrack":
                    p.is_active    = True
                    p.is_backtrack = True
                    _bg["renderer"].update_grid(_bg["grid"])
                elif kind in ("replay_start", "replay"):
                    p.is_active    = True
                    p.is_backtrack = False
                    _bg["renderer"].update_grid(_bg["grid"])
                elif kind in ("found", "no_solution"):
                    reset_bg()
            except StopIteration:
                reset_bg()

        # ── Spring title animation (slow ease-out pop) ───────────────────────
        if t_scale < 0.999:
            t_vel   = t_vel * 0.2 + (1.0 - t_scale) * 0.045
            t_scale = min(1.0, t_scale + t_vel)
        if t_scale >= 0.999 and not title_settled:
            t_scale        = 1.0
            title_settled  = True
            title_settle_t = now

        # ── Button sequential drop-in ────────────────────────────────────────
        if title_settled:
            for i in range(3):
                if now - title_settle_t >= i * BTN_STAGGER:
                    btn_started[i] = True
                if btn_started[i] and not btn_done[i]:
                    btn_offsets[i] *= 0.86   # slow ease-out toward 0
                    if abs(btn_offsets[i]) < 1.0:
                        btn_offsets[i] = 0.0
                        btn_done[i]    = True

        # ── Draw ─────────────────────────────────────────────────────────────
        screen.fill(BG)

        if _bg_ok and _bg:
            _bg["renderer"].draw(screen, pygame.time.get_ticks(),
                                 offset=_bg["offset"])
            _bg["player"].draw(screen, _bg["sprites"], offset=_bg["offset"])

        screen.blit(overlay, (0, 0))

        if t_scale > 0.01:
            scaled_ws = [max(1, int(w * t_scale)) for w in char_widths]
            scaled_h  = max(1, int(char_h * t_scale))
            total_w   = sum(scaled_ws)
            x         = cx - total_w // 2
            for i, (surf, sw) in enumerate(zip(char_surfs, scaled_ws)):
                s = pygame.transform.smoothscale(surf, (sw, scaled_h)) if t_scale < 1.0 else surf
                if title_settled:
                    t_norm = (now / BURST_CYCLE - i * BURST_STAGGER) % 1.0
                    y_wave = -int(math.sin(t_norm / BURST_FRAC * math.pi) * BURST_AMP) if t_norm < BURST_FRAC else 0
                else:
                    y_wave = 0
                screen.blit(s, (x, title_cy - scaled_h // 2 + y_wave))
                x += sw

        for i, b in enumerate(btns):
            if btn_started[i]:
                b.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


# ── Map selection screen ──────────────────────────────────────────────────────
def map_select_screen(screen):
    pygame.font.init()
    font_lg = pygame.font.Font("assets/font.ttf", 48)
    font_md = pygame.font.Font("assets/font.ttf", 22)
    font_sm = pygame.font.Font("assets/font.ttf", 16)
    clock   = pygame.time.Clock()
    cx      = SCREEN_W // 2

    # ── Background image (scales to screen, falls back to solid colour) ────────
    _bg_img = None
    try:
        _raw    = pygame.image.load(MAP_SELECT_BG).convert()
        _full   = pygame.transform.smoothscale(_raw, (SCREEN_W, SCREEN_H))
        _small  = pygame.transform.smoothscale(_full, (SCREEN_W // 8, SCREEN_H // 8))
        _bg_img = pygame.transform.smoothscale(_small, (SCREEN_W, SCREEN_H))
    except Exception:
        pass

    maps = sorted(f for f in os.listdir("maps") if f.endswith(".txt"))

    def label(filename):
        stem = filename[:-4]
        return stem.replace("_", " ").title()

    btn_h, btn_gap = 54, 10
    back_h, back_gap = 48, 18
    n = len(maps)

    TITLE_H      = 52
    SUB_H        = 20
    TITLE_TO_SUB = 12
    SUB_TO_BTNS  = 22

    btns_block_h = n * btn_h + max(0, n - 1) * btn_gap if n else 0
    total_h      = TITLE_H + TITLE_TO_SUB + SUB_H + SUB_TO_BTNS + btns_block_h + back_gap + back_h
    block_top    = (SCREEN_H - total_h) // 2

    title_y = block_top
    sub_y   = block_top + TITLE_H + TITLE_TO_SUB
    start_y = block_top + TITLE_H + TITLE_TO_SUB + SUB_H + SUB_TO_BTNS

    map_btns = [
        Btn((cx - 140, start_y + i * (btn_h + btn_gap), 280, btn_h),
            label(m), font_md,
            color=DG_BTN_BG, hover=DG_BTN_HOV, tc=DG_TEXT,
            border_color=DG_BORDER, pop=True)
        for i, m in enumerate(maps)
    ]
    back_y   = start_y + btns_block_h + back_gap
    btn_back = Btn((cx - 100, back_y, 200, back_h), "← Back", font_md,
                   color=DG_BTN_BG, hover=DG_BTN_HOV, tc=DG_TEXT,
                   border_color=DG_BORDER)

    while True:
        mp = pygame.mouse.get_pos()
        for b in map_btns:
            b.update(mp)
        btn_back.update(mp)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
            if btn_back.clicked(event):
                return None
            for i, b in enumerate(map_btns):
                if b.clicked(event):
                    return f"maps/{maps[i]}"

        if _bg_img:
            screen.blit(_bg_img, (0, 0))
        else:
            screen.fill(DG_BG)
        title = font_lg.render("Select a Map", True, DG_TEXT)
        screen.blit(title, title.get_rect(centerx=cx, y=title_y))

        if maps:
            for b in map_btns:
                b.draw(screen)
        else:
            msg = font_sm.render("No maps found in /maps/", True, DG_TEXT_DIM)
            screen.blit(msg, msg.get_rect(centerx=cx, y=500))

        btn_back.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


# ── Results overlay ───────────────────────────────────────────────────────────
def draw_results_overlay(surface, status, player, visited_cells,
                         backtrack_count, paths_explored, best_score,
                         screen_w, screen_h):
    font_lg = pygame.font.SysFont("monospace", 28, bold=True)
    font_md = pygame.font.SysFont("monospace", 16, bold=True)
    font_sm = pygame.font.SysFont("monospace", 13)

    backdrop = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
    backdrop.fill((0, 0, 0, 170))
    surface.blit(backdrop, (0, 0))

    stats = [
        ("Steps Taken",   str(player.steps),          (120, 190, 255)),
        ("HP Remaining",  str(max(0, player.hp)),      ( 60, 210,  80)),
        ("Keys Held",     str(player.keys),            (240, 200,  40)),
        ("Cells Visited", str(len(visited_cells)),     (160, 160, 200)),
        ("Backtracks",    str(backtrack_count),        (220, 150,  50)),
    ]
    if paths_explored > 0:
        stats.append(("Paths Explored", str(paths_explored), (255, 160, 40)))
    if best_score is not None:
        stats.append(("Best Score",     str(best_score),      (255, 215, 40)))

    row_h   = 36
    panel_w = 420
    panel_h = 72 + len(stats) * row_h + 52  # title block + rows + divider+hint

    px = (screen_w - panel_w) // 2
    py = (screen_h - panel_h) // 2

    if status == "found":
        border_col = (255, 215,  40)
        title_text = "Goal Reached!"
        title_col  = (255, 215,  40)
    else:
        border_col = (210,  55,  55)
        title_text = "No Solution Found"
        title_col  = (210,  55,  55)

    pygame.draw.rect(surface, (18, 18, 30), (px, py, panel_w, panel_h), border_radius=14)
    pygame.draw.rect(surface, border_col,   (px, py, panel_w, panel_h), 2, border_radius=14)

    t_surf = font_lg.render(title_text, True, title_col)
    surface.blit(t_surf, t_surf.get_rect(centerx=px + panel_w // 2, y=py + 18))

    sep_y = py + 60
    pygame.draw.line(surface, (50, 50, 72), (px + 20, sep_y), (px + panel_w - 20, sep_y), 1)

    y = sep_y + 10
    for label, value, color in stats:
        lbl_s = font_sm.render(label, True, (115, 115, 140))
        val_s = font_md.render(value, True, color)
        surface.blit(lbl_s, (px + 28,  y + (row_h - lbl_s.get_height()) // 2))
        surface.blit(val_s, (px + panel_w - 28 - val_s.get_width(),
                             y + (row_h - val_s.get_height()) // 2))
        y += row_h

    pygame.draw.line(surface, (50, 50, 72), (px + 20, y + 4), (px + panel_w - 20, y + 4), 1)
    hint = font_sm.render("Click to dismiss   R restart   ESC menu", True, (75, 75, 108))
    surface.blit(hint, hint.get_rect(centerx=px + panel_w // 2, y=y + 14))


# ── Game helpers ──────────────────────────────────────────────────────────────
def _play_tile_sound(sounds, extra):
    if extra.get("key_picked_up"):   sounds.play("key_pickup")
    elif extra.get("teleported_to"): sounds.play("teleport")
    elif extra.get("freeze_frames"): sounds.play("mud")
    elif extra.get("fire_damage"):   sounds.play("fire")
    elif extra.get("regen_heal"):    sounds.play("regen")
    elif extra.get("wall_broken"):   sounds.play("wall_break")
    else:                            sounds.play("step")


def make_overlay(tile_size, r, g, b, a):
    s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    s.fill((r, g, b, a))
    return s


def build_run(grid_master, tile_size, algo, diff="medium"):
    cfg    = DIFF_CONFIGS[diff]
    grid   = copy.deepcopy(grid_master)
    starts = find_tile(grid, "S")
    goals  = find_tile(grid, "G")
    start  = starts[0] if starts else (1, 1)
    if not goals:
        goals = [(len(grid)-2, len(grid[0])-2)]
    player = Player(start[0], start[1], tile_size, start_hp=cfg["start_hp"])
    if algo == "chained":
        gen = backtracking_chained(grid, player, start, goals, diff=cfg)
    elif algo == "optimize":
        gen = backtracking_optimize(grid, player, start, goals[0], diff=cfg)
    else:
        gen = backtracking_backtrack(grid, player, start, goals[0], diff=cfg)
    return grid, player, gen, goals


ZOOM_MIN  = 8
ZOOM_MAX  = 80
ZOOM_STEP = 4


def _camera(player_col, player_row, ts, cols, rows):
    """Camera top-left in world pixels.
    Small maps (fit in viewport) are centred; large maps follow the player."""
    area_h  = SCREEN_H - HUD_HEIGHT
    world_w = cols * ts
    world_h = rows * ts

    if world_w <= SCREEN_W:
        cx = -(SCREEN_W - world_w) // 2   # negative → positive draw offset → centred
    else:
        cx = player_col * ts + ts // 2 - SCREEN_W // 2
        cx = max(0, min(cx, world_w - SCREEN_W))

    if world_h <= area_h:
        cy = -(area_h - world_h) // 2
    else:
        cy = player_row * ts + ts // 2 - area_h // 2
        cy = max(0, min(cy, world_h - area_h))

    return cx, cy


# ── Game loop ─────────────────────────────────────────────────────────────────
def run_game(screen, map_path, sounds=None):
    grid_master, _ = load_map(map_path)
    cols = len(grid_master[0])
    rows = len(grid_master)

    # Auto-fit: choose ts so the map fills the fixed window as much as possible
    area_h = SCREEN_H - HUD_HEIGHT
    ts_fit = min(SCREEN_W // cols, area_h // rows)
    ts     = max(ZOOM_MIN, min(ZOOM_MAX, ts_fit))

    game_screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    sprites    = load_sprites(ts)
    if sounds is None:
        sounds = SoundManager()
    trail_surf = make_overlay(ts, *TRAIL_COLOR, TRAIL_ALPHA)
    bt_surf    = make_overlay(ts, 255, 120, 60, BT_ALPHA)
    gold_surf  = make_overlay(ts, 255, 215, 40, 110)

    # Default algo: map3 filename → optimize, multi-goal → chained, else classic
    goals_init = find_tile(grid_master, "G")
    if "map3" in os.path.basename(map_path).lower():
        algo = "optimize"
    elif len(goals_init) > 1:
        algo = "chained"
    else:
        algo = "classic"
    dropdown      = AlgoDropdown(algo)
    diff          = "medium"
    diff_dropdown = DiffDropdown(diff)
    speed_dd      = SpeedDropdown("normal")
    algo_btn_rect  = None
    diff_btn_rect  = None
    speed_btn_rect = None

    grid, player, gen, goals = build_run(grid_master, ts, algo, diff)
    renderer = MapRenderer(grid, ts, sprites=sprites)
    hud      = HUD(SCREEN_W, SCREEN_H)

    visited_cells    = {(player.row, player.col)}
    backtrack_cells  = set()
    solution_path    = [(player.row, player.col)]
    active_goal_idx  = 0
    best_score       = None
    backtrack_count  = 0
    paths_explored   = 0
    status       = "idle"
    finished     = False
    show_overlay = False
    last_step    = time.time()

    while True:
        now             = time.time()
        cam_x, cam_y   = _camera(player.col, player.row, ts, cols, rows)
        offset          = (-cam_x, -cam_y)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and finished and show_overlay):
                show_overlay = False
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if dropdown.open or diff_dropdown.open or speed_dd.open:
                        dropdown.open      = False
                        diff_dropdown.open = False
                        speed_dd.open      = False
                    else:
                        return "menu"
                if event.key == pygame.K_r and not dropdown.open and not diff_dropdown.open and not speed_dd.open:
                    grid, player, gen, goals = build_run(grid_master, ts, algo, diff)
                    renderer.update_grid(grid)
                    visited_cells   = {(player.row, player.col)}
                    backtrack_cells = set()
                    solution_path   = [(player.row, player.col)]
                    active_goal_idx = 0
                    best_score      = None
                    backtrack_count = 0
                    paths_explored  = 0
                    status       = "idle"
                    finished     = False
                    show_overlay = False
                    last_step    = now
            if event.type == pygame.MOUSEWHEEL:
                new_ts = max(ZOOM_MIN, min(ZOOM_MAX, ts + event.y * ZOOM_STEP))
                if new_ts != ts:
                    ts = new_ts
                    player.tile_size = ts
                    renderer.set_tile_size(ts)
                    sprites    = load_sprites(ts)
                    renderer.sprites = sprites
                    trail_surf = make_overlay(ts, *TRAIL_COLOR, TRAIL_ALPHA)
                    bt_surf    = make_overlay(ts, 255, 120, 60, BT_ALPHA)
                    gold_surf  = make_overlay(ts, 255, 215, 40, 110)
            if not dropdown.handle_event(event, algo_btn_rect):
                if not diff_dropdown.handle_event(event, diff_btn_rect):
                    speed_dd.handle_event(event, speed_btn_rect)

        if dropdown.pending_algo:
            algo = dropdown.consume()
            grid, player, gen, goals = build_run(grid_master, ts, algo, diff)
            renderer.update_grid(grid)
            visited_cells   = {(player.row, player.col)}
            backtrack_cells = set()
            solution_path   = [(player.row, player.col)]
            active_goal_idx = 0
            best_score      = None
            backtrack_count = 0
            paths_explored  = 0
            status       = "idle"
            finished     = False
            show_overlay = False
            last_step    = now

        if diff_dropdown.pending_diff:
            diff = diff_dropdown.consume()
            grid, player, gen, goals = build_run(grid_master, ts, algo, diff)
            renderer.update_grid(grid)
            visited_cells   = {(player.row, player.col)}
            backtrack_cells = set()
            solution_path   = [(player.row, player.col)]
            active_goal_idx = 0
            best_score      = None
            backtrack_count = 0
            paths_explored  = 0
            status       = "idle"
            finished     = False
            show_overlay = False
            last_step    = now

        if player.is_frozen():
            player.tick_freeze()
            time.sleep(0.12)

        if not finished and not player.is_frozen():
            delay = speed_dd.delay * (0.5 if status == "backtracking" else 1.0)
            if now - last_step >= delay:
                try:
                    kind, r, c, extra = next(gen)
                    last_step = time.time()
                    if kind == "move":
                        status = "exploring"
                        player.is_active    = True
                        player.is_backtrack = False
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                        solution_path.append((r, c))
                        renderer.update_grid(grid)
                        if extra.get("freeze_frames", 0) > 0:
                            player.freeze_frames_left = extra["freeze_frames"]
                        _play_tile_sound(sounds, extra)
                    elif kind == "backtrack":
                        status = "backtracking"
                        player.is_active    = True
                        player.is_backtrack = True
                        backtrack_cells.add((r, c))
                        if len(solution_path) > 1:
                            solution_path.pop()
                        backtrack_count += 1
                        renderer.update_grid(grid)
                    elif kind == "segment_found":
                        active_goal_idx += 1
                        status = "checkpoint"
                        player.is_active    = True
                        player.is_backtrack = False
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                        sounds.play("goal")
                    elif kind == "candidate":
                        status = "candidate"
                        paths_explored += 1
                        if extra.get("is_best"):
                            best_score = extra["score"]
                    elif kind == "replay_start":
                        status = "replaying"
                        best_score      = extra.get("score")
                        visited_cells   = {(r, c)}
                        backtrack_cells = set()
                        solution_path   = [(r, c)]
                        player.is_active    = True
                        player.is_backtrack = False
                        renderer.update_grid(grid)
                    elif kind == "replay":
                        status = "replaying"
                        player.is_active    = True
                        player.is_backtrack = False
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                        solution_path.append((r, c))
                        renderer.update_grid(grid)
                        if extra.get("freeze_frames", 0) > 0:
                            player.freeze_frames_left = extra["freeze_frames"]
                        _play_tile_sound(sounds, extra)
                    elif kind == "found":
                        status = "found"
                        player.is_active    = False
                        player.is_backtrack = False
                        if extra.get("score") is not None:
                            best_score = extra["score"]
                        sounds.play("goal")
                        finished     = True
                        show_overlay = True
                    elif kind == "no_solution":
                        status = "no_solution"
                        player.is_active = False
                        finished     = True
                        show_overlay = True
                except StopIteration:
                    if status not in ("found", "no_solution"):
                        status = "no_solution"
                    finished     = True
                    show_overlay = True

        game_screen.fill((0, 0, 0))

        # Clip all tile/trail/player drawing to the game area (above HUD)
        game_area_h = SCREEN_H - HUD_HEIGHT
        game_screen.set_clip(pygame.Rect(0, 0, SCREEN_W, game_area_h))

        renderer.draw(game_screen, pygame.time.get_ticks(), offset=offset)

        for (vr, vc) in visited_cells:
            game_screen.blit(trail_surf, (vc * ts - cam_x, vr * ts - cam_y))
        for (vr, vc) in backtrack_cells:
            game_screen.blit(bt_surf, (vc * ts - cam_x, vr * ts - cam_y))

        if status in ("found", "replaying"):
            for (vr, vc) in solution_path:
                game_screen.blit(gold_surf, (vc * ts - cam_x, vr * ts - cam_y))

        player.draw(game_screen, sprites, offset=offset)

        pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500
        for gi, g in enumerate(goals):
            gx = g[1] * ts - cam_x
            gy = g[0] * ts - cam_y
            if gi == active_goal_idx:
                pygame.draw.rect(game_screen, (255, 215, 40),
                                 (gx, gy, ts, ts), max(1, int(1 + pulse * 3)))
            elif gi > active_goal_idx:
                pygame.draw.rect(game_screen, (180, 150, 40),
                                 (gx, gy, ts, ts), 1)

        game_screen.set_clip(None)
        algo_btn_rect, diff_btn_rect, speed_btn_rect = hud.draw(
            game_screen, player, status, dropdown.label,
            score=best_score, diff_label=diff_dropdown.label,
            speed_label=speed_dd.label)
        dropdown.draw(game_screen, algo_btn_rect)
        diff_dropdown.draw(game_screen, diff_btn_rect)
        speed_dd.draw(game_screen, speed_btn_rect)

        if finished and show_overlay:
            draw_results_overlay(game_screen, status, player, visited_cells,
                                 backtrack_count, paths_explored, best_score,
                                 SCREEN_W, SCREEN_H)

        pygame.display.flip()
        clock.tick(FPS)


# ── Entry ─────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(WINDOW_TITLE)

    sounds = SoundManager()
    sounds.play_bgm()

    while True:
        # Always restore menu-sized window when returning
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

        action = start_screen(screen)
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))  # restore after menu resize

        if action == "quit":
            break
        elif action == "play":
            map_path = map_select_screen(screen)
            if map_path is None:
                continue
            result = run_game(screen, map_path, sounds=sounds)
            if result == "quit":
                break
            # result == "menu" → loop back to start screen
        elif action == "editor":
            result = run_editor(screen)
            if result == "quit":
                break
            # result == "back" → loop back to start screen

    sounds.stop_bgm()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()