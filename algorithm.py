from tiles import is_passable, get_step_cost, apply_tile_effect, build_teleporter_map

# (row_delta, col_delta) for UP, DOWN, LEFT, RIGHT — order determines which direction is tried first
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]



def backtracking_backtrack(grid, player, start, goal, diff=None):
    # Orchestrator for classic backtracking — called ONCE, never recurses.
    # Kicks off the recursive search, then handles replay after the goal is found.
    teleporter_map = build_teleporter_map(grid)
    visited    = set()
    visited.add(start)          # pre-mark start so the bot can never loop back to it
    path       = []             # stack of saved states; used to undo moves on backtrack
    step_seq   = []             # records the winning sequence of positions for replay
    found_flag = [False]        # list (not bool) so recursive calls can mutate it in-place
    player.set_position(*start)

    # All recursion and yielding happens inside here — yields move/backtrack to main.py
    yield from _backtracking(grid, player, start, goal, visited, path, step_seq,
                    teleporter_map, found_flag, diff)

    if not found_flag[0]:
        yield ("no_solution", player.row, player.col, {})
        return

    # Undo all grid mutations (broken walls, picked keys) accumulated during search
    _restore_grid(grid, path)
    start_hp = diff["start_hp"] if diff else 100
    # Walk the saved step_seq from start — this is the clean visual replay the player sees
    yield from _replay(grid, player, start, step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def backtracking_chained(grid, player, start, goals, diff=None):
    # Orchestrator for multi-goal maps — runs one independent search per goal in order.
    # Goal order is determined by find_tile() which scans top-to-bottom, left-to-right.
    teleporter_map = build_teleporter_map(grid)
    player.set_position(*start)
    current_pos = start

    full_step_seq = []  # accumulates steps from every segment for one big replay at the end
    all_paths     = []  # saves each segment's path stack for _restore_grid after all done

    for seg_idx, goal in enumerate(goals):
        # Each segment gets a fresh search state — visited/path/found_flag reset each loop
        # player.hp, player.keys, player.steps carry over from the previous segment
        visited    = {current_pos}
        path       = []
        step_seq   = []
        found_flag = [False]

        yield from _backtracking_segment(grid, player, current_pos, goal,
                                 visited, path, step_seq, teleporter_map, found_flag, diff)

        if found_flag[0]:
            full_step_seq.extend(step_seq)          # stitch this segment into the full journey
            all_paths.append(path)
            current_pos = (player.row, player.col)  # next segment starts where this one ended
            if seg_idx < len(goals) - 1:
                yield ("segment_found", player.row, player.col,
                       {"segment": seg_idx, "total": len(goals)})
        else:
            # Any single segment failing ends the whole chain — no skipping to the next goal
            yield ("no_solution", player.row, player.col, {})
            return

    # Restore all grid mutations from all segments at once before replay
    for seg_path in all_paths:
        _restore_grid(grid, seg_path)

    start_hp = diff["start_hp"] if diff else 100
    # Replay the entire stitched journey from start through every goal in one shot
    yield from _replay(grid, player, start, full_step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def backtracking_optimize(grid, player, start, goal, diff=None):
    # Orchestrator for exhaustive backtracking — explores ALL possible paths, scores each,
    # then replays the highest scored one.
    teleporter_map = build_teleporter_map(grid)
    visited  = set()
    visited.add(start)
    path     = []
    step_seq = []
    player.set_position(*start)

    # Manhattan = theoretical minimum steps (straight-line row+col distance, no obstacles)
    # Used in scoring to measure how direct a path was
    manhattan      = abs(goal[0] - start[0]) + abs(goal[1] - start[1])
    total_keys     = sum(row.count("K") for row in grid)
    max_hp         = diff["start_hp"] if diff else 100

    weights = diff["score_weights"] if diff else (5, 3, 2)
    # best tracks the highest scored path found so far across all explorations
    best = {"score": None, "step_seq": None,
            "manhattan": manhattan, "total_keys": total_keys,
            "max_hp": max_hp, "weights": weights}

    # Never exits early — exhausts every possible path before finishing
    yield from _backtracking_all(grid, player, start, goal, visited, path, step_seq,
                        teleporter_map, best, diff)

    if best["score"] is None:
        yield ("no_solution", player.row, player.col, {})
        return

    # No _restore_grid needed — exhaustive backtracking already fully restored the grid
    start_hp = diff["start_hp"] if diff else 100
    # Replay only the best scoring path
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
    # Resets player to start and walks step_seq cleanly.
    # replay_start wipes the visual trail in main.py; each replay step re-paints it gold.
    player.set_position(*start)
    player.hp           = start_hp
    player.keys         = 0
    player.steps        = 0
    player.is_backtrack = False

    payload = {"score": score} if score is not None else {}
    yield ("replay_start", start[0], start[1], payload)

    for nr, nc in step_seq:
        wall_broken_in_replay = grid[nr][nc] == "%" and player.keys > 0
        if wall_broken_in_replay:
            player.keys  -= 1
            grid[nr][nc]  = "."

        player.set_position(nr, nc)
        sym   = grid[player.row][player.col]
        extra = apply_tile_effect(sym, player, grid, tmap, diff)
        player.steps += extra["step_cost"]
        if wall_broken_in_replay:
            extra["wall_broken"] = True

        yield ("replay", player.row, player.col, extra)


# ── Internal backtracking helpers ─────────────────────────────────────────────

def _backtracking(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
    if pos == goal:
        # Signal every recursive caller to unwind immediately — no more moves or yields
        found_flag[0] = True
        return

    r, c = pos

    # Try all 4 directions from the current cell one by one
    for dr, dc in DIRECTIONS:
        # Calculate the coordinate of the neighboring cell in this direction
        nr, nc = r + dr, c + dc

        # Skip if this cell is already on the current active path — prevents loops.
        # visited only contains the current active path — cells are discarded on backtrack,
        # so other branches can still enter a cell that was previously explored and abandoned
        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        # Skip walls (#) and locked doors (% with no keys)
        if not is_passable(target, player.keys):
            continue

        # ── Pre-move: snapshot current state ──────────────────────────────────
        # Save everything we might need to undo if this direction turns out to be a dead end
        keys_before     = player.keys
        hp_before       = player.hp
        steps_before    = player.steps
        wall_broken_at  = None   # will be set if we break a % wall this move
        key_restored_at = None   # will be set if we pick up a K key this move

        # If the target is a breakable wall and we have a key, consume the key and open it
        if target == "%" and player.keys > 0:
            player.keys    -= 1
            grid[nr][nc]    = "."
            wall_broken_at  = (nr, nc)  # remember which cell to restore on backtrack

        # ── Move: physically step onto the new cell ────────────────────────────
        player.set_position(nr, nc)

        # Apply whatever the tile does: fire damage, mud freeze, regen heal,
        # teleport to partner, or key pickup. Returns an extra{} dict with results.
        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap, diff)
        if wall_broken_at:
            extra["wall_broken"] = True

        # If a key was picked up, record its cell so we can restore it on backtrack
        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        # final_pos may differ from (nr, nc) if a teleporter moved the player elsewhere
        final_pos = (player.row, player.col)

        # ── Commit this move to all tracking structures ────────────────────────
        visited.add(final_pos)   # lock cell into the current path
        # Store where we came from + full pre-move state so backtrack can undo everything
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))
        step_seq.append((nr, nc))  # record step for replay later (uses original target, not teleport dest)

        # ── Yield to main.py — execution pauses here until next(gen) is called ─
        yield ("move", player.row, player.col, extra)

        if player.hp <= 0:
            # Tile damage killed the player — undo this move and try the next direction
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

        # ── Recurse: go deeper from the new position ───────────────────────────
        # All further exploring (and their yields) happen inside this call
        yield from _backtracking(grid, player, final_pos, goal, visited, path,
                        step_seq, tmap, found_flag, diff)

        # Goal was found somewhere deeper — propagate the exit upward without undoing anything
        if found_flag[0]:
            return

        # ── Backtrack: this direction was a dead end ───────────────────────────
        # The recursive call returned without finding the goal.
        # Undo everything this move did: restore grid, player state, and tracking structures,
        # then let the for loop continue to try the next direction.
        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
            visited.discard(final_pos)  # removed so other branches can enter this cell

            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # restore broken wall
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K" # restore picked-up key
                player.keys -= 1

            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)   # move player back to where we came from

            yield ("backtrack", r, c, {})
        else:
            return


def _backtracking_all(grid, player, pos, goal, visited, path, step_seq, tmap, best, diff=None):
    # Exhaustive version — no found_flag, never exits early on goal.
    # Every path that reaches the goal is scored; the best is saved in best{}.
    if pos == goal:
        # Score this path on three ratios, each 0.0–1.0, weighted by difficulty config
        keys_spent  = sum(1 for e in path if e[5] is not None)
        hp_ratio    = player.hp / best["max_hp"]                              # HP remaining
        step_ratio  = best["manhattan"] / player.steps if player.steps > 0 else 1.0  # path directness
        step_ratio  = min(step_ratio, 1.0)
        if best["total_keys"] > 0:
            key_ratio = 1.0 - keys_spent / best["total_keys"]                # keys conserved
        else:
            key_ratio = 1.0
        w_hp, w_step, w_key = best["weights"]
        score   = round((w_hp * hp_ratio + w_step * step_ratio + w_key * key_ratio) * 10, 1)
        is_best = best["score"] is None or score > best["score"]
        if is_best:
            best["score"]    = score
            best["step_seq"] = list(step_seq)  # copy — step_seq keeps changing as we explore
        yield ("candidate", pos[0], pos[1], {"score": score, "is_best": is_best})
        return  # returns to caller which ALWAYS backtracks — unlike classic which exits here

    r, c = pos

    # Same move/backtrack loop as _backtracking — try all 4 directions one by one
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        if not is_passable(target, player.keys):
            continue

        # Snapshot state before moving so we can fully undo this move later
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
        if wall_broken_at:
            extra["wall_broken"] = True

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
            # Dead from tile damage — undo and try the next direction
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

        # Recurse deeper — may hit the goal and yield a "candidate", or exhaust and return
        yield from _backtracking_all(grid, player, final_pos, goal,
                             visited, path, step_seq, tmap, best, diff)

        # No found_flag check here — ALWAYS backtrack regardless of whether goal was reached,
        # so we continue exploring every other possible path from this position.
        # This is the key difference from _backtracking which would return early on found.
        path.pop()
        step_seq.pop()
        visited.discard(final_pos)   # free this cell so sibling branches can use it

        if wall_broken_at:
            grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # restore broken wall
        if key_restored_at:
            grid[key_restored_at[0]][key_restored_at[1]] = "K" # restore picked-up key
            player.keys -= 1

        player.keys  = keys_before
        player.hp    = hp_before
        player.steps = steps_before
        player.set_position(r, c)   # move player back to current position

        yield ("backtrack", r, c, {})


def _backtracking_segment(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
    # Identical logic to _backtracking — used by chained so each segment has its own found_flag.
    # The only difference is this function recurses into itself instead of _backtracking.
    if pos == goal:
        # Segment goal reached — signal this segment's found_flag and stop recursing
        found_flag[0] = True
        return

    r, c = pos

    # Try all 4 directions from the current cell one by one
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        if not is_passable(target, player.keys):
            continue

        # Snapshot state before moving so we can fully undo this move later
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
        if wall_broken_at:
            extra["wall_broken"] = True

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
            # Dead from tile damage — undo and try the next direction
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

        # Recurse deeper — same found_flag is passed so the signal reaches all levels
        yield from _backtracking_segment(grid, player, final_pos, goal,
                                  visited, path, step_seq, tmap, found_flag, diff)

        # Goal found somewhere deeper — propagate exit upward without undoing anything
        if found_flag[0]:
            return

        # Branch exhausted — undo this move, restore everything, try next direction
        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
            visited.discard(final_pos)  # free cell for other branches

            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # restore broken wall
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K" # restore picked-up key
                player.keys -= 1

            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)

            yield ("backtrack", r, c, {})
        else:
            return
