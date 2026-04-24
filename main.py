"""
main.py — Phase 6
Minimum viable UI — clean final version.
  - HUD: HP bar, key counter, step counter, speed slider, status
  - Visited trail (blue) + backtrack trail (orange)
  - Goal tile highlight
  - R = restart, ESC = quit
"""

import pygame
import sys
import time
import copy

from map_loader   import load_map, find_tile
from map_renderer import MapRenderer
from player       import Player
from algorithm    import dfs_backtrack
from ui           import HUD, HUD_HEIGHT

WINDOW_TITLE = "MazeCrawler — Prototype"
FPS          = 60

TRAIL_COLOR  = (80,  160, 255)
TRAIL_ALPHA  = 55
BT_ALPHA     = 30


def make_overlay(tile_size, r, g, b, a):
    s = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
    s.fill((r, g, b, a))
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
    cols     = len(grid_master[0])
    rows     = len(grid_master)
    screen_w = cols * tile_size
    screen_h = rows * tile_size + HUD_HEIGHT

    screen = pygame.display.set_mode((screen_w, screen_h))
    pygame.display.set_caption(WINDOW_TITLE)
    clock  = pygame.time.Clock()

    trail_surf = make_overlay(tile_size, *TRAIL_COLOR, TRAIL_ALPHA)
    bt_surf    = make_overlay(tile_size, 255, 120, 60, BT_ALPHA)

    grid, player, gen, goal = build_run(grid_master, tile_size)
    renderer = MapRenderer(grid, tile_size)
    hud      = HUD(screen_w, screen_h)

    visited_cells   = {(player.row, player.col)}
    backtrack_cells = set()
    status   = "idle"
    finished = False
    last_step = time.time()

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
            hud.handle_event(event)

        # ── Mud freeze tick ────────────────────────────────────────────────
        if player.is_frozen():
            player.tick_freeze()
            time.sleep(0.12)

        # ── Step algorithm ─────────────────────────────────────────────────
        if not finished and not player.is_frozen():
            delay = hud.step_delay * (0.5 if status == "backtracking" else 1.0)
            if now - last_step >= delay:
                try:
                    kind, r, c, extra = next(gen)
                    last_step = time.time()

                    if kind == "move":
                        status = "exploring"
                        visited_cells.add((r, c))
                        backtrack_cells.discard((r, c))
                        renderer.update_grid(grid)
                        if extra.get("freeze_frames", 0) > 0:
                            player.freeze_frames_left = extra["freeze_frames"]

                    elif kind == "backtrack":
                        status = "backtracking"
                        backtrack_cells.add((r, c))
                        renderer.update_grid(grid)

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

        # ── Draw ──────────────────────────────────────────────────────────
        screen.fill((0, 0, 0))
        renderer.draw(screen)

        for (vr, vc) in visited_cells:
            screen.blit(trail_surf, (vc * tile_size, vr * tile_size))
        for (vr, vc) in backtrack_cells:
            screen.blit(bt_surf, (vc * tile_size, vr * tile_size))

        player.draw(screen)

        # Goal highlight — pulsing yellow ring
        gx = goal[1] * tile_size
        gy = goal[0] * tile_size
        pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500   # 0→1→0
        ring_w = max(1, int(1 + pulse * 3))
        pygame.draw.rect(screen, (255, 215, 40),
                         (gx, gy, tile_size, tile_size), ring_w)

        hud.draw(screen, player, status)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()