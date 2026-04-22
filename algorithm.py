"""
algorithm.py — Phase 4
DFS backtracking with full tile mechanics:
  - step counter
  - fire damage + HP tracking
  - mud freeze frames
  - ice sliding
  - teleporters
  - key pickup
  - broken wall (key consumed / restored on backtrack)

Yields tuples:
  ("move",        row, col, extra)
  ("backtrack",   row, col, extra)
  ("found",       row, col, extra)
  ("no_solution", -1,  -1,  {})

extra dict always contains:
  step_cost, freeze_frames, teleported_to, key_picked_up, wall_broken
"""

from tiles import is_passable, get_step_cost, apply_tile_effect, build_teleporter_map

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def dfs_backtrack(grid, player, start, goal):
    teleporter_map = build_teleporter_map(grid)
    visited = set()
    visited.add(start)
    path = []   # (prev_r, prev_c, keys_before, hp_before, wall_broken_at, key_restored_at, steps_before)

    player.set_position(*start)

    yield from _dfs(grid, player, start, goal, visited, path, teleporter_map)


def _dfs(grid, player, pos, goal, visited, path, tmap):
    if pos == goal:
        yield ("found", pos[0], pos[1], {})
        return

    r, c = pos

    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]

        if not is_passable(target, player.keys):
            continue

        # --- Snapshot state before entry ---
        keys_before  = player.keys
        hp_before    = player.hp
        steps_before = player.steps

        wall_broken_at  = None
        key_restored_at = None

        # Broken wall: consume key, open tile
        if target == "%" and player.keys > 0:
            player.keys -= 1
            grid[nr][nc]   = "."
            wall_broken_at = (nr, nc)

        # --- Move bot ---
        player.set_position(nr, nc)

        # --- Ice: slide until wall ---
        if target == "I":
            nr, nc = _slide(grid, player, dr, dc, tmap)

        # --- Apply tile effect (fire, mud, teleporter, key pickup) ---
        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap)

        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        # Step cost
        player.steps += extra["step_cost"]

        final_pos = (player.row, player.col)
        visited.add(final_pos)
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))

        yield ("move", player.row, player.col, extra)

        # Recurse
        yield from _dfs(grid, player, final_pos, goal, visited, path, tmap)

        # Check if we should backtrack
        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            visited.discard(final_pos)

            # Restore broken wall
            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"

            # Restore picked-up key (put K back, decrement inventory)
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K"
                player.keys -= 1

            # Restore snapshots
            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)

            yield ("backtrack", r, c, {})
        else:
            return


def _slide(grid, player, dr, dc, tmap):
    """
    Slide the player in direction (dr, dc) until the next cell is a wall.
    Returns the final (row, col) after sliding.
    All intermediate cells are entered silently (no yields — caller handles display).
    """
    while True:
        nr = player.row + dr
        nc = player.col + dc
        if not (0 <= nr < len(grid) and 0 <= nc < len(grid[0])):
            break
        if not is_passable(grid[nr][nc], player.keys):
            break
        player.set_position(nr, nc)
        # Stop sliding if we leave the ice
        if grid[nr][nc] != "I":
            break
    return player.row, player.col