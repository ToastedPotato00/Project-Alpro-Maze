"""
ui.py — bilah HUD (Heads-Up Display) yang digambar di bagian bawah layar game.

HUD adalah strip tetap 60 px yang dibagi menjadi lima zona visual dari kiri ke kanan:
  Zona 1 — bilah HP + nilai HP numerik
  Zona 2 — jumlah kunci + jumlah langkah
  Zona 3 — tombol dropdown kecepatan
  Zona 4 — tombol dropdown algoritma + kesulitan
  Zona 5 — label status + skor opsional + petunjuk keyboard (jangkar kanan)

draw() mengembalikan tiga Rect tombol dropdown agar main.py dapat meneruskannya
ke objek dropdown untuk pengujian klik mouse.
"""

import pygame

# ── Konstanta tata letak ──────────────────────────────────────────────────────────
HUD_HEIGHT   = 60        # pixel height of the HUD strip
HUD_BG       = (12, 12, 18)
HUD_BORDER   = (40, 40, 55)
PADDING      = 10

# ── Ukuran font ────────────────────────────────────────────────────────────────
FONT_MAIN    = 25   # teks nilai utama (nomor HP, jumlah kunci, langkah)
FONT_LABEL   = 20   # teks label sekunder ("HP", "KEYS", "STEPS", petunjuk)

# ── Pengaturan visual bilah HP ────────────────────────────────────────────────────
HP_BAR_W     = 100   # total lebar bilah dalam piksel
HP_BAR_H     = 12    # tinggi bilah dalam piksel
HP_SEGMENT_W = 4     # setiap blok kecil dalam bilah tersegmentasi/piksel
HP_GAP       = 1     # jarak antar segmen
# Ambang batas warna: hijau di atas 50%, kuning 25–50%, merah di bawah 25%
HP_COL_HI    = (60,  210,  80)
HP_COL_MID   = (220, 180,  40)
HP_COL_LO    = (220,  50,  40)
HP_COL_BG    = (35,  35,  45)   # unfilled bar background

# ── Warna teks ──────────────────────────────────────────────────────────────
TEXT_COLOR   = (190, 190, 200)
LABEL_COLOR  = (100, 100, 120)
KEY_COLOR    = (240, 200,  40)
STEP_COLOR   = (120, 190, 255)
DIVIDER_COL  = (40,  40,  55)

# Each algorithm state maps to a display colour and a human-readable label.
STATUS_COLORS = {
    "idle":         (120, 120, 140),
    "exploring":    ( 80, 210,  80),
    "backtracking": (220, 150,  50),
    "found":        (255, 215,  40),
    "no_solution":  (210,  55,  55),
    "checkpoint":   (100, 220, 255),   # algo berantai: satu tujuan tercapai
    "candidate":    (255, 160,  40),   # algo optimasi: sebuah jalur telah dinilai
    "replaying":    ( 80, 210, 255),
}
STATUS_LABELS = {
    "idle":         "Waiting...",
    "exploring":    "Exploring...",
    "backtracking": "Backtracking...",
    "found":        "Goal Reached!",
    "no_solution":  "No Solution Found",
    "checkpoint":   "Checkpoint!",
    "candidate":    "Candidate found!",
    "replaying":    "Replaying best...",
}


class HUD:
    def __init__(self, screen_w: int, screen_h: int):
        pygame.font.init()
        self.font     = pygame.font.Font("assets/font.ttf", FONT_MAIN)
        self.font_sm  = pygame.font.Font("assets/font.ttf", FONT_LABEL)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.hud_y    = screen_h - HUD_HEIGHT   # koordinat y atas strip HUD

    # ── Public draw ───────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface, player, status: str,
             algo_label: str = "Classic Backtracking", score=None,
             diff_label: str = "Medium",
             speed_label: str = "Normal") -> tuple:
        """
        Gambar HUD penuh dan kembalikan (algo_btn_rect, diff_btn_rect, speed_btn_rect).
        Rect yang dikembalikan digunakan oleh main.py untuk mengarahkan klik mouse ke
        objek dropdown yang tepat.
        """
        # ── Strip latar dan garis batas atas ──────────────────────────────
        hud_rect = pygame.Rect(0, self.hud_y, self.screen_w, HUD_HEIGHT)
        pygame.draw.rect(surface, HUD_BG, hud_rect)
        pygame.draw.line(surface, HUD_BORDER,
                         (0, self.hud_y), (self.screen_w, self.hud_y), 2)

        cy = self.hud_y + HUD_HEIGHT // 2   # pusat vertikal strip HUD

        # ── Zona 1: Bilah HP + angka ───────────────────────────────────────────
        x = PADDING
        lbl = self.font_sm.render("HP", True, LABEL_COLOR)
        surface.blit(lbl, (x, cy - lbl.get_height() // 2))
        x += lbl.get_width() - 18
        # _draw_hp_bar mengembalikan posisi x tepat setelah bilah berakhir
        x = self._draw_hp_bar(surface, player.hp, x+24, cy)
        hp_txt = self.font.render(str(max(0, player.hp)), True, TEXT_COLOR)
        surface.blit(hp_txt, (x, cy - hp_txt.get_height() // 2))

        # ── Zona 2: Kunci + Langkah ──────────────────────────────────────────────
        self._draw_divider(surface, 200, cy)
        x = 210
        k_lbl = self.font_sm.render("KEYS", True, LABEL_COLOR)
        k_val = self.font.render(str(player.keys), True, KEY_COLOR)
        surface.blit(k_lbl, (x, cy - k_lbl.get_height() // 2))
        x += k_lbl.get_width() + 5
        surface.blit(k_val, (x, cy - k_val.get_height() // 2))
        x += k_val.get_width() + PADDING * 2

        s_lbl = self.font_sm.render("STEPS", True, LABEL_COLOR)
        s_val = self.font.render(str(player.steps), True, STEP_COLOR)
        surface.blit(s_lbl, (x, cy - s_lbl.get_height() // 2))
        x += s_lbl.get_width() + 5
        surface.blit(s_val, (x, cy - s_val.get_height() // 2))

        # ── Zona 3 + 4: Tombol dropdown Kecepatan / Algoritma / Kesulitan ──────
        # Ini hanyalah pemicu visual; status dropdown sebenarnya ada di main.py.
        self._draw_divider(surface, 410, cy)
        btn_x   = 420
        sbtn_w  = 150
        abtn_w  = 235
        dbtn_w  = 180
        btn_h   = HUD_HEIGHT - 16
        btn_gap = 30

        speed_btn = pygame.Rect(btn_x, self.hud_y + 8, sbtn_w, btn_h)
        pygame.draw.rect(surface, (40, 40, 62), speed_btn, border_radius=6)
        pygame.draw.rect(surface, (65, 65, 92), speed_btn, 1, border_radius=6)
        sp_surf = self.font_sm.render(f"{speed_label} ▼", True, (160, 230, 180))
        surface.blit(sp_surf, sp_surf.get_rect(center=speed_btn.center))
        ax = btn_x + sbtn_w + btn_gap   # x start of algorithm button

        algo_btn = pygame.Rect(ax, self.hud_y + 8, abtn_w, btn_h)
        pygame.draw.rect(surface, (40, 40, 62), algo_btn, border_radius=6)
        pygame.draw.rect(surface, (65, 65, 92), algo_btn, 1, border_radius=6)
        al_surf  = self.font_sm.render(f"{algo_label}  ▼", True, (160, 195, 240))
        surface.blit(al_surf, al_surf.get_rect(center=algo_btn.center))

        diff_btn = pygame.Rect(ax + abtn_w + btn_gap, self.hud_y + 8, dbtn_w, btn_h)
        pygame.draw.rect(surface, (40, 40, 62), diff_btn, border_radius=6)
        pygame.draw.rect(surface, (65, 65, 92), diff_btn, 1, border_radius=6)
        df_surf  = self.font_sm.render(f"{diff_label}  ▼", True, (200, 160, 240))
        surface.blit(df_surf, df_surf.get_rect(center=diff_btn.center))

        # ── Zona 5: Status + skor + petunjuk (sisi kanan) ────────────────────────
        slabel     = STATUS_LABELS.get(status, status)
        scolor     = STATUS_COLORS.get(status, TEXT_COLOR)
        stxt       = self.font.render(slabel, True, scolor)
        # Skor hanya ditampilkan setelah algoritma optimasi selesai
        score_surf = (self.font_sm.render(f"Score: {score}", True, (200, 200, 150))
                      if score is not None else None)
        hint       = self.font_sm.render("  R restart   ESC menu", True, (80, 80, 105))

        # Tumpuk baris secara vertikal dan ratakan kanan terhadap tepi layar.
        line_gap  = 0
        lines     = [stxt] + ([score_surf] if score_surf else []) + [hint]
        block_h   = sum(l.get_height() for l in lines) + line_gap * (len(lines) - 1)
        block_top = self.hud_y + (HUD_HEIGHT - block_h) // 2

        # Bilah aksen berwarna kecil di sisi kiri blok teks
        max_w = max(l.get_width() for l in lines)
        pygame.draw.rect(surface, scolor,
                         (self.screen_w - max_w - PADDING - 6, block_top, 3, block_h),
                         border_radius=1)
        y = block_top
        for l in lines:
            surface.blit(l, (self.screen_w - l.get_width() - PADDING, y))
            y += l.get_height() + line_gap

        # Kembalikan ketiga rect tombol agar main.py dapat meneruskan klik ke dropdown
        return algo_btn, diff_btn, speed_btn

    # ── Pembantu internal ──────────────────────────────────────────────────────

    def _draw_divider(self, surface, x, cy):
        """Gambar garis pemisah vertikal tipis di x."""
        pygame.draw.line(surface, DIVIDER_COL,
                         (x, self.hud_y + 8), (x, self.hud_y + HUD_HEIGHT - 8), 1)
        return x + PADDING

    def _draw_hp_bar(self, surface, hp: int, x: int, cy: int):
        """
        Gambar bilah HP tersegmentasi bergaya piksel yang dipusatkan pada cy.
        Mengembalikan koordinat x tepat setelah bilah berakhir,
        sehingga pemanggil dapat menempatkan angka HP sejajar dengannya.
        """
        hp_frac = max(0.0, min(1.0, hp / 100.0))

        # Warna berubah saat HP turun: hijau → kuning → merah
        if hp_frac > 0.5:
            bar_color = HP_COL_HI
        elif hp_frac > 0.25:
            bar_color = HP_COL_MID
        else:
            bar_color = HP_COL_LO

        bar_y = cy - HP_BAR_H // 2

        # Gambar latar kosong dari bilah penuh
        pygame.draw.rect(surface, HP_COL_BG,
                         (x, bar_y, HP_BAR_W, HP_BAR_H), border_radius=2)

        # Isi dengan segmen individual hingga fraksi HP saat ini
        filled_w  = int(HP_BAR_W * hp_frac)
        seg_total = HP_SEGMENT_W + HP_GAP   # width of one segment + gap
        sx        = x
        while sx + HP_SEGMENT_W <= x + filled_w:
            pygame.draw.rect(surface, bar_color,
                             (sx, bar_y + 1, HP_SEGMENT_W, HP_BAR_H - 2))
            sx += seg_total

        # Garis luar di sekitar seluruh bilah
        pygame.draw.rect(surface, (60, 60, 75),
                         (x, bar_y, HP_BAR_W, HP_BAR_H), 1, border_radius=2)

        return x + HP_BAR_W + 5   # jarak 5 px sebelum nomor HP

