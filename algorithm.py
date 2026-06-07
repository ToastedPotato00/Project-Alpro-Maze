from tiles import is_passable, get_step_cost, apply_tile_effect, build_teleporter_map

# ATAS, BAWAH, KIRI, KANAN  urutan menentukan arah yang dicoba 
DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]



def backtracking_backtrack(grid, player, start, goal, diff=None):
    # backtracking klasik dipanggil SEKALI, tidak pernah rekursi.
    # Memulai pencarian rekursif, lalu menangani replay setelah tujuan ditemukan.
    teleporter_map = build_teleporter_map(grid)
    visited    = set()
    visited.add(start)          # tandai awal terlebih dahulu agar bot tidak pernah kembali ke sana
    path       = []             # stack status tersimpan; digunakan untuk membatalkan gerakan saat mundur
    step_seq   = []             # mencatat urutan posisi pemenang untuk replay
    found_flag = [False]        # list (bukan bool) agar panggilan rekursif dapat mengubahnya langsung
    player.set_position(*start)

    # Semua rekursi dan yield terjadi di dalam sini — yield move/backtrack ke main.py
    yield from _backtracking(grid, player, start, goal, visited, path, step_seq,
                    teleporter_map, found_flag, diff)

    if not found_flag[0]:
        yield ("no_solution", player.row, player.col, {})
        return

    # Batalkan semua mutasi grid (dinding rusak, kunci diambil) yang terkumpul selama pencarian
    _restore_grid(grid, path)
    start_hp = diff["start_hp"] if diff else 100
    # Jalan melalui step_seq tersimpan dari awal — ini adalah replay visual bersih yang dilihat pemain
    yield from _replay(grid, player, start, step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def backtracking_chained(grid, player, start, goals, diff=None):
    # backtracking chained  menjalankan satu pencarian independen per tujuan secara berurutan.
    # Urutan tujuan ditentukan oleh find_tile()
    teleporter_map = build_teleporter_map(grid)
    player.set_position(*start)
    current_pos = start

    full_step_seq = []  # mengumpulkan langkah dari setiap segmen untuk satu replay besar di akhir
    all_paths     = []  # menyimpan stack jalur setiap segmen untuk _restore_grid setelah semua selesai

    for seg_idx, goal in enumerate(goals):
        # Setiap segmen mendapatkan status pencarian baru — visited/path/found_flag direset setiap loop
        # player.hp, player.keys, player.steps terbawa dari segmen sebelumnya
        visited    = {current_pos}
        path       = []
        step_seq   = []
        found_flag = [False]

        yield from _backtracking_segment(grid, player, current_pos, goal,
                                 visited, path, step_seq, teleporter_map, found_flag, diff)

        if found_flag[0]:
            full_step_seq.extend(step_seq)          # gabungkan segmen ini ke perjalanan penuh
            all_paths.append(path)
            current_pos = (player.row, player.col)  # segmen berikutnya dimulai di mana segmen ini berakhir
            if seg_idx < len(goals) - 1:
                yield ("segment_found", player.row, player.col,
                       {"segment": seg_idx, "total": len(goals)})
        else:
            # Kegagalan satu segmen mengakhiri seluruh rantai — tidak ada lompatan ke tujuan berikutnya
            yield ("no_solution", player.row, player.col, {})
            return

    # Pulihkan semua mutasi grid dari semua segmen sekaligus sebelum replay
    for seg_path in all_paths:
        _restore_grid(grid, seg_path)

    start_hp = diff["start_hp"] if diff else 100
    # Replay seluruh perjalanan gabungan dari awal melalui setiap tujuan dalam satu kali
    yield from _replay(grid, player, start, full_step_seq, teleporter_map,
                       start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {})


def backtracking_optimize(grid, player, start, goal, diff=None):
    # Orkestrator untuk backtracking menyeluruh — menjelajahi SEMUA jalur yang mungkin, menilai masing-masing,
    # lalu memutar ulang yang mendapat skor tertinggi.
    teleporter_map = build_teleporter_map(grid)
    visited  = set()
    visited.add(start)
    path     = []
    step_seq = []
    player.set_position(*start)

    # Manhattan = langkah minimum teoritis (jarak garis lurus baris+kolom, tanpa halangan)
    # Digunakan dalam penilaian untuk mengukur seberapa langsung sebuah jalur
    manhattan      = abs(goal[0] - start[0]) + abs(goal[1] - start[1])
    total_keys     = sum(row.count("K") for row in grid)
    max_hp         = diff["start_hp"] if diff else 100

    weights = diff["score_weights"] if diff else (5, 3, 2)
    # best melacak jalur dengan skor tertinggi yang ditemukan sejauh ini di semua eksplorasi
    best = {"score": None, "step_seq": None,
            "manhattan": manhattan, "total_keys": total_keys,
            "max_hp": max_hp, "weights": weights}

    # Tidak pernah keluar lebih awal — menghabiskan setiap jalur yang mungkin sebelum selesai
    yield from _backtracking_all(grid, player, start, goal, visited, path, step_seq,
                        teleporter_map, best, diff)

    if best["score"] is None:
        yield ("no_solution", player.row, player.col, {})
        return

    # Tidak perlu _restore_grid — backtracking menyeluruh sudah memulihkan grid sepenuhnya
    start_hp = diff["start_hp"] if diff else 100
    # Putar ulang hanya jalur dengan skor terbaik
    yield from _replay(grid, player, start, best["step_seq"], teleporter_map,
                       score=best["score"], start_hp=start_hp, diff=diff)
    yield ("found", player.row, player.col, {"score": best["score"]})


# ── Pembantu bersama ─────────────────────────────────────────────────────────────

def _restore_grid(grid, path):
    """Batalkan mutasi grid (dinding rusak, kunci diambil) yang tercatat dalam stack jalur."""
    for entry in path:
        wall_broken_at, key_restored_at = entry[5], entry[6]
        if wall_broken_at:
            grid[wall_broken_at[0]][wall_broken_at[1]] = "%"
        if key_restored_at:
            grid[key_restored_at[0]][key_restored_at[1]] = "K"


def _replay(grid, player, start, step_seq, tmap, score=None, start_hp=100, diff=None):
    # Mengatur ulang pemain ke awal dan menelusuri step_seq secara bersih.
    # replay_start menghapus jejak visual di main.py; setiap langkah replay mengecat ulangnya menjadi emas.
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


# ── Pembantu backtracking internal ─────────────────────────────────────────────

def _backtracking(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
    if pos == goal:
        # Beri sinyal setiap pemanggil rekursif untuk mundur segera — tidak ada lagi gerakan atau yield
        found_flag[0] = True
        return

    r, c = pos

    # Coba semua 4 arah dari sel saat ini satu per satu
    for dr, dc in DIRECTIONS:
        # Hitung koordinat sel tetangga ke arah ini
        nr, nc = r + dr, c + dc

        # Lewati jika sel ini sudah ada di jalur aktif saat ini — mencegah loop.
        # visited hanya berisi jalur aktif saat ini — sel dibuang saat mundur,
        # sehingga cabang lain masih bisa memasuki sel yang sebelumnya dijelajahi dan ditinggalkan
        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        # Lewati dinding (#) dan pintu terkunci (% tanpa kunci)
        if not is_passable(target, player.keys):
            continue

        # ── Pra-gerakan: snapshot status saat ini ──────────────────────────────────
        # Simpan semua yang mungkin perlu dibatalkan jika arah ini ternyata jalan buntu
        keys_before     = player.keys
        hp_before       = player.hp
        steps_before    = player.steps
        wall_broken_at  = None   # akan diatur jika kita menghancurkan dinding % pada gerakan ini
        key_restored_at = None   # akan diatur jika kita mengambil kunci K pada gerakan ini

        # Jika target adalah dinding yang bisa dihancurkan dan kita punya kunci, gunakan kunci dan buka
        if target == "%" and player.keys > 0:
            player.keys    -= 1
            grid[nr][nc]    = "."
            wall_broken_at  = (nr, nc)  # ingat sel mana yang harus dipulihkan saat mundur

        # ── Gerakan: melangkah secara fisik ke sel baru ────────────────────────────
        player.set_position(nr, nc)

        # Terapkan efek tile: kerusakan api, beku lumpur, penyembuhan regen,
        # teleport ke pasangan, atau pengambilan kunci. Mengembalikan dict extra{} dengan hasilnya.
        current_sym = grid[player.row][player.col]
        extra = apply_tile_effect(current_sym, player, grid, tmap, diff)
        if wall_broken_at:
            extra["wall_broken"] = True

        # Jika kunci diambil, catat selnya agar bisa dipulihkan saat mundur
        if extra.get("key_picked_up"):
            key_restored_at = (player.row, player.col)

        player.steps += extra["step_cost"]

        # final_pos mungkin berbeda dari (nr, nc) jika teleporter memindahkan pemain ke tempat lain
        final_pos = (player.row, player.col)

        # ── Komit gerakan ini ke semua struktur pelacak ────────────────────────
        visited.add(final_pos)   # kunci sel ke dalam jalur aktif saat ini
        # Simpan dari mana kita datang + status pra-gerakan penuh agar mundur bisa membatalkan semuanya
        path.append((r, c, keys_before, hp_before, steps_before,
                     wall_broken_at, key_restored_at))
        step_seq.append((nr, nc))  # catat langkah untuk replay nanti (menggunakan target asli, bukan tujuan teleport)

        # ── Yield ke main.py — eksekusi berhenti di sini sampai next(gen) dipanggil ─
        yield ("move", player.row, player.col, extra)

        if player.hp <= 0:
            # Kerusakan tile membunuh pemain — batalkan gerakan ini dan coba arah berikutnya
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

        # ── Rekursi: masuk lebih dalam dari posisi baru ───────────────────────────
        # Semua penjelajahan lebih lanjut (dan yield-nya) terjadi di dalam panggilan ini
        yield from _backtracking(grid, player, final_pos, goal, visited, path,
                        step_seq, tmap, found_flag, diff)

        # Tujuan ditemukan di kedalaman — propagasikan keluar ke atas tanpa membatalkan apa pun
        if found_flag[0]:
            return

        # ── Mundur: arah ini adalah jalan buntu ───────────────────────────
        # Panggilan rekursif kembali tanpa menemukan tujuan.
        # Batalkan semua yang dilakukan gerakan ini: pulihkan grid, status pemain, dan struktur pelacak,
        # lalu biarkan for loop melanjutkan mencoba arah berikutnya.
        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
            visited.discard(final_pos)  # dihapus agar cabang lain dapat memasuki sel ini

            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # pulihkan dinding yang dihancurkan
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K" # pulihkan kunci yang diambil
                player.keys -= 1

            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)   # kembalikan pemain ke posisi semula

            yield ("backtrack", r, c, {})
        else:
            return


def _backtracking_all(grid, player, pos, goal, visited, path, step_seq, tmap, best, diff=None):
    # Versi menyeluruh — tanpa found_flag, tidak pernah keluar lebih awal saat menemukan tujuan.
    # Setiap jalur yang mencapai tujuan dinilai; yang terbaik disimpan di best{}.
    if pos == goal:
        # Nilai jalur ini dengan tiga rasio, masing-masing 0.0–1.0, berbobot oleh konfigurasi kesulitan
        keys_spent  = sum(1 for e in path if e[5] is not None)
        hp_ratio    = player.hp / best["max_hp"]                              # HP tersisa
        step_ratio  = best["manhattan"] / player.steps if player.steps > 0 else 1.0  # kelurusan jalur
        step_ratio  = min(step_ratio, 1.0)
        if best["total_keys"] > 0:
            key_ratio = 1.0 - keys_spent / best["total_keys"]                # kunci yang dihemat
        else:
            key_ratio = 1.0
        w_hp, w_step, w_key = best["weights"]
        score   = round((w_hp * hp_ratio + w_step * step_ratio + w_key * key_ratio) * 10, 1)
        is_best = best["score"] is None or score > best["score"]
        if is_best:
            best["score"]    = score
            best["step_seq"] = list(step_seq)  # salin — step_seq terus berubah saat kita menjelajah
        yield ("candidate", pos[0], pos[1], {"score": score, "is_best": is_best})
        return  # kembali ke pemanggil yang SELALU mundur — berbeda dari klasik yang keluar di sini

    r, c = pos

    # Loop gerak/mundur yang sama seperti _backtracking — coba semua 4 arah satu per satu
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        if not is_passable(target, player.keys):
            continue

        # Rekam snapshot state sebelum bergerak agar bisa membatalkan gerakan ini sepenuhnya nanti
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
            # Mati karena kerusakan tile — batalkan dan coba arah berikutnya
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

        # Rekursi lebih dalam — bisa mencapai tujuan dan yield "candidate", atau habis dan kembali
        yield from _backtracking_all(grid, player, final_pos, goal,
                             visited, path, step_seq, tmap, best, diff)

        # Tidak ada pengecekan found_flag di sini — SELALU mundur terlepas dari apakah tujuan tercapai,
        # sehingga kita terus menjelajahi setiap jalur lain yang mungkin dari posisi ini.
        # Ini adalah perbedaan kunci dari _backtracking yang akan keluar lebih awal saat ditemukan.
        path.pop()
        step_seq.pop()
        visited.discard(final_pos)   # bebaskan sel ini agar cabang saudara dapat menggunakannya

        if wall_broken_at:
            grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # pulihkan dinding yang dihancurkan
        if key_restored_at:
            grid[key_restored_at[0]][key_restored_at[1]] = "K" # pulihkan kunci yang diambil
            player.keys -= 1

        player.keys  = keys_before
        player.hp    = hp_before
        player.steps = steps_before
        player.set_position(r, c)   # kembalikan pemain ke posisi saat ini

        yield ("backtrack", r, c, {})


def _backtracking_segment(grid, player, pos, goal, visited, path, step_seq, tmap, found_flag, diff=None):
    # Logika identik dengan _backtracking — digunakan oleh chained agar setiap segmen punya found_flag sendiri.
    # Perbedaannya hanya fungsi ini merekursi ke dirinya sendiri, bukan ke _backtracking.
    if pos == goal:
        # Tujuan segmen tercapai — sinyal found_flag segmen ini dan hentikan rekursi
        found_flag[0] = True
        return

    r, c = pos

    # Coba semua 4 arah dari sel saat ini satu per satu
    for dr, dc in DIRECTIONS:
        nr, nc = r + dr, c + dc

        if (nr, nc) in visited:
            continue

        target = grid[nr][nc]
        if not is_passable(target, player.keys):
            continue

        # Rekam snapshot state sebelum bergerak agar bisa membatalkan gerakan ini sepenuhnya nanti
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
            # Mati karena kerusakan tile — batalkan dan coba arah berikutnya
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

        # Rekursi lebih dalam — found_flag yang sama diteruskan agar sinyal mencapai semua level
        yield from _backtracking_segment(grid, player, final_pos, goal,
                                  visited, path, step_seq, tmap, found_flag, diff)

        # Tujuan ditemukan di kedalaman — propagasikan keluar ke atas tanpa membatalkan apa pun
        if found_flag[0]:
            return

        # Cabang habis — batalkan gerakan ini, pulihkan semuanya, coba arah berikutnya
        if path and path[-1] == (r, c, keys_before, hp_before, steps_before,
                                  wall_broken_at, key_restored_at):
            path.pop()
            step_seq.pop()
            visited.discard(final_pos)  # bebaskan sel untuk cabang lain

            if wall_broken_at:
                grid[wall_broken_at[0]][wall_broken_at[1]] = "%"   # pulihkan dinding yang dihancurkan
            if key_restored_at:
                grid[key_restored_at[0]][key_restored_at[1]] = "K" # pulihkan kunci yang diambil
                player.keys -= 1

            player.keys  = keys_before
            player.hp    = hp_before
            player.steps = steps_before
            player.set_position(r, c)

            yield ("backtrack", r, c, {})
        else:
            return
