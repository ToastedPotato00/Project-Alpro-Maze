"""
map_loader.py — membaca file peta teks biasa menjadi grid 2D.

File peta adalah file .txt di mana setiap karakter adalah satu simbol tile.
Baris mungkin berbeda panjangnya; baris pendek diisi dengan '#' (dinding) di kanan
sehingga grid yang dikembalikan selalu berbentuk persegi panjang.

Diekspor oleh main.py dan algorithm.py:
  load_map()  — parse file → grid + tile_size
  find_tile() — pindai grid untuk semua sel yang cocok dengan simbol
"""

# Digunakan hanya saat tile_size dihitung otomatis (tidak ada override yang diteruskan ke load_map).
MAX_SCREEN_W = 1280
MAX_SCREEN_H = 800
MIN_TILE     = 16   # jangan pernah render tile lebih kecil dari 16 px
DEFAULT_TILE = 32   # ukuran tile target untuk tampilan yang nyaman


def load_map(filepath: str, tile_size: int = None):
    """
    Parse file peta .txt dan kembalikan (grid, tile_size).

    grid      — list[list[str]], diakses sebagai grid[row][col]
    tile_size — ukuran piksel untuk setiap tile, disesuaikan ke layar jika tidak diberikan

    Baris kosong di awal/akhir dihapus agar file peta bisa memiliki
    spasi putih opsional di atas atau bawah tanpa mempengaruhi grid.
    """
    with open(filepath, "r") as f:
        lines = [line.rstrip("\n") for line in f.readlines()]

    # Hapus baris kosong di awal dan akhir file
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()

    # Isi baris yang lebih pendek dengan '#' agar setiap baris memiliki panjang yang sama.
    # Ini mencegah kesalahan indeks saat algoritma berjalan di dekat tepi kanan.
    max_width = max(len(row) for row in lines)
    grid = [list(row.ljust(max_width, "#")) for row in lines]

    rows = len(grid)
    cols = max_width

    if tile_size is None:
        # Pilih ukuran tile terbesar yang cocok untuk peta di dalam layar,
        # dibatasi ke [MIN_TILE, DEFAULT_TILE] agar tile tidak terlalu kecil atau besar.
        tile_w = MAX_SCREEN_W // cols
        tile_h = MAX_SCREEN_H // rows
        tile_size = max(MIN_TILE, min(DEFAULT_TILE, tile_w, tile_h))

    return grid, tile_size


def find_tile(grid, symbol: str):
    """
    Kembalikan daftar tuple (row, col) untuk setiap sel yang cocok dengan simbol.
    Hasil diurutkan atas-ke-bawah, kiri-ke-kanan (urutan pindai alami).
    Digunakan oleh main.py untuk menemukan posisi mulai ('S') dan tujuan ('G').
    """
    positions = []
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == symbol:
                positions.append((r, c))
    return positions