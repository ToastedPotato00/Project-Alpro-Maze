"""
main.py — Phase 4
Full tile mechanics wired in:
  step counter, fire HP, mud freeze, ice slide,
  teleporter snap, key pickup, broken wall + key restore on backtrack.

HUD shows HP bar, key count, step count, status.
R = restart, ESC = quit.
"""

import pygame
import sys
import time
import copy

from map_loader   import load_map, find_tile
from map_renderer import MapRenderer
from player       import Player
from algorithm    import dfs_backtrack
from tiles        import build_teleporter_map
from ui           import HUD

WINDOW_TITLE   = "MazeCrawler — Phase 4 (Tile Mechanics)"
FPS            = 60

SLEEP_MOVE      = 0.08
SLEEP_BACKTRACK = 0.04
SLEEP_FREEZE    = 0.15   # per mud freeze frame

TRAIL_COLOR  = (80, 160, 255)
TRAIL_ALPHA  = 60


def make_trail_surf(tile_size):
    s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    s.fill((*TRAIL_COLOR, TRAIL_ALPHA))
    return s


def make_bt_surf(tile_size):
    s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    s.fill((255, 120, 60, 35))
    return s


def build_run(grid_master, tile_size):
    grid   = copy.deepcopy(grid_master)
    starts = find_tile(grid, "S")
    goals  = find_tile(grid, "G")
    start  = starts[0] if starts else (1, 1)
    goal   = goals[0]  if goals  else (len(grid)-2, len(grid[0])-2)
    player = Player(start[0], start[1], tile_size)
    gen    = dfs_backtrack(grid, player, start, goal)
    return grid, player, gen, goal


def main():
    pygame.init()
    pygame.font.init()

    grid_master, tile_size = load_map("maps/map_test.txt")
    cols = len(grid_master[0])
    rows = len(grid_master)

    # Extra height for HUD
    from ui import HUD_HEIGHT
    screen_w = cols * tile_size
    screen_h = rows * tile_size + HUD_HEIGHT

    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption(WINDOW_TITLE)
    clock  = pygame.time.Clock()

    trail_surf = make_trail_surf(tile_size)
    bt_surf    = make_bt_surf(tile_size)

    grid, player, gen, goal = build_run(grid_master, tile_size)
    renderer = MapRenderer(grid, tile_size)
    hud      = HUD(screen_w, screen_h)

    visited_cells   = {(player.row, player.col)}
    backtrack_cells = set()
    status     = "idle"
    finished   = False
    last_step  = time.time()

    help_font = pygame.font.SysFont("monospace", 14)
    help_text = help_font.render("R = restart   ESC = quit", True, (100, 100, 100))

    running = True
    while running:
        now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    grid, player, gen, goal = build_run(grid_master, tile_size)
                    renderer.update_grid(grid)
                    visited_cells   = {(player.row, player.col)}
                    backtrack_cells = set()
                    status    = "idle"
                    finished  = False
                    last_step = now

        # --- Mud freeze tick ---
        if player.is_frozen():
            player.tick_freeze()
            # Slow down while frozen
            time.sleep(SLEEP_FREEZE)

        # --- Step algorithm ---
        if not finished and not player.is_frozen():
            sleep_time = SLEEP_BACKTRACK if status == "backtracking" else SLEEP_MOVE
            if now - last_step >= sleep_time:
                try:
                    kind, r, c, extra = next(gen)
                    last_step = time.time()

                    if kind == "move":
                        status = "exploring"
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                        renderer.update_grid(grid)

                        # Trigger mud freeze
                        if extra.get("freeze_frames", 0) > 0:
                            player.freeze_frames_left = extra["freeze_frames"]

                    elif kind == "backtrack":
                        status = "backtracking"
                        backtrack_cells.add((r, c))
                        renderer.update_grid(grid)   # wall/key restorations

                    elif kind == "found":
                        status   = "found"
                        finished = True

                    elif kind == "no_solution":
                        status   = "no_solution"
                        finished = True

                except StopIteration:
                    if status not in ("found", "no_solution"):
                        status = "no_solution"
                    finished = True

        # --- Draw ---
        screen.fill((0, 0, 0))
        renderer.draw(screen)

        for (vr, vc) in visited_cells:
            screen.blit(trail_surf, (vc * tile_size, vr * tile_size))
        for (vr, vc) in backtrack_cells:
            screen.blit(bt_surf, (vc * tile_size, vr * tile_size))

        player.draw(screen)

        # Goal highlight
        gx = goal[1] * tile_size
        gy = goal[0] * tile_size
        pygame.draw.rect(screen, (255, 220, 40), (gx, gy, tile_size, tile_size), 3)

        hud.draw(screen, player, status)

        screen.blit(help_text, (screen_w - help_text.get_width() - 8, 6))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()