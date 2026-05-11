"""
sprite_loader.py
Loads map tile sprites from the Kenney Tiny Dungeon spritesheet and
bot animation frames from the 0x72 Dungeon Tileset II knight PNGs.
Returns None gracefully on missing files — all callers fall back to colored rects.
"""

import os
import pygame

SHEET_PATH    = "assets/kenney_tiny_dungeon/tilemap_packed.png"
NATIVE_SIZE   = 16   # each cell in the Kenney spritesheet is 16x16 px

FRAMES_DIR    = "assets/0x72_DungeonTilesetII_v1.7/frames"
KNIGHT_GENDER = "m"   # "f" for female variant

# 0x72 floor autotile atlas — 7 cols × 7 rows, 16 px per cell
# (3, 3) is the isolated/plain tile in the center of the autotile grid
FLOOR_SHEET_PATH  = "assets/0x72_DungeonTilesetII_v1.7/atlas_floor-16x16.png"
FLOOR_TILE_COORD  = (3, 1)   # (col, row) — tune if it looks wrong

BROKEN_WALL_PATH = "assets/0x72_DungeonTilesetII_v1.7/atlas_walls_high-16x32.png"
BROKEN_TILE_COORD = (12,6.5)

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

# (grid_col, grid_row) — zero-indexed into the spritesheet grid
#
# Sheet layout (12 cols × 11 rows, 16 px per tile):
#   Cols 0-5, rows 0-3 : Individual dungeon tiles (wall, floor, items)
#   Cols 6-11, rows 0-3: Autotile stone-wall grid (not used here)
#   Rows 4-10           : Character sprites
TILE_SPRITE_COORDS = {
    "#": (4, 3),   # dark stone wall              (col 0, row 0)
    ".": (1, 4),   # stone floor                  (col 1, row 0)
    "%": (2, 9),   # lighter/cracked stone wall   (col 2, row 0)
    "M": (0, 1),   # sandy/mud tile               (col 0, row 2)
    "F": (3, 1),   # fire/torch tile              (col 3, row 1)
    "R": (5, 0),   # regen tile — verify position (col 5, row 0)
    "T": (4, 1),   # teleporter A                 (col 4, row 1)
    "t": (5, 1),   # teleporter B                 (col 5, row 1)
    "K": (4, 0),   # key item                     (col 4, row 0)
    "S": (9, 2),   # start (wooden floor)         (col 0, row 1)
    "G": (5, 7.1),   # goal (chest/object)          (col 3, row 0)
}

def load_sprites(tile_size: int):
    """
    Returns {"tiles": {symbol: Surface}, "bot": {anim: [Surface, ...]}}
    Tile sprites come from the Kenney spritesheet; bot frames from 0x72 individual PNGs.
    Either section can be empty if files are missing — callers fall back to colored rects.
    """
    sprites = {"tiles": {}, "bot": {}}

    # ── Tile sprites (Kenney spritesheet) ────────────────────────────────────
    if os.path.isfile(SHEET_PATH):
        try:
            sheet = pygame.image.load(SHEET_PATH).convert_alpha()
            for symbol, (gc, gr) in TILE_SPRITE_COORDS.items():
                sprites["tiles"][symbol] = _slice(sheet, gc, gr, tile_size)
        except pygame.error:
            pass

    # ── Floor tile override — 0x72 atlas ─────────────────────────────────────
    if os.path.isfile(FLOOR_SHEET_PATH):
        try:
            floor_sheet = pygame.image.load(FLOOR_SHEET_PATH).convert_alpha()
            gc, gr      = FLOOR_TILE_COORD
            sprites["tiles"]["."] = _slice(floor_sheet, gc, gr, tile_size)
        except pygame.error:
            pass
        
    if os.path.isfile(BROKEN_WALL_PATH):
        try:
            wall_sheet = pygame.image.load(BROKEN_WALL_PATH).convert_alpha()
            gc, gr      = BROKEN_TILE_COORD
            sprites["tiles"]["%"] = _slice(wall_sheet, gc, gr, tile_size)
        except pygame.error:
            pass

    # ── Bot animation frames (0x72 knight PNGs) ──────────────────────────────
    knight = _load_knight_frames(tile_size)
    if knight:
        sprites["bot"] = knight

    # ── Custom tile animations (fire.png / regen.png) ─────────────────────────
    tile_anims = _load_custom_tile_anims(tile_size)
    if tile_anims:
        sprites["tile_anims"] = tile_anims

    return sprites if (sprites["tiles"] or sprites["bot"] or sprites.get("tile_anims")) else None


def _load_knight_frames(tile_size: int) -> dict | None:
    """
    Loads knight animation frames from individual PNG files.
    Returns {"run": [...], "idle": [...], "hit": [...]} or None on any failure.
    sprites["bot"] contract: each value is a list of pygame.Surface.
    """
    base = os.path.join(FRAMES_DIR, f"knight_{KNIGHT_GENDER}")
    anim_defs = {
        "run":  [f"{base}_run_anim_f{i}.png"  for i in range(4)],
        "idle": [f"{base}_idle_anim_f{i}.png" for i in range(4)],
        "hit":  [f"{base}_hit_anim_f0.png"],
    }
    result = {}
    for anim_name, paths in anim_defs.items():
        frames = []
        for path in paths:
            if not os.path.isfile(path):
                return None
            try:
                img = pygame.image.load(path).convert_alpha()
                frames.append(pygame.transform.scale(img, (tile_size, tile_size)))
            except pygame.error:
                return None
        result[anim_name] = frames
    return result


def _load_custom_tile_anims(tile_size: int) -> dict:
    """
    Slices each custom PNG (horizontal strip of CUSTOM_ANIM_FRAMES frames) into
    individual surfaces scaled to tile_size × tile_size.
    Returns {symbol: [Surface, ...]} for every file found.
    """
    result = {}
    for symbol, filename in CUSTOM_TILE_ANIMS.items():
        path = os.path.join(CUSTOM_DIR, filename)
        if not os.path.isfile(path):
            continue
        try:
            sheet   = pygame.image.load(path).convert_alpha()
            w, h    = sheet.get_size()
            frame_w = w // CUSTOM_ANIM_FRAMES
            frames  = []
            for i in range(CUSTOM_ANIM_FRAMES):
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
    src_rect = pygame.Rect(
        grid_col * NATIVE_SIZE,
        grid_row * NATIVE_SIZE,
        NATIVE_SIZE,
        NATIVE_SIZE,
    )
    raw = pygame.Surface((NATIVE_SIZE, NATIVE_SIZE), pygame.SRCALPHA)
    raw.blit(sheet, (0, 0), src_rect)
    return pygame.transform.scale(raw, (tile_size, tile_size))
