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
from algorithm     import dfs_backtrack, dfs_chained
from ui            import HUD, HUD_HEIGHT
from map_editor    import run_editor
from sprite_loader import load_sprites

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


# ── Start / map-select screen ─────────────────────────────────────────────────
def start_screen(screen):
    pygame.font.init()
    font_lg = pygame.font.SysFont("monospace", 48, bold=True)
    font_md = pygame.font.SysFont("monospace", 22, bold=True)
    font_sm = pygame.font.SysFont("monospace", 16)
    clock   = pygame.time.Clock()
    cx      = SCREEN_W // 2

    btn_play   = Btn((cx-140, 420, 280, 58), "▶  Play",
                     font_md, color=BTN_ACT, hover=ACCENT_HOV, tc=(255,255,255))
    btn_editor = Btn((cx-140, 496, 280, 58), "✏  Map Editor", font_md)
    btn_quit   = Btn((cx-140, 572, 280, 58), "✕  Quit", font_md)

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
        screen.blit(title, title.get_rect(centerx=cx, y=280))
        sub = font_sm.render("A Backtracking Visualizer", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, y=348))

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

    btn_h, btn_gap = 58, 12
    start_y = 380
    map_btns = [
        Btn((cx - 140, start_y + i * (btn_h + btn_gap), 280, btn_h),
            label(m), font_md)
        for i, m in enumerate(maps)
    ]
    btn_back = Btn((cx - 100, 820, 200, 52), "← Back", font_md)

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
        screen.blit(title, title.get_rect(centerx=cx, y=260))
        sub = font_sm.render("Choose a map to run the algorithm on", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, y=328))

        if maps:
            for b in map_btns:
                b.draw(screen)
        else:
            msg = font_sm.render("No maps found in /maps/", True, TEXT_DIM)
            screen.blit(msg, msg.get_rect(centerx=cx, y=500))

        btn_back.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


# ── Game helpers ──────────────────────────────────────────────────────────────
def make_overlay(tile_size, r, g, b, a):
    s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    s.fill((r, g, b, a))
    return s


def build_run(grid_master, tile_size):
    grid   = copy.deepcopy(grid_master)
    starts = find_tile(grid, "S")
    goals  = find_tile(grid, "G")
    start  = starts[0] if starts else (1, 1)
    if not goals:
        goals = [(len(grid)-2, len(grid[0])-2)]
    player = Player(start[0], start[1], tile_size)
    if len(goals) > 1:
        gen = dfs_chained(grid, player, start, goals)
    else:
        gen = dfs_backtrack(grid, player, start, goals[0])
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
    trail_surf = make_overlay(ts, *TRAIL_COLOR, TRAIL_ALPHA)
    bt_surf    = make_overlay(ts, 255, 120, 60, BT_ALPHA)

    grid, player, gen, goals = build_run(grid_master, ts)
    renderer = MapRenderer(grid, ts, sprites=sprites)
    hud      = HUD(SCREEN_W, SCREEN_H)

    visited_cells    = {(player.row, player.col)}
    backtrack_cells  = set()
    active_goal_idx  = 0
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
                    return "menu"
                if event.key == pygame.K_r:
                    grid, player, gen, goals = build_run(grid_master, ts)
                    renderer.update_grid(grid)
                    visited_cells   = {(player.row, player.col)}
                    backtrack_cells = set()
                    active_goal_idx = 0
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
            hud.handle_event(event)

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
                        renderer.update_grid(grid)
                        if extra.get("freeze_frames", 0) > 0:
                            player.freeze_frames_left = extra["freeze_frames"]
                    elif kind == "backtrack":
                        status = "backtracking"
                        player.is_active    = True
                        player.is_backtrack = True
                        backtrack_cells.add((r, c))
                        renderer.update_grid(grid)
                    elif kind == "segment_found":
                        active_goal_idx += 1
                        status = "checkpoint"
                        player.is_active    = True
                        player.is_backtrack = False
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                    elif kind == "found":
                        status = "found"
                        player.is_active    = False
                        player.is_backtrack = False
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
        hud.draw(game_screen, player, status)
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