"""
map_loader.py
Reads a .txt map file and returns:
  - grid  : 2D list of single-character strings (one per tile)
  - tile_size : pixel size to render each tile (auto-scaled to screen)
"""

MAX_SCREEN_W = 1280
MAX_SCREEN_H = 800
MIN_TILE     = 16
DEFAULT_TILE = 32

def load_map(filepath: str, tile_size: int = None):
    """
    Parameters
    ----------
    filepath  : path to the .txt map file
    tile_size : override tile pixel size; if None, auto-calculated

    Returns
    -------
    (grid, tile_size)
      grid      : list[list[str]]  — grid[row][col]
      tile_size : int
    """
    with open(filepath, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    # Strip blank lines at start/end
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()

    # Make all rows the same width (pad with walls)
    max_width = max(len(row) for row in lines)
    grid = [list(row.ljust(max_width, "#")) for row in lines]

    rows = len(grid)
    cols = max_width

    if tile_size is None:
        # Fit inside max screen dimensions
        tile_w = MAX_SCREEN_W // cols
        tile_h = MAX_SCREEN_H // rows
        tile_size = max(MIN_TILE, min(DEFAULT_TILE, tile_w, tile_h))

    return grid, tile_size


def find_tile(grid, symbol: str):
    """Return list of (row, col) positions matching symbol."""
    positions = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == symbol:
                positions.append((r, c))
    return positions