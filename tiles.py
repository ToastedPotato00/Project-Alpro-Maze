"""
tiles.py — mendefinisikan setiap jenis tile yang digunakan dalam labirin.

Setiap tile diwakili oleh satu karakter dalam file peta .txt.
Modul ini memusatkan semua data tile: warna untuk rendering cadangan,
biaya langkah untuk penilaian, nilai kerusakan/beku per kesulitan, dan fungsi
apply_tile_effect() yang dipanggil semua algoritma setelah setiap gerakan.
"""

# ── Warna cadangan ──────────────────────────────────────────────────────────
# Digunakan oleh MapRenderer ketika gambar sprite tidak tersedia.
# Setiap karakter dipetakan ke tuple RGB.
TILE_COLORS = {
    "#": (30,  30,  35),   # dinding solid — hampir hitam
    "%": (80,  55,  30),   # dinding yang bisa dihancurkan — cokelat
    ".": (60,  55,  50),   # lantai biasa
    "M": (90,  70,  20),   # lumpur — memperlambat bot
    "F": (210,  70,  20),  # api — merusak bot
    "R": (60,  180,  80),  # regen — menyembuhkan bot
    "T": (140,  60, 200),  # pintu masuk teleporter (ungu)
    "t": (180, 100, 220),  # pintu keluar teleporter (ungu muda)
    "K": (240, 200,  40),  # pengambilan kunci — keemasan
    "S": (40,  180,  80),  # posisi mulai
    "G": (240, 200,  40),  # tujuan — keemasan
}

DEFAULT_COLOR = (200, 0, 200)   # magenta — menandakan simbol tile yang tidak diketahui

# ── Biaya langkah ────────────────────────────────────────────────────────────────
# Ditambahkan ke player.steps ketika bot mendarat pada tile tersebut.
# Biaya lumpur digantikan saat runtime oleh konfigurasi kesulitan.
# Kunci dan mulai/tujuan gratis (0) karena keduanya adalah peristiwa, bukan lintasan.
STEP_COST = {
    ".": 1,
    "M": 3,   # default; diff["mud_step"] menggantikan ini di apply_tile_effect
    "F": 1,
    "R": 1,
    "T": 1,
    "t": 1,
    "K": 1,
    "%": 1,
    "S": 0,
    "G": 0,
}

# ── Besaran efek default (digunakan saat tidak ada konfigurasi kesulitan yang diberikan) ──────────
MUD_FREEZE_FRAMES = 2    # frame bot dibekukan setelah menginjak lumpur
FIRE_DAMAGE  = 25        # HP yang hilang per tile api
REGEN_HEAL   = 15        # HP yang didapat per tile regen
REGEN_CAP    = 100       # regen tidak dapat menaikkan HP di atas nilai ini

# ── Konfigurasi kesulitan ─────────────────────────────────────────────────
# Setiap kunci dipetakan ke dict yang digunakan oleh algorithm.py dan apply_tile_effect().
#   fire        — HP yang hilang per tile api
#   mud_freeze  — frame bot dibekukan di lumpur
#   mud_step    — biaya langkah untuk lumpur (menggantikan STEP_COST["M"])
#   start_hp    — HP yang dimiliki pemain di awal setiap putaran
#   score_weights — (w_hp, w_step, w_key) digunakan oleh algoritma optimasi
# Hardcore dimulai dengan 1 HP dan menggandakan kerusakan api; skor mengabaikan HP sepenuhnya.
DIFF_CONFIGS = {
    "easy":     {"fire": 12, "mud_freeze": 1, "mud_step": 1, "start_hp": 100, "score_weights": (2, 5, 3)},
    "medium":   {"fire": 25, "mud_freeze": 2, "mud_step": 3, "start_hp": 100, "score_weights": (5, 3, 2)},
    "hard":     {"fire": 37, "mud_freeze": 3, "mud_step": 4, "start_hp": 100, "score_weights": (7, 2, 1)},
    "hardcore": {"fire": 50, "mud_freeze": 4, "mud_step": 6, "start_hp":   1, "score_weights": (0, 7, 3)},
}


def get_color(symbol: str):
    """Kembalikan warna RGB cadangan untuk simbol tile."""
    return TILE_COLORS.get(symbol, DEFAULT_COLOR)

def is_wall(symbol: str) -> bool:
    """True untuk dinding keras (#) dan dinding yang bisa dihancurkan (%)."""
    return symbol in ("#", "%")

def is_passable(symbol: str, keys: int = 0) -> bool:
    """
    Mengembalikan True jika bot dapat memasuki tile ini.
    Dinding keras tidak pernah bisa dilewati.
    Dinding yang bisa dihancurkan (%) membutuhkan setidaknya satu kunci.
    Semua tile lainnya selalu bisa dilewati.
    """
    if symbol == "#":
        return False
    if symbol == "%" and keys == 0:
        return False
    return True

def get_step_cost(symbol: str) -> int:
    """Biaya langkah dasar untuk tile (mengabaikan skala kesulitan)."""
    return STEP_COST.get(symbol, 1)

def build_teleporter_map(grid) -> dict:
    """
    Pindai grid untuk tile T dan t dan pasangkan mereka sesuai urutan kemunculan.
    Mengembalikan dict yang memetakan setiap sel teleporter ke sel pasangannya.
    Kedua arah disimpan agar salah satu ujung bisa menjadi titik masuk.
    mis. {(r1,c1): (r2,c2), (r2,c2): (r1,c1)}
    """
    T_cells, t_cells = [], []
    for r, row in enumerate(grid):
        for c, sym in enumerate(row):
            if sym == "T": T_cells.append((r, c))
            elif sym == "t": t_cells.append((r, c))
    teleporters = {}
    for a, b in zip(T_cells, t_cells):
        teleporters[a] = b   # T → t
        teleporters[b] = a   # t → T (dua arah)
    return teleporters

def apply_tile_effect(symbol: str, player, grid, teleporter_map: dict, diff=None):
    """
    Terapkan efek tile yang baru saja diinjak pemain dan kembalikan
    dict 'extra' yang diteruskan algorithm.py ke main.py untuk isyarat suara/visual.

    Dipanggil setelah set_position() — pemain sudah berada di tile.
    Mengubah player.hp, player.keys, player.row/col, dan grid secara langsung.

    Kunci dict yang dikembalikan:
      freeze_frames  — jumlah frame animasi untuk membekukan bot (lumpur)
      teleported_to  — tuple sel tujuan jika diteleportasi, selain itu None
      key_picked_up  — True jika kunci dikumpulkan
      wall_broken    — True jika dinding % dihancurkan (diatur oleh algoritma, bukan di sini)
      step_cost      — biaya yang ditambahkan ke player.steps untuk penilaian
      fire_damage    — True jika bot mengalami kerusakan api pada langkah ini
      regen_heal     — True jika bot sembuh pada langkah ini
    """
    # Biaya langkah lumpur disesuaikan dengan kesulitan; yang lainnya menggunakan tabel tetap.
    step_cost = diff["mud_step"] if (diff and symbol == "M") else get_step_cost(symbol)
    result = {
        "freeze_frames": 0,
        "teleported_to": None,
        "key_picked_up": False,
        "wall_broken":   False,
        "step_cost":     step_cost,
        "fire_damage":   False,
        "regen_heal":    False,
    }
    if symbol == "F":
        # Tile api — berikan kerusakan yang disesuaikan dengan kesulitan
        player.hp -= diff["fire"] if diff else FIRE_DAMAGE
        result["fire_damage"] = True
    elif symbol == "R":
        # Tile regen — sembuhkan tapi jangan pernah melebihi batas
        player.hp = min(REGEN_CAP, player.hp + REGEN_HEAL)
        result["regen_heal"] = True
    elif symbol == "M":
        # Tile lumpur — berapa lama bot dibekukan ditentukan oleh kesulitan
        result["freeze_frames"] = diff["mud_freeze"] if diff else MUD_FREEZE_FRAMES
    elif symbol in ("T", "t"):
        # Teleporter — cari sel pasangan dan lompat ke sana
        dest = teleporter_map.get((player.row, player.col))
        if dest:
            player.set_position(*dest)
            result["teleported_to"] = dest
    elif symbol == "K":
        # Pengambilan kunci — tambah jumlah kunci, ganti tile K dengan lantai agar hilang
        player.keys += 1
        grid[player.row][player.col] = "."
        result["key_picked_up"] = True
    return result