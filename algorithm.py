"""
algorithm.py — ice sliding removed
"""

from tiles import is_passable, get_step_cost, apply_tile_effect, build_teleporter_map

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def dfs_backtrack(grid, player, start, goal):
    teleporter_map = build_teleporter_map(grid)
    visited = set()
    visited.add(start)
    path = []
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

        keys_before  = player.keys
        hp_before    = player.hp
        steps_before = player.steps
        wall_broken_at  = None
        key_restored_at = None

        if target == "%" and player.keys > 0:
            player.keys -= 1
            grid[nr][nc]   = "."
            wall_broken_at = (nr, nc)

        player.set_position(nr, nc)

        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap)

        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        final_pos = (player.row, player.col)
        visited.add(final_pos)
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))

        yield ("move", player.row, player.col, extra)

        yield from _dfs(grid, player, final_pos, goal, visited, path, tmap)

        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            visited.discard(final_pos)

            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K"
                player.keys -= 1

            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)

            yield ("backtrack", r, c, {})
        else:
            return