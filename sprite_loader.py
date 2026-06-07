"""
sprite_loader.py — memuat semua aset visual dan mengembalikannya dalam satu dict.

Tiga sumber aset digunakan:
  1. Spritesheet Kenney Tiny Dungeon (tilemap_packed.png)
     Tile statis 16×16 yang diiris berdasarkan koordinat grid.
  2. PNG individual 0x72 Dungeon Tileset II
     Frame animasi lari/diam/terkena knight (satu PNG per frame).
     Juga menyediakan tile lantai dan tile dinding rusak dari lembar atlas.
  3. Strip PNG kustom di assets/custom/
     Setiap PNG adalah strip horizontal dari CUSTOM_ANIM_FRAMES frame untuk
     tile animasi (api, lumpur, regen, teleporter, kunci).

load_sprites() mengembalikan:
  {
    "tiles":      {simbol: Surface},            # sprite tile statis
    "tile_anims": {simbol: [Surface, ...]},     # sprite tile animasi
    "bot":        {"run": [...], "idle": [...], "hit": [...]}  # frame bot
  }

Semua bagian bersifat opsional — pemanggil kembali ke persegi panjang berwarna jika
file sumber mana pun hilang atau gagal dimuat.
"""

import os
import pygame

# ── Asset paths ───────────────────────────────────────────────────────────────
SHEET_PATH    = "assets/kenney_tiny_dungeon/tilemap_packed.png"
NATIVE_SIZE   = 16   # setiap sel dalam spritesheet Kenney berukuran 16×16 px

FRAMES_DIR    = "assets/0x72_DungeonTilesetII_v1.7/frames"
KNIGHT_GENDER = "m"   # ubah ke "f" untuk varian knight perempuan

# Atlas lantai 0x72 adalah grid autotile 7×7; (3,1) adalah tile terisolasi biasa.
FLOOR_SHEET_PATH  = "assets/0x72_DungeonTilesetII_v1.7/atlas_floor-16x16.png"
FLOOR_TILE_COORD  = (3, 1)   # (kolom, baris) ke dalam atlas lantai

# Tile dinding rusak diiris dari atlas dinding tinggi (sel 16×32).
BROKEN_WALL_PATH  = "assets/0x72_DungeonTilesetII_v1.7/atlas_walls_high-16x32.png"
BROKEN_TILE_COORD = (12, 6.5)

# Tile animasi kustom — setiap file adalah strip horizontal dari 5 frame.
CUSTOM_DIR         = "assets/custom"
CUSTOM_ANIM_FRAMES = 5
CUSTOM_TILE_ANIMS  = {
    "F": "fire.png",
    "R": "regen.png",
    "M": "mud.png",
    "T": "teleport b.png",
    "t": "teleport p.png",
    "K": "key.png"
}

# ── Koordinat spritesheet ───────────────────────────────────────────────────
# Setiap nilai adalah (kolom_grid, baris_grid) — diindeks mulai 0 ke dalam sheet Kenney.
# Sheet berukuran 12 kolom × 11 baris, 16 px per sel.
# Lantai ('.') dan dinding rusak ('%') digantikan di bawah oleh atlas 0x72.
TILE_SPRITE_COORDS = {
    "#": (4, 3),     # dinding batu gelap
    ".": (1, 4),     # lantai batu (digantikan oleh atlas 0x72 di bawah)
    "%": (2, 9),     # dinding retak/yang bisa dihancurkan (digantikan oleh atlas 0x72 di bawah)
    "M": (0, 1),     # lumpur
    "F": (3, 1),     # api/obor
    "R": (5, 0),     # regen
    "T": (4, 1),     # teleporter A
    "t": (5, 1),     # teleporter B
    "K": (4, 0),     # kunci
    "S": (9, 2),     # tile mulai (gaya lantai kayu)
    "G": (5, 7.1),   # tile tujuan (peti)
}


def load_sprites(tile_size: int):
    """
    Muat semua aset sprite yang diskalakan ke tile_size × tile_size.
    Mengembalikan dict sprite gabungan, atau None jika tidak ada yang berhasil dimuat.
    Pemanggil (MapRenderer, Player.draw) memeriksa None dan menggunakan rect berwarna sebagai gantinya.
    """
    sprites = {"tiles": {}, "bot": {}}

    # ── Langkah 1: Tile statis dari spritesheet Kenney ──────────────────────────
    if os.path.isfile(SHEET_PATH):
        try:
            sheet = pygame.image.load(SHEET_PATH).convert_alpha()
            for symbol, (gc, gr) in TILE_SPRITE_COORDS.items():
                sprites["tiles"][symbol] = _slice(sheet, gc, gr, tile_size)
        except pygame.error:
            pass

    # ── Langkah 2: Ganti tile lantai dengan atlas 0x72 ───────────────────────────
    # Lantai 0x72 terlihat lebih baik dari Kenney, jadi ganti jika tersedia.
    if os.path.isfile(FLOOR_SHEET_PATH):
        try:
            floor_sheet = pygame.image.load(FLOOR_SHEET_PATH).convert_alpha()
            gc, gr      = FLOOR_TILE_COORD
            sprites["tiles"]["."] = _slice(floor_sheet, gc, gr, tile_size)
        except pygame.error:
            pass

    # ── Langkah 3: Ganti tile dinding rusak dengan atlas 0x72 ─────────────────────
    if os.path.isfile(BROKEN_WALL_PATH):
        try:
            wall_sheet = pygame.image.load(BROKEN_WALL_PATH).convert_alpha()
            gc, gr      = BROKEN_TILE_COORD
            sprites["tiles"]["%"] = _slice(wall_sheet, gc, gr, tile_size)
        except pygame.error:
            pass

    # ── Langkah 4: Frame animasi bot (PNG knight 0x72) ──────────────────────
    knight = _load_knight_frames(tile_size)
    if knight:
        sprites["bot"] = knight

    # ── Langkah 5: Strip tile animasi kustom ───────────────────────────────────
    tile_anims = _load_custom_tile_anims(tile_size)
    if tile_anims:
        sprites["tile_anims"] = tile_anims

    # Kembalikan None jika tidak ada yang dimuat agar pemanggil tahu untuk menggunakan rendering cadangan
    return sprites if (sprites["tiles"] or sprites["bot"] or sprites.get("tile_anims")) else None


def _load_knight_frames(tile_size: int) -> dict | None:
    """
    Muat ketiga set animasi knight dari file PNG individual.
    Mengembalikan {"run": [Surface,...], "idle": [Surface,...], "hit": [Surface]}
    atau None jika ada file yang hilang (semua atau tidak sama sekali — set parsial terlihat buruk).
    """
    base = os.path.join(FRAMES_DIR, f"knight_{KNIGHT_GENDER}")
    anim_defs = {
        "run":  [f"{base}_run_anim_f{i}.png"  for i in range(4)],
        "idle": [f"{base}_idle_anim_f{i}.png" for i in range(4)],
        "hit":  [f"{base}_hit_anim_f0.png"],   # hanya satu frame terkena
    }
    result = {}
    for anim_name, paths in anim_defs.items():
        frames = []
        for path in paths:
            if not os.path.isfile(path):
                return None   # batalkan seluruh pemuatan sprite bot jika ada file yang hilang
            try:
                img = pygame.image.load(path).convert_alpha()
                frames.append(pygame.transform.scale(img, (tile_size, tile_size)))
            except pygame.error:
                return None
        result[anim_name] = frames
    return result


def _load_custom_tile_anims(tile_size: int) -> dict:
    """
    Muat sprite tile animasi dari strip PNG horizontal.
    Setiap strip memiliki CUSTOM_ANIM_FRAMES frame berukuran sama berdampingan.
    Mengirisnya secara individual dan menskalakan masing-masing ke tile_size × tile_size.
    File yang hilang dilewati; tile yang berhasil dimuat dikembalikan.
    """
    result = {}
    for symbol, filename in CUSTOM_TILE_ANIMS.items():
        path = os.path.join(CUSTOM_DIR, filename)
        if not os.path.isfile(path):
            continue
        try:
            sheet   = pygame.image.load(path).convert_alpha()
            w, h    = sheet.get_size()
            frame_w = w // CUSTOM_ANIM_FRAMES   # lebar setiap frame individual
            frames  = []
            for i in range(CUSTOM_ANIM_FRAMES):
                # Ekstrak satu frame dengan mem-blit sub-rect ke permukaan baru
                src = pygame.Rect(i * frame_w, 0, frame_w, h)
                raw = pygame.Surface((frame_w, h), pygame.SRCALPHA)
                raw.blit(sheet, (0, 0), src)
                frames.append(pygame.transform.scale(raw, (tile_size, tile_size)))
            result[symbol] = frames
        except pygame.error:
            pass
    return result


def _slice(sheet: pygame.Surface, grid_col: int, grid_row: int,
           tile_size: int) -> pygame.Surface:
    """
    Ekstrak tile 16×16 tunggal dari spritesheet berdasarkan koordinat grid,
    lalu skalakan ke tile_size × tile_size.
    grid_col dan grid_row adalah posisi sel yang diindeks mulai 0 dalam grid sheet.
    """
    src_rect = pygame.Rect(
        grid_col * NATIVE_SIZE,
        grid_row * NATIVE_SIZE,
        NATIVE_SIZE,
        NATIVE_SIZE,
    )
    # Blit ke permukaan transparan terlebih dahulu agar alpha dipertahankan dengan benar
    raw = pygame.Surface((NATIVE_SIZE, NATIVE_SIZE), pygame.SRCALPHA)
    raw.blit(sheet, (0, 0), src_rect)
    return pygame.transform.scale(raw, (tile_size, tile_size))
