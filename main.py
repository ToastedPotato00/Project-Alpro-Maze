"""
main.py — with start screen and Map Editor button
"""

import pygame
import sys
import time
import copy

from map_loader    import load_map, find_tile
from map_renderer  import MapRenderer
from player        import Player
from algorithm     import dfs_backtrack
from ui            import HUD, HUD_HEIGHT
from map_editor    import run_editor
from sprite_loader import load_sprites

WINDOW_TITLE = "MazeCrawler"
SCREEN_W     = 800
SCREEN_H     = 640
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
    font_lg = pygame.font.SysFont("monospace", 32, bold=True)
    font_md = pygame.font.SysFont("monospace", 18, bold=True)
    font_sm = pygame.font.SysFont("monospace", 14)
    clock   = pygame.time.Clock()
    cx      = SCREEN_W // 2

    btn_play   = Btn((cx-110, 260, 220, 48), "▶  Play",
                     font_md, color=BTN_ACT, hover=ACCENT_HOV, tc=(255,255,255))
    btn_editor = Btn((cx-110, 325, 220, 48), "✏  Map Editor", font_md)
    btn_quit   = Btn((cx-110, 390, 220, 48), "✕  Quit", font_md)

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
        screen.blit(title, title.get_rect(centerx=cx, y=140))
        sub = font_sm.render("A Backtracking Visualizer", True, TEXT_DIM)
        screen.blit(sub, sub.get_rect(centerx=cx, y=185))

        for b in (btn_play, btn_editor, btn_quit):
            b.draw(screen)

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
    goal   = goals[0]  if goals  else (len(grid)-2, len(grid[0])-2)
    player = Player(start[0], start[1], tile_size)
    gen    = dfs_backtrack(grid, player, start, goal)
    return grid, player, gen, goal


# ── Game loop ─────────────────────────────────────────────────────────────────
def run_game(screen):
    grid_master, tile_size = load_map("maps/map_test.txt")
    cols     = len(grid_master[0])
    rows     = len(grid_master)
    game_w   = cols * tile_size
    game_h   = rows * tile_size + HUD_HEIGHT

    # Resize window to fit map
    game_screen = pygame.display.set_mode((game_w, game_h))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    sprites = load_sprites(tile_size)   # None if spritesheet missing → rect fallback

    trail_surf = make_overlay(tile_size, *TRAIL_COLOR, TRAIL_ALPHA)
    bt_surf    = make_overlay(tile_size, 255, 120, 60, BT_ALPHA)

    grid, player, gen, goal = build_run(grid_master, tile_size)
    renderer = MapRenderer(grid, tile_size, sprites=sprites)
    hud      = HUD(game_w, game_h)

    visited_cells   = {(player.row, player.col)}
    backtrack_cells = set()
    status    = "idle"
    finished  = False
    last_step = time.time()

    while True:
        now = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if event.key == pygame.K_r:
                    grid, player, gen, goal = build_run(grid_master, tile_size)
                    renderer.update_grid(grid)
                    visited_cells   = {(player.row, player.col)}
                    backtrack_cells = set()
                    status    = "idle"
                    finished  = False
                    last_step = now
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
        renderer.draw(game_screen, pygame.time.get_ticks())

        for (vr, vc) in visited_cells:
            game_screen.blit(trail_surf, (vc * tile_size, vr * tile_size))
        for (vr, vc) in backtrack_cells:
            game_screen.blit(bt_surf, (vc * tile_size, vr * tile_size))

        player.draw(game_screen, sprites)

        gx = goal[1] * tile_size
        gy = goal[0] * tile_size
        pulse = abs((pygame.time.get_ticks() % 1000) - 500) / 500
        pygame.draw.rect(game_screen, (255, 215, 40),
                         (gx, gy, tile_size, tile_size), max(1, int(1 + pulse * 3)))

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
            result = run_game(screen)
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