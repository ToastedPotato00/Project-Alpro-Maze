"""
tiles.py — ice removed
"""

TILE_COLORS = {
    "#": (30,  30,  35),
    "%": (80,  55,  30),
    ".": (60,  55,  50),
    "M": (90,  70,  20),
    "F": (210,  70,  20),
    "R": (60,  180,  80),
    "T": (140,  60, 200),
    "t": (180, 100, 220),
    "K": (240, 200,  40),
    "S": (40,  180,  80),
    "G": (240, 200,  40),
}

DEFAULT_COLOR = (200, 0, 200)

STEP_COST = {
    ".": 1,
    "M": 3,
    "F": 1,
    "R": 1,
    "T": 1,
    "t": 1,
    "K": 0,
    "%": 1,
    "S": 0,
    "G": 0,
}

MUD_FREEZE_FRAMES = 2
FIRE_DAMAGE  = 25
REGEN_HEAL   = 15
REGEN_CAP    = 100


def get_color(symbol: str):
    return TILE_COLORS.get(symbol, DEFAULT_COLOR)

def is_wall(symbol: str) -> bool:
    return symbol in ("#", "%")

def is_passable(symbol: str, keys: int = 0) -> bool:
    if symbol == "#":
        return False
    if symbol == "%" and keys == 0:
        return False
    return True

def get_step_cost(symbol: str) -> int:
    return STEP_COST.get(symbol, 1)

def build_teleporter_map(grid) -> dict:
    T_cells, t_cells = [], []
    for r, row in enumerate(grid):
        for c, sym in enumerate(row):
            if sym == "T": T_cells.append((r, c))
            elif sym == "t": t_cells.append((r, c))
    teleporters = {}
    for a, b in zip(T_cells, t_cells):
        teleporters[a] = b
        teleporters[b] = a
    return teleporters

def apply_tile_effect(symbol: str, player, grid, teleporter_map: dict):
    result = {
        "freeze_frames": 0,
        "teleported_to": None,
        "key_picked_up": False,
        "wall_broken":   False,
        "step_cost":     get_step_cost(symbol),
    }
    if symbol == "F":
        player.hp -= FIRE_DAMAGE
    elif symbol == "R":
        player.hp = min(REGEN_CAP, player.hp + REGEN_HEAL)
    elif symbol == "M":
        result["freeze_frames"] = MUD_FREEZE_FRAMES
    elif symbol in ("T", "t"):
        dest = teleporter_map.get((player.row, player.col))
        if dest:
            player.set_position(*dest)
            result["teleported_to"] = dest
    elif symbol == "K":
        player.keys += 1
        grid[player.row][player.col] = "."
        result["key_picked_up"] = True
        result["step_cost"] = 0
    return result