"""
map_editor.py — editor peta penggambaran tile di dalam game.

Dipanggil dari main.py melalui run_editor(). Mengelola tiga layar secara internal:
  1. MapListScreen  — menampilkan daftar file .txt yang ada di maps/ + tombol "Add New Map"
  2. NewMapScreen   — input teks untuk nama peta dan dimensi grid; divalidasi sebelum dibuat
  3. EditorScreen   — kanvas grid penuh dengan palet tile, zoom/pan, dan simpan

Transisi layar ditangani oleh loop while di run_editor(); setiap kelas layar
menjalankan event loop-nya sendiri dan mengembalikan string aksi saat selesai.

Kontrol di editor:
  Klik Kiri    — gambar tile yang dipilih
  Klik Kanan   — hapus ke lantai ('.')
  Scroll       — zoom masuk/keluar, berpusat pada kursor
  Seret Tengah — geser kanvas
  Ctrl+S       — simpan
"""

import pygame
import os
import glob
from sprite_loader import load_sprites
from tiles import get_color

# ── Palet tile ─────────────────────────────────────────────────────────────
# Setiap entri berisi (simbol, nama_tampilan, warna_cadangan).
# Daftar ini menggerakkan strip palet di bagian bawah editor dan
# logika rendering swatch di EditorScreen._build_palette().
PALETTE = [
    ("#", "Wall",         (30,  30,  35)),
    ("%", "Broken Wall",  (80,  55,  30)),
    (".", "Floor",        (60,  55,  50)),
    ("M", "Mud",          (90,  70,  20)),
    ("F", "Fire",         (210, 70,  20)),
    ("R", "Regen",        (60, 180,  80)),
    ("T", "Teleport A",   (140, 60, 200)),
    ("t", "Teleport B",   (180,100, 220)),
    ("K", "Key",          (240,200,  40)),
    ("S", "Start",        (40, 180,  80)),
    ("G", "Goal",         (240,200,  40)),
]

MAPS_DIR = "maps"
MAPS_EXT = "*.txt"

# Gambar latar untuk layar daftar dan layar peta baru; mundur diam ke warna solid.
MAP_LIST_BG = "assets/bg2.jpg"
NEW_MAP_BG  = "assets/bg2.jpg"


def _load_bg(path, w, h):
    """Muat dan skalakan gambar latar ke (w, h). Mengembalikan None secara diam-diam jika file tidak ditemukan."""
    try:
        raw = pygame.image.load(path).convert()
        return pygame.transform.smoothscale(raw, (w, h))
    except Exception:
        return None

# ── Warna (tema Dungeon Gold) ─────────────────────────────────────────────
BG         = (20,  15,  10)
PANEL_BG   = (28,  20,  12)
BORDER     = (120,  85,  25)
TEXT       = (235, 210, 140)
TEXT_DIM   = (130, 100,  55)
ACCENT     = (168, 120,  38)
ACCENT_HOV = (200, 150,  55)
BTN_BG     = (38,  28,  18)
BTN_HOV    = (62,  46,  26)
BTN_ACT    = (130,  90,  22)
RED_BTN    = (160,  40,  40)
RED_HOV    = (200,  60,  60)
INPUT_BG   = (30,  22,  12)
INPUT_ACT  = (44,  32,  16)
INPUT_BDR  = (90,  65,  25)
SEL_BORDER = (255, 215,  40)
GRID_LINE  = (50,  38,  20)
BG_CANVAS  = (18,  18,  24)

FPS = 60


# ── Widget UI yang dapat digunakan ulang ───────────────────────────────────────────────────────

class Button:
    """Persegi panjang yang bisa diklik dengan label teks dan sorotan hover."""
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
        """Panggil setiap frame dengan posisi mouse saat ini untuk melacak status hover."""
        self._hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, event):
        """Mengembalikan True jika event ini adalah klik kiri di dalam tombol."""
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))


class TextInput:
    """Bidang input teks satu baris. Mengklik mengaktifkannya; mengetik menambahkan karakter."""
    def __init__(self, rect, placeholder="", font=None, max_chars=30):
        self.rect        = pygame.Rect(rect)
        self.placeholder = placeholder
        self.font        = font
        self.max_chars   = max_chars
        self.text        = ""
        self.active      = False   # True ketika bidang memiliki fokus keyboard

    def handle_event(self, event):
        # Mengklik di mana saja mengatur fokus; mengklik di luar menghapusnya
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]   # hapus karakter terakhir
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB):
                if len(self.text) < self.max_chars:
                    self.text += event.unicode

    def draw(self, surface):
        bg = INPUT_ACT if self.active else INPUT_BG
        pygame.draw.rect(surface, bg, self.rect, border_radius=4)
        bdr_col = ACCENT if self.active else INPUT_BDR
        pygame.draw.rect(surface, bdr_col, self.rect, 1, border_radius=4)
        if self.font:
            # Tampilkan teks placeholder dalam warna redup saat kosong
            display = self.text if self.text else self.placeholder
            col     = TEXT if self.text else TEXT_DIM
            lbl     = self.font.render(display, True, col)
            surface.blit(lbl, (self.rect.x + 8,
                                self.rect.centery - lbl.get_height() // 2))
            # Gambar kursor bergaya berkedip setelah teks saat aktif
            if self.active and self.text:
                cx = self.rect.x + 8 + lbl.get_width() + 2
                cy = self.rect.centery
                pygame.draw.line(surface, TEXT,
                                 (cx, cy - 8), (cx, cy + 8), 1)


# ── Layar 1: Daftar peta ───────────────────────────────────────────────────────

class MapListScreen:
    def __init__(self, surface, fonts, sounds=None):
        self.surface = surface
        self.fonts   = fonts
        self.sounds  = sounds
        self.W, self.H = surface.get_size()
        self._bg_img = _load_bg(MAP_LIST_BG, self.W, self.H)
        self._build()

    def _build(self):
        f  = self.fonts
        cx = self.W // 2
        self.btn_new = Button(
            (cx - 140, self.H - 90, 280, 52),
            "Add New Map",
            color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["md"]
        )
        self.btn_back = Button(
            (20, self.H - 90, 140, 52),
            "← Back",
            font=f["sm"]
        )
        self._refresh()

    def _refresh(self):
        """Pindai ulang direktori maps/ dan bangun ulang daftar tombol per peta."""
        os.makedirs(MAPS_DIR, exist_ok=True)
        self.maps = sorted(glob.glob(os.path.join(MAPS_DIR, MAPS_EXT)))
        f  = self.fonts
        cx = self.W // 2
        self.map_btns = []
        for i, path in enumerate(self.maps):
            name = os.path.splitext(os.path.basename(path))[0]
            r    = pygame.Rect(cx - 200, 160 + i * 66, 400, 52)
            self.map_btns.append((Button(r, name, font=f["md"]), path))

    def run(self):
        """
        Loop event untuk layar daftar peta.
        Mengembalikan tuple: ("quit"|"back"|"new"|"edit", path_or_None)
        run_editor() membaca elemen pertama untuk menentukan layar berikutnya.
        """
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
                    if self.sounds: self.sounds.play("click")
                    return ("back", None)
                if self.btn_new.is_clicked(event):
                    if self.sounds: self.sounds.play("click")
                    return ("new", None)
                for btn, path in self.map_btns:
                    if btn.is_clicked(event):
                        if self.sounds: self.sounds.play("click")
                        return ("edit", path)   # kirim path ke run_editor untuk EditorScreen

            self._draw()
            clock.tick(FPS)

    def _draw(self):
        s = self.surface
        if self._bg_img:
            s.blit(self._bg_img, (0, 0))
        else:
            s.fill(BG)

        # Judul
        title = self.fonts["lg"].render("Map Editor", True, TEXT)
        s.blit(title, title.get_rect(centerx=self.W // 2, y=60))

        # Daftar peta
        if not self.map_btns:
            msg = self.fonts["sm"].render("No maps found in /maps folder.",
                                          True, TEXT_DIM)
            s.blit(msg, msg.get_rect(centerx=self.W // 2, y=300))
        else:
            for btn, _ in self.map_btns:
                btn.draw(s)

        self.btn_new.draw(s)
        self.btn_back.draw(s)
        pygame.display.flip()


# ── Layar 2: Dialog peta baru ──────────────────────────────────────────────────

class NewMapScreen:
    def __init__(self, surface, fonts, sounds=None):
        self.surface = surface
        self.fonts   = fonts
        self.sounds  = sounds
        self.W, self.H = surface.get_size()
        self.error   = ""
        self._bg_img = _load_bg(NEW_MAP_BG, self.W, self.H)
        self._build()

    def _build(self):
        f  = self.fonts
        cx = self.W // 2

        self.inp_name = TextInput(
            (cx - 160, 280, 320, 46),
            placeholder="e.g. map4",
            font=f["md"], max_chars=24
        )
        self.inp_w = TextInput(
            (cx - 80, 380, 70, 46),
            placeholder="cols",
            font=f["md"], max_chars=3
        )
        self.inp_h = TextInput(
            (cx + 20, 380, 70, 46),
            placeholder="rows",
            font=f["md"], max_chars=3
        )
        self.btn_confirm = Button(
            (cx - 110, 480, 220, 52),
            "Create Map",
            color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["md"]
        )
        self.btn_back = Button(
            (20, self.H - 90, 140, 52),
            "← Back", font=f["sm"]
        )

    def run(self):
        """
        Loop event untuk dialog peta baru.
        Mengembalikan ("quit"|"back", ...) atau ("created", name, cols, rows) jika berhasil.
        """
        clock  = pygame.time.Clock()
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
                    if self.sounds: self.sounds.play("click")
                    return ("back", None, 0, 0)
                if self.btn_confirm.is_clicked(event):
                    if self.sounds: self.sounds.play("click")
                    result = self._validate()
                    if result:
                        name, cols, rows = result
                        return ("created", name, cols, rows)

            self._draw()
            clock.tick(FPS)

    def _validate(self):
        """
        Validasi ketiga bidang input sebelum membuat peta.
        Mengatur self.error dengan pesan yang ditampilkan ke pengguna jika ada kegagalan.
        Mengembalikan (name, cols, rows) jika berhasil, None jika gagal.
        """
        name = self.inp_name.text.strip()
        if not name:
            self.error = "Map name cannot be empty."; return None
        # Hanya izinkan karakter yang aman untuk sistem file dalam nama file
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

        # Terapkan batas ukuran yang wajar agar peta tetap dapat digunakan
        if not (3 <= cols <= 60 and 3 <= rows <= 40):
            self.error = "Width: 3–60   Height: 3–40"; return None

        self.error = ""
        return name, cols, rows

    def _draw(self):
        s  = self.surface
        cx = self.W // 2
        if self._bg_img:
            s.blit(self._bg_img, (0, 0))
        else:
            s.fill(BG)

        title = self.fonts["lg"].render("New Map", True, TEXT)
        s.blit(title, title.get_rect(centerx=cx, y=160))

        # Label
        for text, y in [("Map name", 252), ("Size  (W × H)", 352)]:
            lbl = self.fonts["sm"].render(text, True, TEXT_DIM)
            s.blit(lbl, (cx - 160, y))

        x_lbl = self.fonts["sm"].render("×", True, TEXT_DIM)
        s.blit(x_lbl, x_lbl.get_rect(centerx=cx, centery=403))

        self.inp_name.draw(s)
        self.inp_w.draw(s)
        self.inp_h.draw(s)
        self.btn_confirm.draw(s)
        self.btn_back.draw(s)

        if self.error:
            err = self.fonts["sm"].render(self.error, True, (220, 80, 80))
            s.blit(err, err.get_rect(centerx=cx, y=550))

        pygame.display.flip()


# ── Layar 3: Kanvas editor ───────────────────────────────────────────────────

PALETTE_H       = 120   # tinggi strip palet tile di bagian bawah
TOP_BAR_H       = 60    # tinggi bilah atas (nama peta, tombol simpan, tombol kembali)
MIN_TILE        = 8     # ukuran tile minimum saat di-zoom keluar
MAX_TILE        = 80    # ukuran tile maksimum saat di-zoom masuk
PAL_ITEM_W      = 120   # 11 item palet × 120 px = 1320 px, dipusatkan di 1440
PAL_ITEM_H      = 100
PAL_SPRITE_SIZE = 64    # ukuran sprite yang dirender di dalam setiap swatch palet


class EditorScreen:
    def __init__(self, surface, fonts, map_path: str, grid: list, sounds=None):
        self.surface  = surface
        self.fonts    = fonts
        self.sounds   = sounds
        self.map_path = map_path
        self.grid     = grid          # list[list[str]] yang bisa diubah — langsung dilukis di tempat
        self.W, self.H = surface.get_size()

        self.rows = len(grid)
        self.cols = len(grid[0])

        # Sesuaikan otomatis: pilih ukuran tile terbesar yang menampilkan seluruh grid
        # di area kanvas (antara bilah atas dan strip palet).
        canvas_h = self.H - PALETTE_H - TOP_BAR_H
        ts_by_w  = self.W // self.cols
        ts_by_h  = canvas_h // self.rows
        self.ts  = max(MIN_TILE, min(MAX_TILE, ts_by_w, ts_by_h))

        # off_x/off_y adalah offset piksel sudut kiri atas grid.
        # Dimulai dari tengah; pan dan zoom keduanya memperbarui nilai-nilai ini.
        self.off_x = (self.W - self.cols * self.ts) // 2
        self.off_y = TOP_BAR_H + max(0, (canvas_h - self.rows * self.ts) // 2)

        self._pan_start  = None    # menyimpan posisi mouse awal saat seret tengah dimulai
        self._pan_origin = (0, 0)  # menyimpan off_x/off_y di awal gerakan pan

        self.selected_tile = "#"   # tile yang sedang aktif di palet
        self.painting      = False # True saat tombol mouse kiri ditahan
        self.error_msg     = ""
        self.saved_msg     = ""
        self.saved_timer   = 0     # hitung mundur (ms) untuk pesan kilat "Tersimpan!"

        # Dua set sprite terpisah: satu diskalakan ke ukuran tile kanvas, satu untuk swatch palet.
        self.sprites     = load_sprites(self.ts)
        self.pal_sprites = load_sprites(PAL_SPRITE_SIZE)

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
            (self.W - 150, 10, 138, 40),
            "Save", color=BTN_ACT, hover_color=ACCENT_HOV,
            text_color=(255,255,255), font=f["sm"]
        )
        self.btn_back = Button(
            (10, 10, 120, 40),
            "← Back", font=f["sm"]
        )

    # ── Pembantu zoom / pan ────────────────────────────────────────────────────

    def _clamp_offsets(self):
        """
        Cegah pengguna dari menggeser grid sepenuhnya keluar layar.
        Selalu menjaga setidaknya `margin` piksel dari grid terlihat di setiap tepi.
        """
        margin     = 60
        grid_w     = self.cols * self.ts
        grid_h     = self.rows * self.ts
        canvas_bot = self.H - PALETTE_H
        self.off_x = max(margin - grid_w, min(self.W - margin, self.off_x))
        self.off_y = max(TOP_BAR_H + margin - grid_h,
                         min(canvas_bot - margin, self.off_y))

    # ── Loop utama ─────────────────────────────────────────────────────────────
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
                    if self.sounds: self.sounds.play("click")
                    return "back"
                if self.btn_save.is_clicked(event):
                    if self.sounds: self.sounds.play("click")
                    self._save()

                # Klik palet
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for r, sym, label, col in self.pal_rects:
                        if r.collidepoint(event.pos):
                            if self.sounds: self.sounds.play("click")
                            self.selected_tile = sym

                # Mulai / hentikan menggambar
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.painting = True
                    self._try_paint(event.pos)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.painting = False

                # Klik kanan menghapus ke lantai
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    self._try_paint(event.pos, force_sym=".")

                # Seret mouse tengah untuk pan
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                    self._pan_start  = event.pos
                    self._pan_origin = (self.off_x, self.off_y)
                if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
                    self._pan_start = None
                if event.type == pygame.MOUSEMOTION and self._pan_start:
                    dx = event.pos[0] - self._pan_start[0]
                    dy = event.pos[1] - self._pan_start[1]
                    self.off_x = self._pan_origin[0] + dx
                    self.off_y = self._pan_origin[1] + dy
                    self._clamp_offsets()

                # Roda gulir untuk zoom (berpusat pada kursor mouse)
                if event.type == pygame.MOUSEWHEEL:
                    mx, my  = pygame.mouse.get_pos()
                    old_ts  = self.ts
                    new_ts  = max(MIN_TILE, min(MAX_TILE, old_ts + event.y * 2))
                    if new_ts != old_ts:
                        mc = (mx - self.off_x) / old_ts
                        mr = (my - self.off_y) / old_ts
                        self.off_x = int(mx - mc * new_ts)
                        self.off_y = int(my - mr * new_ts)
                        self.ts    = new_ts
                        self._clamp_offsets()
                        self.sprites = load_sprites(self.ts)

            if self.painting:
                self._try_paint(pygame.mouse.get_pos())

            # Timer pesan tersimpan
            if self.saved_timer > 0:
                self.saved_timer -= clock.get_time()

            self._draw()
            clock.tick(FPS)

    # ── Menggambar ──────────────────────────────────────────────────────────────

    def _try_paint(self, pos, force_sym=None):
        """
        Ubah posisi piksel layar menjadi sel grid dan gambar di sana.
        force_sym mengganti pilihan palet (digunakan untuk penghapusan klik kanan).
        Sel tepi (baris 0, baris terakhir, kolom 0, kolom terakhir) dilindungi —
        peta harus selalu memiliki batas dinding yang lengkap.
        """
        px, py = pos
        col = (px - self.off_x) // self.ts
        row = (py - self.off_y) // self.ts

        # Di luar batas grid — abaikan
        if not (0 <= row < self.rows and 0 <= col < self.cols):
            return
        # Lindungi batas luar agar peta selalu sepenuhnya tertutup
        if row == 0 or row == self.rows-1 or col == 0 or col == self.cols-1:
            return
        # Abaikan klik yang jatuh di strip palet atau bilah atas
        if py >= self.H - PALETTE_H or py < TOP_BAR_H:
            return

        sym = force_sym if force_sym else self.selected_tile
        self.grid[row][col] = sym

    # ── Simpan ──────────────────────────────────────────────────────────────────

    def _save(self):
        """Tulis grid saat ini ke file peta. Menampilkan kilat "Tersimpan!" selama 2 detik."""
        os.makedirs(MAPS_DIR, exist_ok=True)
        try:
            with open(self.map_path, "w") as f:
                for row in self.grid:
                    f.write("".join(row) + "\n")   # setiap baris adalah satu baris karakter
            self.saved_timer = 2000   # durasi kilat 2000 ms
            self.error_msg   = ""
        except Exception as e:
            self.error_msg = str(e)

    # ── Gambar ──────────────────────────────────────────────────────────────────
    def _draw(self):
        s = self.surface
        s.fill(BG_CANVAS)

        # ── Grid (dipotong ke area kanvas) ─────────────────────────────────────
        ts  = self.ts
        ox  = self.off_x
        oy  = self.off_y

        s.set_clip(pygame.Rect(0, TOP_BAR_H, self.W, self.H - PALETTE_H - TOP_BAR_H))

        tile_sprites = self.sprites.get("tiles", {}) if self.sprites else {}
        tile_anims   = self.sprites.get("tile_anims", {}) if self.sprites else {}
        ticks        = pygame.time.get_ticks()
        for r, row in enumerate(self.grid):
            for c, sym in enumerate(row):
                x = ox + c * ts
                y = oy + r * ts
                if sym in tile_anims:
                    frames = tile_anims[sym]
                    frame  = frames[(ticks // 120) % len(frames)]
                    s.blit(frame, (x, y))
                elif sym in tile_sprites:
                    s.blit(tile_sprites[sym], (x, y))
                else:
                    col = get_color(sym)
                    pygame.draw.rect(s, col, (x, y, ts, ts))
                    if ts >= 18 and sym not in ("#", "."):
                        lbl = self.fonts["xs"].render(sym, True, (255, 255, 255))
                        s.blit(lbl, lbl.get_rect(center=(x + ts // 2, y + ts // 2)))
                pygame.draw.rect(s, GRID_LINE, (x, y, ts, ts), 1)

        # Sorotan hover
        mx, my = pygame.mouse.get_pos()
        hc = (mx - ox) // ts
        hr = (my - oy) // ts
        if (0 < hr < self.rows-1 and 0 < hc < self.cols-1
                and TOP_BAR_H <= my < self.H - PALETTE_H):
            hx = ox + hc * ts
            hy = oy + hr * ts
            hover_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
            hover_surf.fill((255, 255, 255, 40))
            s.blit(hover_surf, (hx, hy))

        s.set_clip(None)

        # ── Panel palet ─────────────────────────────────────────────────────
        pal_y = self.H - PALETTE_H
        pygame.draw.rect(s, BG_CANVAS, (0, pal_y, self.W, PALETTE_H))
        pygame.draw.line(s, BORDER, (0, pal_y), (self.W, pal_y), 1)

        pal_tile_sprites = self.pal_sprites.get("tiles", {}) if self.pal_sprites else {}
        pal_tile_anims   = self.pal_sprites.get("tile_anims", {}) if self.pal_sprites else {}
        for rect, sym, label, col in self.pal_rects:
            # Latar swatch
            pygame.draw.rect(s, col, rect, border_radius=4)
            if sym == self.selected_tile:
                pygame.draw.rect(s, SEL_BORDER, rect, 3, border_radius=4)
            else:
                pygame.draw.rect(s, BORDER, rect, 1, border_radius=4)

            # Sprite atau glyph simbol
            if sym in pal_tile_anims:
                spr = pal_tile_anims[sym][0]
                cx  = rect.x + (rect.width - PAL_SPRITE_SIZE) // 2
                s.blit(spr, (cx, rect.y + 4))
            elif sym in pal_tile_sprites:
                cx = rect.x + (rect.width - PAL_SPRITE_SIZE) // 2
                s.blit(pal_tile_sprites[sym], (cx, rect.y + 4))
            else:
                sym_lbl = self.fonts["md"].render(sym, True, (255, 255, 255))
                s.blit(sym_lbl, sym_lbl.get_rect(centerx=rect.centerx, y=rect.y + 6))

            # Label nama — pil gelap dibatasi lebar tile, teks putih
            name_lbl = self.fonts["xs"].render(label, True, (240, 240, 240))
            lw, lh   = name_lbl.get_size()
            pill_w   = min(lw + 8, rect.width)          # tidak pernah lebih lebar dari swatch
            pill     = pygame.Surface((pill_w, lh + 2), pygame.SRCALPHA)
            pill.fill((0, 0, 0, 150))
            pill_x   = rect.centerx - pill_w // 2
            pill_y   = rect.bottom - lh - 5
            s.blit(pill, (pill_x, pill_y))
            clip_before = s.get_clip()
            s.set_clip(pygame.Rect(pill_x + 2, pill_y, pill_w - 4, lh + 2))
            s.blit(name_lbl, (pill_x + 4, pill_y + 1))
            s.set_clip(clip_before)

        # ── Bilah atas ───────────────────────────────────────────────────────────
        pygame.draw.rect(s, BG_CANVAS, (0, 0, self.W, TOP_BAR_H))
        pygame.draw.line(s, BORDER, (0, TOP_BAR_H), (self.W, TOP_BAR_H), 1)

        map_name = os.path.splitext(os.path.basename(self.map_path))[0]
        title = self.fonts["md"].render(
            f"{map_name}   {self.cols}×{self.rows}", True, TEXT)
        s.blit(title, title.get_rect(centerx=self.W//2, centery=TOP_BAR_H//3))

        hint = self.fonts["xs"].render(
            "LClick: paint   RClick: erase   Scroll: zoom   Mid-drag: pan   Ctrl+S: save",
            True, TEXT)
        s.blit(hint, hint.get_rect(centerx=self.W//2, centery=TOP_BAR_H*2//3))

        self.btn_save.draw(s)
        self.btn_back.draw(s)

        # Umpan balik tersimpan / kesalahan
        if self.saved_timer > 0:
            msg = self.fonts["sm"].render("Saved!", True, (80, 220, 80))
            s.blit(msg, msg.get_rect(right=self.W - 160, centery=TOP_BAR_H // 3))
        if self.error_msg:
            msg = self.fonts["sm"].render(self.error_msg, True, (220, 80, 80))
            s.blit(msg, msg.get_rect(right=self.W - 160, centery=TOP_BAR_H // 3))

        pygame.display.flip()


# ── Pembantu pembuatan grid ──────────────────────────────────────────────────────

def make_empty_grid(cols: int, rows: int) -> list:
    """
    Buat grid kosong yang seluruhnya diisi dengan dinding '#'.
    Pengguna memulai dengan blok solid dan melukis jalur terbuka,
    yang lebih aman daripada grid terbuka yang mungkin tidak memiliki batas.
    """
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            row.append("#")   # semua sel dimulai sebagai dinding — pengguna mengukir labirin
        grid.append(row)
    return grid


def load_grid(path: str) -> list:
    """Baca file peta .txt menjadi daftar 2D, menghapus baris kosong dan mengisi baris hingga lebar yang sama."""
    with open(path, "r") as f:
        lines = [line.rstrip("\n") for line in f]
    while lines and not lines[0].strip(): lines.pop(0)
    while lines and not lines[-1].strip(): lines.pop()
    max_w = max(len(l) for l in lines)
    return [list(l.ljust(max_w, "#")) for l in lines]


def save_grid(path: str, grid: list):
    """Tulis grid 2D kembali ke file .txt, satu baris per baris."""
    os.makedirs(MAPS_DIR, exist_ok=True)
    with open(path, "w") as f:
        for row in grid:
            f.write("".join(row) + "\n")


# ── Titik masuk ───────────────────────────────────────────────────────────────

def run_editor(surface, sounds=None):
    """
    Titik masuk editor tingkat atas yang dipanggil dari main.py.
    Menjalankan loop luar yang berpindah antara tiga layar editor.
    Mengembalikan "quit" atau "back" untuk memberi sinyal ke main.py apa yang harus dilakukan.

    Alur transisi layar:
      list  → "new"     → new  → "created" → editor
      list  → "edit"    → editor
      editor → "back"   → list
      any   → "quit"    → keluar ke OS
    """
    pygame.font.init()
    # Set font bersama yang diteruskan ke setiap layar agar semuanya menggunakan jenis huruf yang sama.
    fonts = {
        "lg": pygame.font.Font("assets/font.ttf", 36),
        "md": pygame.font.Font("assets/font.ttf", 22),
        "sm": pygame.font.Font("assets/font.ttf", 17),
        "xs": pygame.font.Font("assets/font.ttf", 13),
    }

    screen_name = "list"

    while True:
        if screen_name == "list":
            result = MapListScreen(surface, fonts, sounds=sounds).run()
            action = result[0]
            if action == "quit":   return "quit"
            if action == "back":   return "back"
            if action == "new":    screen_name = "new"
            if action == "edit":
                # Muat peta yang dipilih dan langsung masuk ke editor
                path = result[1]
                grid = load_grid(path)
                screen_name = "editor"
                editor_path = path
                editor_grid = grid

        elif screen_name == "new":
            result = NewMapScreen(surface, fonts, sounds=sounds).run()
            action = result[0]
            if action == "quit":  return "quit"
            if action == "back":  screen_name = "list"
            if action == "created":
                # Buat grid kosong, simpan segera, lalu buka editor
                _, name, cols, rows = result
                path = os.path.join(MAPS_DIR, name + ".txt")
                grid = make_empty_grid(cols, rows)
                save_grid(path, grid)   # tulis file agar ada sebelum pengeditan
                editor_path = path
                editor_grid = grid
                screen_name = "editor"

        elif screen_name == "editor":
            result = EditorScreen(surface, fonts, editor_path, editor_grid, sounds=sounds).run()
            if result == "quit": return "quit"
            if result == "back": screen_name = "list"   # kembali ke daftar peta setelah pengeditan