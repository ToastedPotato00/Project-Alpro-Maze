"""
map_editor.py
Self-contained map editor with its own event loop.
Called from main.py via run_editor().

Screens:
  1. Map List  — shows existing maps + "New Map" button
  2. New Map   — input name + size (WxH), confirm creates the .txt
  3. Editor    — tile palette bottom, grid canvas, Save button
"""

import pygame
import os
import glob

# ── Tile palette (no ice) ────────────────────────────────────────────────────
PALETTE = [
    ("#", "Wall",         (30,  30,  35)),
    ("%", "Broken Wall",  (80,  55,  30)),
    (".", "Floor",        (60,  55,  50)),
    ("M", "Mud",          (90,  70,  20)),
    ("F", "Fire",         (210, 70,  20)),
    ("T", "Teleport A",   (140, 60, 200)),
    ("t", "Teleport B",   (180,100, 220)),
    ("K", "Key",          (240,200,  40)),
    ("S", "Start",        (40, 180,  80)),
    ("G", "Goal",         (240,200,  40)),
]

MAPS_DIR   = "maps"
MAPS_EXT   = "*.txt"

# ── Colours ──────────────────────────────────────────────────────────────────
BG         = (18,  18,  24)
PANEL_BG   = (25,  25,  35)
BORDER     = (50,  50,  70)
TEXT       = (200, 200, 210)
TEXT_DIM   = (100, 100, 120)
ACCENT     = (80,  160, 255)
ACCENT_HOV = (110, 185, 255)
BTN_BG     = (35,  35,  50)
BTN_HOV    = (50,  50,  75)
BTN_ACT    = (60,  120, 200)
RED_BTN    = (160,  40,  40)
RED_HOV    = (200,  60,  60)
INPUT_BG   = (30,  30,  45)
INPUT_ACT  = (40,  40,  65)
INPUT_BDR  = (80,  80, 110)
SEL_BORDER = (255, 215,  40)
GRID_LINE  = (45,  45,  60)

FPS = 60


# ── Tiny UI helpers ──────────────────────────────────────────────────────────

class Button:
    def __init__(self, rect, label, color=BTN_BG, hover_color=BTN_HOV,
                 text_color=TEXT, font=None, radius=6):
        self.rect        = pygame.Rect(rect)
        self.label       = label
        self.color       = color
        self.hover_color = hover_color
        self.text_color  = text_color
        self.font        = font
        self.radius      = radius
        self._hovered    = False

    def draw(self, surface):
        col = self.hover_color if self._hovered else self.color
        pygame.draw.rect(surface, col, self.rect, border_radius=self.radius)
        pygame.draw.rect(surface, BORDER, self.rect, 1, border_radius=self.radius)
        if self.font:
            lbl = self.font.render(self.label, True, self.text_color)
            surface.blit(lbl, lbl.get_rect(center=self.rect.center))

    def update(self, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


class TextInput:
    def __init__(self, rect, placeholder="", font=None, max_chars=30):
        self.rect        = pygame.Rect(rect)
        self.placeholder = placeholder
        self.font        = font
        self.max_chars   = max_chars
        self.text        = ""
        self.active      = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB):
                if len(self.text) < self.max_chars:
                    self.text += event.unicode

    def draw(self, surface):
        bg = INPUT_ACT if self.active else INPUT_BG
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        bdr_col = ACCENT if self.active else INPUT_BDR
        pygame.draw.rect(surface, bdr_col, self.rect, 1, border_radius=4)
        if self.font:
            display = self.text if self.text else self.placeholder
            col     = TEXT if self.text else TEXT_DIM
            lbl     = self.font.render(display, True, col)
            surface.blit(lbl, (self.rect.x + 8,
                                self.rect.centery - lbl.get_height() // 2))
            # Cursor
            if self.active and self.text:
                cx = self.rect.x + 8 + lbl.get_width() + 2
                cy = self.rect.centery
                pygame.draw.line(surface, TEXT,
                                 (cx, cy - 8), (cx, cy + 8), 1)


# ── Map list screen ──────────────────────────────────────────────────────────

class MapListScreen:
    def __init__(self, surface, fonts):
        self.surface = surface
        self.fonts   = fonts
        self.W, self.H = surface.get_size()
        self._build()

    def _build(self):
        f  = self.fonts
        cx = self.W // 2

        self.btn_new = Button(
            (cx - 100, self.H - 70, 200, 40),
            "＋  New Map",
            color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["md"]
        )
        self.btn_back = Button(
            (20, self.H - 70, 100, 40),
            "← Back",
            font=f["sm"]
        )
        self._refresh()

    def _refresh(self):
        os.makedirs(MAPS_DIR, exist_ok=True)
        self.maps = sorted(glob.glob(os.path.join(MAPS_DIR, MAPS_EXT)))
        # Row buttons for each map
        f  = self.fonts
        cx = self.W // 2
        self.map_btns = []
        for i, path in enumerate(self.maps):
            name = os.path.splitext(os.path.basename(path))[0]
            r    = pygame.Rect(cx - 160, 120 + i * 52, 320, 40)
            self.map_btns.append((Button(r, name, font=f["md"]), path))

    def run(self):
        clock = pygame.time.Clock()
        while True:
            mouse = pygame.mouse.get_pos()
            self.btn_new.update(mouse)
            self.btn_back.update(mouse)
            for btn, _ in self.map_btns:
                btn.update(mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return ("quit", None)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return ("back", None)
                if self.btn_back.is_clicked(event):
                    return ("back", None)
                if self.btn_new.is_clicked(event):
                    return ("new", None)
                for btn, path in self.map_btns:
                    if btn.is_clicked(event):
                        return ("edit", path)

            self._draw()
            clock.tick(FPS)

    def _draw(self):
        s = self.surface
        s.fill(BG)

        # Title
        title = self.fonts["lg"].render("Map Editor", True, TEXT)
        s.blit(title, title.get_rect(centerx=self.W // 2, y=30))

        sub = self.fonts["sm"].render("Select a map to edit, or create a new one.",
                                      True, TEXT_DIM)
        s.blit(sub, sub.get_rect(centerx=self.W // 2, y=70))

        # Map list
        if not self.map_btns:
            msg = self.fonts["sm"].render("No maps found in /maps folder.",
                                          True, TEXT_DIM)
            s.blit(msg, msg.get_rect(centerx=self.W // 2, y=160))
        else:
            for btn, _ in self.map_btns:
                btn.draw(s)

        self.btn_new.draw(s)
        self.btn_back.draw(s)
        pygame.display.flip()


# ── New map dialog ────────────────────────────────────────────────────────────

class NewMapScreen:
    def __init__(self, surface, fonts):
        self.surface = surface
        self.fonts   = fonts
        self.W, self.H = surface.get_size()
        self.error   = ""
        self._build()

    def _build(self):
        f  = self.fonts
        cx = self.W // 2

        self.inp_name = TextInput(
            (cx - 120, 160, 240, 36),
            placeholder="e.g. map4",
            font=f["md"], max_chars=24
        )
        self.inp_w = TextInput(
            (cx - 60, 240, 55, 36),
            placeholder="cols",
            font=f["md"], max_chars=3
        )
        self.inp_h = TextInput(
            (cx + 10, 240, 55, 36),
            placeholder="rows",
            font=f["md"], max_chars=3
        )
        self.btn_confirm = Button(
            (cx - 80, 320, 160, 40),
            "Create Map",
            color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["md"]
        )
        self.btn_back = Button(
            (20, self.H - 70, 100, 40),
            "← Back", font=f["sm"]
        )

    def run(self):
        clock = pygame.time.Clock()
        inputs = [self.inp_name, self.inp_w, self.inp_h]

        while True:
            mouse = pygame.mouse.get_pos()
            self.btn_confirm.update(mouse)
            self.btn_back.update(mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return ("quit", None, 0, 0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return ("back", None, 0, 0)
                for inp in inputs:
                    inp.handle_event(event)
                if self.btn_back.is_clicked(event):
                    return ("back", None, 0, 0)
                if self.btn_confirm.is_clicked(event):
                    result = self._validate()
                    if result:
                        name, cols, rows = result
                        return ("created", name, cols, rows)

            self._draw()
            clock.tick(FPS)

    def _validate(self):
        name = self.inp_name.text.strip()
        if not name:
            self.error = "Map name cannot be empty."; return None
        if not name.replace("_","").replace("-","").isalnum():
            self.error = "Name: letters, numbers, _ and - only."; return None

        path = os.path.join(MAPS_DIR, name + ".txt")
        if os.path.exists(path):
            self.error = f"{name}.txt already exists."; return None

        try:
            cols = int(self.inp_w.text)
            rows = int(self.inp_h.text)
        except ValueError:
            self.error = "Width and height must be numbers."; return None

        if not (3 <= cols <= 60 and 3 <= rows <= 40):
            self.error = "Width: 3–60   Height: 3–40"; return None

        self.error = ""
        return name, cols, rows

    def _draw(self):
        s  = self.surface
        cx = self.W // 2
        s.fill(BG)

        title = self.fonts["lg"].render("New Map", True, TEXT)
        s.blit(title, title.get_rect(centerx=cx, y=30))

        # Labels
        for text, y in [("Map name", 135), ("Size  (W × H)", 215)]:
            lbl = self.fonts["sm"].render(text, True, TEXT_DIM)
            s.blit(lbl, (cx - 120, y))

        x_lbl = self.fonts["sm"].render("×", True, TEXT_DIM)
        s.blit(x_lbl, x_lbl.get_rect(centerx=cx, centery=258))

        self.inp_name.draw(s)
        self.inp_w.draw(s)
        self.inp_h.draw(s)
        self.btn_confirm.draw(s)
        self.btn_back.draw(s)

        if self.error:
            err = self.fonts["sm"].render(self.error, True, (220, 80, 80))
            s.blit(err, err.get_rect(centerx=cx, y=375))

        pygame.display.flip()


# ── Editor screen ─────────────────────────────────────────────────────────────

PALETTE_H    = 90      # height of palette panel at bottom
MIN_TILE     = 14
MAX_TILE     = 40
PAL_ITEM_W   = 72
PAL_ITEM_H   = 70


class EditorScreen:
    def __init__(self, surface, fonts, map_path: str, grid: list):
        self.surface  = surface
        self.fonts    = fonts
        self.map_path = map_path
        self.grid     = grid          # list[list[str]], mutable
        self.W, self.H = surface.get_size()

        self.rows = len(grid)
        self.cols = len(grid[0])

        # Compute tile size to fit canvas area (above palette)
        canvas_h = self.H - PALETTE_H
        ts_by_w  = self.W // self.cols
        ts_by_h  = canvas_h // self.rows
        self.ts  = max(MIN_TILE, min(MAX_TILE, ts_by_w, ts_by_h))

        # Canvas offset (centre the grid)
        self.off_x = (self.W - self.cols * self.ts) // 2
        self.off_y = max(0, (canvas_h - self.rows * self.ts) // 2)

        self.selected_tile = "#"
        self.painting      = False    # mouse held down
        self.error_msg     = ""
        self.saved_msg     = ""
        self.saved_timer   = 0

        self._build_palette()
        self._build_buttons()

    def _build_palette(self):
        f         = self.fonts
        total_w   = len(PALETTE) * PAL_ITEM_W
        start_x   = (self.W - total_w) // 2
        pal_y     = self.H - PALETTE_H
        self.pal_rects = []
        for i, (sym, label, col) in enumerate(PALETTE):
            r = pygame.Rect(start_x + i * PAL_ITEM_W, pal_y + 4,
                            PAL_ITEM_W - 4, PALETTE_H - 8)
            self.pal_rects.append((r, sym, label, col))

    def _build_buttons(self):
        f = self.fonts
        self.btn_save = Button(
            (self.W - 120, 8, 110, 34),
            "💾  Save", color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["sm"]
        )
        self.btn_back = Button(
            (10, 8, 90, 34),
            "← Back", font=f["sm"]
        )

    # ── Main loop ─────────────────────────────────────────────────────────────
    def run(self):
        clock = pygame.time.Clock()
        while True:
            mouse = pygame.mouse.get_pos()
            self.btn_save.update(mouse)
            self.btn_back.update(mouse)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "back"
                    if event.key == pygame.K_s and \
                       pygame.key.get_mods() & pygame.KMOD_CTRL:
                        self._save()

                if self.btn_back.is_clicked(event):
                    return "back"
                if self.btn_save.is_clicked(event):
                    self._save()

                # Palette click
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for r, sym, label, col in self.pal_rects:
                        if r.collidepoint(event.pos):
                            self.selected_tile = sym

                # Start / stop painting
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.painting = True
                    self._try_paint(event.pos)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.painting = False

                # Right-click erases to floor
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    self._try_paint(event.pos, force_sym=".")

            if self.painting:
                self._try_paint(pygame.mouse.get_pos())

            # Saved message timer
            if self.saved_timer > 0:
                self.saved_timer -= clock.get_time()

            self._draw()
            clock.tick(FPS)

    # ── Painting ──────────────────────────────────────────────────────────────
    def _try_paint(self, pos, force_sym=None):
        px, py = pos
        col = (px - self.off_x) // self.ts
        row = (py - self.off_y) // self.ts

        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        # Don't let user paint over the outer border wall
        if row == 0 or row == self.rows-1 or col == 0 or col == self.cols-1:
            return
        # Don't paint in palette area
        if py >= self.H - PALETTE_H:
            return

        sym = force_sym if force_sym else self.selected_tile
        # Don't place outer wall symbol inside
        self.grid[row][col] = sym

    # ── Save ──────────────────────────────────────────────────────────────────
    def _save(self):
        os.makedirs(MAPS_DIR, exist_ok=True)
        try:
            with open(self.map_path, "w") as f:
                for row in self.grid:
                    f.write("".join(row) + "\n")
            self.saved_timer = 2000
            self.error_msg   = ""
        except Exception as e:
            self.error_msg = str(e)

    # ── Draw ──────────────────────────────────────────────────────────────────
    def _draw(self):
        s = self.surface
        s.fill(BG)

        # ── Grid ──────────────────────────────────────────────────────────────
        from tiles import get_color
        ts  = self.ts
        ox  = self.off_x
        oy  = self.off_y

        for r, row in enumerate(self.grid):
            for c, sym in enumerate(row):
                x = ox + c * ts
                y = oy + r * ts
                col = get_color(sym)
                pygame.draw.rect(s, col, (x, y, ts, ts))
                pygame.draw.rect(s, GRID_LINE, (x, y, ts, ts), 1)

                # Symbol label on large enough tiles
                if ts >= 18 and sym not in ("#", "."):
                    lbl = self.fonts["xs"].render(sym, True, (255,255,255))
                    s.blit(lbl, lbl.get_rect(center=(x + ts//2, y + ts//2)))

        # Hover highlight
        mx, my = pygame.mouse.get_pos()
        hc = (mx - ox) // ts
        hr = (my - oy) // ts
        if (0 < hr < self.rows-1 and 0 < hc < self.cols-1
                and my < self.H - PALETTE_H):
            hx = ox + hc * ts
            hy = oy + hr * ts
            hover_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
            hover_surf.fill((255, 255, 255, 40))
            s.blit(hover_surf, (hx, hy))

        # ── Palette panel ─────────────────────────────────────────────────────
        pal_y = self.H - PALETTE_H
        pygame.draw.rect(s, PANEL_BG, (0, pal_y, self.W, PALETTE_H))
        pygame.draw.line(s, BORDER, (0, pal_y), (self.W, pal_y), 1)

        for rect, sym, label, col in self.pal_rects:
            # Swatch background
            pygame.draw.rect(s, col, rect, border_radius=4)
            if sym == self.selected_tile:
                pygame.draw.rect(s, SEL_BORDER, rect, 3, border_radius=4)
            else:
                pygame.draw.rect(s, BORDER, rect, 1, border_radius=4)

            # Symbol
            sym_lbl = self.fonts["md"].render(sym, True, (255,255,255))
            s.blit(sym_lbl, sym_lbl.get_rect(
                centerx=rect.centerx, y=rect.y + 6))

            # Name
            name_lbl = self.fonts["xs"].render(label, True,
                                               (220,220,220) if sym == self.selected_tile
                                               else TEXT_DIM)
            s.blit(name_lbl, name_lbl.get_rect(
                centerx=rect.centerx, y=rect.y + 30))

        # ── Top bar ───────────────────────────────────────────────────────────
        pygame.draw.rect(s, PANEL_BG, (0, 0, self.W, 50))
        pygame.draw.line(s, BORDER, (0, 50), (self.W, 50), 1)

        map_name = os.path.splitext(os.path.basename(self.map_path))[0]
        title = self.fonts["md"].render(
            f"{map_name}   {self.cols}×{self.rows}", True, TEXT)
        s.blit(title, title.get_rect(centerx=self.W//2, centery=25))

        hint = self.fonts["xs"].render(
            "Left-click: paint   Right-click: erase   Ctrl+S: save",
            True, TEXT_DIM)
        s.blit(hint, hint.get_rect(centerx=self.W//2, y=52))

        self.btn_save.draw(s)
        self.btn_back.draw(s)

        # Saved / error feedback
        if self.saved_timer > 0:
            msg = self.fonts["sm"].render("✓ Saved!", True, (80, 220, 80))
            s.blit(msg, (self.W - 230, 8))
        if self.error_msg:
            msg = self.fonts["sm"].render(self.error_msg, True, (220, 80, 80))
            s.blit(msg, (self.W - 400, 8))

        pygame.display.flip()


# ── Grid factory ─────────────────────────────────────────────────────────────

def make_empty_grid(cols: int, rows: int) -> list:
    """All # outer border, floor inside."""
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            if r == 0 or r == rows-1 or c == 0 or c == cols-1:
                row.append("#")
            else:
                row.append("#")   # start all-# as requested, user paints from there
        grid.append(row)
    return grid


def load_grid(path: str) -> list:
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f]
    while lines and not lines[0].strip(): lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    max_w = max(len(l) for l in lines)
    return [list(l.ljust(max_w, "#")) for l in lines]


def save_grid(path: str, grid: list):
    os.makedirs(MAPS_DIR, exist_ok=True)
    with open(path, "w") as f:
        for row in grid:
            f.write("".join(row) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def run_editor(surface):
    """
    Main entry called from main.py.
    Manages screen transitions internally.
    Returns when user backs out to main menu.
    """
    pygame.font.init()
    fonts = {
        "lg": pygame.font.SysFont("monospace", 28, bold=True),
        "md": pygame.font.SysFont("monospace", 16, bold=True),
        "sm": pygame.font.SysFont("monospace", 14),
        "xs": pygame.font.SysFont("monospace", 11),
    }

    screen_name = "list"

    while True:
        if screen_name == "list":
            result = MapListScreen(surface, fonts).run()
            action = result[0]
            if action == "quit":   return "quit"
            if action == "back":   return "back"
            if action == "new":    screen_name = "new"
            if action == "edit":
                path = result[1]
                grid = load_grid(path)
                screen_name = "editor"
                editor_path = path
                editor_grid = grid

        elif screen_name == "new":
            result = NewMapScreen(surface, fonts).run()
            action = result[0]
            if action == "quit":  return "quit"
            if action == "back":  screen_name = "list"
            if action == "created":
                _, name, cols, rows = result
                path = os.path.join(MAPS_DIR, name + ".txt")
                grid = make_empty_grid(cols, rows)
                save_grid(path, grid)
                editor_path = path
                editor_grid = grid
                screen_name = "editor"

        elif screen_name == "editor":
            result = EditorScreen(surface, fonts, editor_path, editor_grid).run()
            if result == "quit": return "quit"
            if result == "back": screen_name = "list"