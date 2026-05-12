"""
algorithm.py — ice sliding removed
"""

from tiles import is_passable, get_step_cost, apply_tile_effect, build_teleporter_map

DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def dfs_backtrack(grid, player, start, goal, diff=None):
    teleporter_map = build_teleporter_map(grid)
    visited    = set()
    visited.add(start)
    path       = []
    step_seq   = []
    found_flag = [False]
    player.set_position(*start)

    yield from _dfs(grid, player, start, goal, visited, path, step_seq,
                    teleporter_map, found_flag, diff)

    if not found_flag[0]:
        yield ("no_solution", player.row, player.col, {})
        return

    _restore_grid(grid, path)
    start_hp = diff["start_hp"] if diff else 100
    yield from _replay(grid, player, start, step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def dfs_chained(grid, player, start, goals, diff=None):
    """Map 2: visit all goals in sequence. HP carries over between segments."""
    teleporter_map = build_teleporter_map(grid)
    player.set_position(*start)
    current_pos = start

    full_step_seq = []
    all_paths     = []

    for seg_idx, goal in enumerate(goals):
        visited    = {current_pos}
        path       = []
        step_seq   = []
        found_flag = [False]

        yield from _dfs_segment(grid, player, current_pos, goal,
                                 visited, path, step_seq, teleporter_map, found_flag, diff)

        if found_flag[0]:
            full_step_seq.extend(step_seq)
            all_paths.append(path)
            current_pos = (player.row, player.col)
            if seg_idx < len(goals) - 1:
                yield ("segment_found", player.row, player.col,
                       {"segment": seg_idx, "total": len(goals)})
        else:
            yield ("no_solution", player.row, player.col, {})
            return

    for seg_path in all_paths:
        _restore_grid(grid, seg_path)

    start_hp = diff["start_hp"] if diff else 100
    yield from _replay(grid, player, start, full_step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def dfs_optimize(grid, player, start, goal, diff=None):
    """Map 3: explore all paths, score each, replay the best."""
    teleporter_map = build_teleporter_map(grid)
    visited  = set()
    visited.add(start)
    path     = []
    step_seq = []
    player.set_position(*start)

    best = {"score": None, "step_seq": None, "min_steps": None}

    yield from _dfs_all(grid, player, start, goal, visited, path, step_seq,
                        teleporter_map, best, diff)

    if best["score"] is None:
        yield ("no_solution", player.row, player.col, {})
        return

    # Grid is already fully restored by exhaustive backtracking — no _restore_grid needed
    start_hp = diff["start_hp"] if diff else 100
    yield from _replay(grid, player, start, best["step_seq"], teleporter_map,
                       score=best["score"], start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {"score": best["score"]})


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _restore_grid(grid, path):
    """Undo grid mutations (broken walls, picked-up keys) recorded in a path stack."""
    for entry in path:
        wall_broken_at, key_restored_at = entry[5], entry[6]
        if wall_broken_at:
            grid[wall_broken_at[0]][wall_broken_at[1]] = "%"
        if key_restored_at:
            grid[key_restored_at[0]][key_restored_at[1]] = "K"


def _replay(grid, player, start, step_seq, tmap, score=None, start_hp=100, diff=None):
    """Reset player to start and walk step_seq, yielding replay_start then replay events."""
    player.set_position(*start)
    player.hp           = start_hp
    player.keys         = 0
    player.steps        = 0
    player.is_backtrack = False

    payload = {"score": score} if score is not None else {}
    yield ("replay_start", start[0], start[1], payload)

    for nr, nc in step_seq:
        if grid[nr][nc] == "%" and player.keys > 0:
            player.keys  -= 1
            grid[nr][nc]  = "."

        player.set_position(nr, nc)
        sym   = grid[player.row][player.col]
        extra = apply_tile_effect(sym, player, grid, tmap, diff)
        player.steps += extra["step_cost"]

        yield ("replay", player.row, player.col, extra)


# ── Internal DFS helpers ───────────────────────────────────────────────────────

def _dfs(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
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

        keys_before     = player.keys
        hp_before       = player.hp
        steps_before    = player.steps
        wall_broken_at  = None
        key_restored_at = None

        if target == "%" and player.keys > 0:
            player.keys    -= 1
            grid[nr][nc]    = "."
            wall_broken_at  = (nr, nc)

        player.set_position(nr, nc)

        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap, diff)

        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        final_pos = (player.row, player.col)
        visited.add(final_pos)
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))
        step_seq.append((nr, nc))

        yield ("move", player.row, player.col, extra)

        if player.hp <= 0:
            path.pop()
            step_seq.pop()
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

        yield from _dfs(grid, player, final_pos, goal, visited, path,
                        step_seq, tmap, found_flag, diff)

        if found_flag[0]:
            return

        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
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


def _dfs_all(grid, player, pos, goal, visited, path, step_seq, tmap, best, diff=None):
    """Exhaustive DFS for Map 3. Never exits early on goal — always backtracks."""
    if pos == goal:
        keys_spent = sum(1 for e in path if e[5] is not None)
        # Track shortest path seen so far to anchor step efficiency
        if best["min_steps"] is None or player.steps < best["min_steps"]:
            best["min_steps"] = player.steps
        step_penalty = player.steps - best["min_steps"]  # 0 on shortest path, grows for longer
        score        = player.hp - step_penalty - keys_spent * 10
        is_best      = best["score"] is None or score > best["score"]
        if is_best:
            best["score"]    = score
            best["step_seq"] = list(step_seq)
        yield ("candidate", pos[0], pos[1], {"score": score, "is_best": is_best})
        return

    r, c = pos

    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        if not is_passable(target, player.keys):
            continue

        keys_before     = player.keys
        hp_before       = player.hp
        steps_before    = player.steps
        wall_broken_at  = None
        key_restored_at = None

        if target == "%" and player.keys > 0:
            player.keys    -= 1
            grid[nr][nc]    = "."
            wall_broken_at  = (nr, nc)

        player.set_position(nr, nc)

        sym   = grid[player.row][player.col]
        extra = apply_tile_effect(sym, player, grid, tmap, diff)

        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        final_pos = (player.row, player.col)
        visited.add(final_pos)
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))
        step_seq.append((nr, nc))

        yield ("move", player.row, player.col, extra)

        if player.hp <= 0:
            path.pop()
            step_seq.pop()
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

        yield from _dfs_all(grid, player, final_pos, goal,
                             visited, path, step_seq, tmap, best, diff)

        # Always backtrack to keep exploring other paths
        path.pop()
        step_seq.pop()
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


def _dfs_segment(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
    """Single segment of chained DFS. Signals completion via found_flag."""
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

        keys_before     = player.keys
        hp_before       = player.hp
        steps_before    = player.steps
        wall_broken_at  = None
        key_restored_at = None

        if target == "%" and player.keys > 0:
            player.keys    -= 1
            grid[nr][nc]    = "."
            wall_broken_at  = (nr, nc)

        player.set_position(nr, nc)

        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap, diff)

        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        final_pos = (player.row, player.col)
        visited.add(final_pos)
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))
        step_seq.append((nr, nc))

        yield ("move", player.row, player.col, extra)

        if player.hp <= 0:
            path.pop()
            step_seq.pop()
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
                                  visited, path, step_seq, tmap, found_flag, diff)

        if found_flag[0]:
            return

        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
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
