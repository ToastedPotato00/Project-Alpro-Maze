"""
main.py — with start screen and Map Editor button
"""

import os
import pygame
import sys
import time
import copy

from map_loader    import load_map, find_tile
from map_renderer  import MapRenderer
from player        import Player
from algorithm     import dfs_backtrack, dfs_chained, dfs_optimize
from ui            import HUD, HUD_HEIGHT
from map_editor    import run_editor
from sprite_loader import load_sprites
from tiles         import DIFF_CONFIGS
from sound_manager import SoundManager

WINDOW_TITLE = "MazeCrawler"
SCREEN_W     = 1440
SCREEN_H     = 700
FPS          = 60

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


# ── Simple button (local, avoids circular import) ─────────────────────────────
class Btn:
    def __init__(self, rect, label, font,
                 color=BTN_BG, hover=BTN_HOV, tc=TEXT):
        self.rect  = pygame.Rect(rect)
        self.label = label
        self.font  = font
        self.color = color
        self.hover = hover
        self.tc    = tc
        self._hov  = False

    def update(self, mp): self._hov = self.rect.collidepoint(mp)

    def draw(self, s):
        pygame.draw.rect(s, self.hover if self._hov else self.color,
                         self.rect, border_radius=8)
        pygame.draw.rect(s, BORDER, self.rect, 1, border_radius=8)
        lbl = self.font.render(self.label, True, self.tc)
        s.blit(lbl, lbl.get_rect(center=self.rect.center))

    def clicked(self, e):
        return (e.type == pygame.MOUSEBUTTONDOWN and e.button == 1
                and self.rect.collidepoint(e.pos))


# ── Algorithm picker ─────────────────────────────────────────────────────────
ALGOS = [
    ("classic",  "Classic DFS",  "First valid path"),
    ("chained",  "Chained DFS",  "All goals in sequence"),
    ("optimize", "Optimize DFS", "Best scored path"),
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


# ── Start / map-select screen ─────────────────────────────────────────────────
def start_screen(screen):
    pygame.font.init()
    font_lg = pygame.font.SysFont("monospace", 48, bold=True)
    font_md = pygame.font.SysFont("monospace", 22, bold=True)
    font_sm = pygame.font.SysFont("monospace", 16)
    clock   = pygame.time.Clock()
    cx      = SCREEN_W // 2

    btn_play   = Btn((cx-140, 302, 280, 58), "▶  Play",
                     font_md, color=BTN_ACT, hover=ACCENT_HOV, tc=(255,255,255))
    btn_editor = Btn((cx-140, 376, 280, 58), "✏  Map Editor", font_md)
    btn_quit   = Btn((cx-140, 450, 280, 58), "✕  Quit", font_md)

    while True:
        mp = pygame.mouse.get_pos()
        for b in (btn_play, btn_editor, btn_quit):
            b.update(mp)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "quit"
            if btn_play.clicked(event):   return "play"
            if btn_editor.clicked(event): return "editor"
            if btn_quit.clicked(event):   return "quit"

        screen.fill(BG)
        title = font_lg.render("MazeCrawler", True, TEXT)
        screen.blit(title, title.get_rect(centerx=cx, y=192))

        for b in (btn_play, btn_editor, btn_quit):
            b.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


# ── Map selection screen ──────────────────────────────────────────────────────
def map_select_screen(screen):
    pygame.font.init()
    font_lg = pygame.font.SysFont("monospace", 48, bold=True)
    font_md = pygame.font.SysFont("monospace", 22, bold=True)
    font_sm = pygame.font.SysFont("monospace", 16)
    clock   = pygame.time.Clock()
    cx      = SCREEN_W // 2

    maps = sorted(f for f in os.listdir("maps") if f.endswith(".txt"))

    def label(filename):
        stem = filename[:-4]
        return stem.replace("_", " ").title()

    btn_h, btn_gap = 54, 10
    back_h, back_gap = 48, 18
    n = len(maps)

    # Measure approximate font heights for centering the whole block
    TITLE_H      = 52
    SUB_H        = 18
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
            label(m), font_md)
        for i, m in enumerate(maps)
    ]
    back_y   = start_y + btns_block_h + back_gap
    btn_back = Btn((cx - 100, back_y, 200, back_h), "← Back", font_md)

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

        screen.fill(BG)
        title = font_lg.render("Select a Map", True, TEXT)
        screen.blit(title, title.get_rect(centerx=cx, y=title_y))
        sub = font_sm.render("Choose a map to run the algorithm on", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, y=sub_y))

        if maps:
            for b in map_btns:
                b.draw(screen)
        else:
            msg = font_sm.render("No maps found in /maps/", True, TEXT_DIM)
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
    hint = font_sm.render("R  restart          ESC  return to menu", True, (75, 75, 108))
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
        gen = dfs_chained(grid, player, start, goals, diff=cfg)
    elif algo == "optimize":
        gen = dfs_optimize(grid, player, start, goals[0], diff=cfg)
    else:
        gen = dfs_backtrack(grid, player, start, goals[0], diff=cfg)
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
def run_game(screen, map_path):
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
    sounds     = SoundManager()
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
    algo_btn_rect = None
    diff_btn_rect = None

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
    status    = "idle"
    finished  = False
    last_step = time.time()

    while True:
        now             = time.time()
        cam_x, cam_y   = _camera(player.col, player.row, ts, cols, rows)
        offset          = (-cam_x, -cam_y)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if dropdown.open or diff_dropdown.open:
                        dropdown.open      = False
                        diff_dropdown.open = False
                    else:
                        return "menu"
                if event.key == pygame.K_r and not dropdown.open and not diff_dropdown.open:
                    grid, player, gen, goals = build_run(grid_master, ts, algo, diff)
                    renderer.update_grid(grid)
                    visited_cells   = {(player.row, player.col)}
                    backtrack_cells = set()
                    solution_path   = [(player.row, player.col)]
                    active_goal_idx = 0
                    best_score      = None
                    backtrack_count = 0
                    paths_explored  = 0
                    status    = "idle"
                    finished  = False
                    last_step = now
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
                    hud.handle_event(event)

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
            status    = "idle"
            finished  = False
            last_step = now

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
            status    = "idle"
            finished  = False
            last_step = now

        if player.is_frozen():
            player.tick_freeze()
            time.sleep(0.12)

        if not finished and not player.is_frozen():
            delay = hud.step_delay * (0.5 if status == "backtracking" else 1.0)
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
                        finished = True
                    elif kind == "no_solution":
                        status = "no_solution"
                        player.is_active = False
                        finished = True
                except StopIteration:
                    if status not in ("found", "no_solution"):
                        status = "no_solution"
                    finished = True

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
        algo_btn_rect, diff_btn_rect = hud.draw(
            game_screen, player, status, dropdown.label,
            score=best_score, diff_label=diff_dropdown.label)
        dropdown.draw(game_screen, algo_btn_rect)
        diff_dropdown.draw(game_screen, diff_btn_rect)

        if finished:
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

    while True:
        # Always restore menu-sized window when returning
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

        action = start_screen(screen)

        if action == "quit":
            break
        elif action == "play":
            map_path = map_select_screen(screen)
            if map_path is None:
                continue
            result = run_game(screen, map_path)
            if result == "quit":
                break
            # result == "menu" → loop back to start screen
        elif action == "editor":
            result = run_editor(screen)
            if result == "quit":
                break
            # result == "back" → loop back to start screen

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()