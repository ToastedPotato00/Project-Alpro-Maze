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


def dfs_chained(grid, player, start, goals):
    """Map 2: visit all goals in sequence. HP carries over between segments."""
    teleporter_map = build_teleporter_map(grid)
    player.set_position(*start)
    current_pos = start

    for seg_idx, goal in enumerate(goals):
        visited    = {current_pos}
        path       = []
        found_flag = [False]

        yield from _dfs_segment(grid, player, current_pos, goal,
                                 visited, path, teleporter_map, found_flag)

        if found_flag[0]:
            current_pos = (player.row, player.col)
            if seg_idx < len(goals) - 1:
                yield ("segment_found", player.row, player.col,
                       {"segment": seg_idx, "total": len(goals)})
            else:
                yield ("found", player.row, player.col, {})
        else:
            yield ("no_solution", player.row, player.col, {})
            return


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

        if player.hp <= 0:
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
            continue

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


def _dfs_segment(grid, player, pos, goal, visited, path, tmap, found_flag):
    """Single segment of chained DFS. Signals completion via found_flag instead
    of yielding 'found', so the outer dfs_chained controls goal sequencing."""
    if pos == goal:
        found_flag[0] = True
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

        if player.hp <= 0:
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
            continue

        yield from _dfs_segment(grid, player, final_pos, goal,
                                  visited, path, tmap, found_flag)

        if found_flag[0]:
            return  # goal found downstream — unwind without backtracking

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