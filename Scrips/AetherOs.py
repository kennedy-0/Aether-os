from __future__ import annotations
import argparse
import math
import random
import sys
import time
import traceback
import subprocess
import pygame
import threading



def retro():
    print("Iniciando o sistema retro...")
    subprocess.Popen(["retroarch"])

def controle():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nenhum controle detectado.")
        return
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    loop = True
    while loop:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                if joystick.get_button(0):  # Botão A
                    print("Botão A pressionado. Iniciando o sistema retro...")
                    retro()
                    loop = False
                elif joystick.get_button(1):  # Botão B
                    print("Botão B pressionado. Saindo do programa.")
                    loop = False
            elif event.type == pygame.QUIT:
                loop = False


try:
    import tkinter as tk
    from tkinter import font as tkfont
except ImportError:  # pragma: no cover - depende do sistema
    sys.exit(
        "Tkinter não encontrado.\n"
        "  Windows/macOS: reinstale o Python marcando a opção 'tcl/tk'.\n"
        "  Raspberry Pi / Debian / Ubuntu: sudo apt install python3-tk"
    )

# --------------------------------------------------------------------------- #
# Identidade visual
# --------------------------------------------------------------------------- #

BG = "#090710"          # fundo principal
SURFACE = "#120C1D"     # superfícies escuras
PURPLE = "#A855F7"      # roxo neon
VIOLET = "#C084FC"      # violeta claro
TEXT = "#F5F0FF"        # texto principal
TEXT_DIM = "#A39AAF"    # texto secundário

VERSION_LABEL = "AETHEROS // v1.0"
PULSE_PERIOD = 2.4      # segundos por ciclo de pulsação do "PRESS X"
FRAME_MS = 33           # ~30 quadros por segundo

# Fontes monoespaçadas em ordem de preferência (a primeira instalada é usada).
MONO_CANDIDATES = (
    "JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo",
    "DejaVu Sans Mono", "Liberation Mono", "Courier New", "Courier",
)

# Fonte pixel 5x7 desenhada à mão: o logotipo não depende de fontes instaladas.
GLYPHS = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "H": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "O": [".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
}
LOGO_PARTS = (("AETHER", TEXT), ("OS", PURPLE))

# Ícone pixel art de um controle genérico (apenas ilustrativo).
GAMEPAD = [
    ".#########.",
    "##.#####.##",
    "#...###.#.#",
    "##.#####.##",
    "####...####",
    "###.....###",
    "##.......##",
]


# --------------------------------------------------------------------------- #
# Utilitários
# --------------------------------------------------------------------------- #

def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def blend(c1: str, c2: str, t: float) -> str:
    """Mistura duas cores hex. Tkinter não tem alfa, então simulamos
    transparência misturando a cor com o fundo."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return "#{:02x}{:02x}{:02x}".format(
        round(r1 + (r2 - r1) * t),
        round(g1 + (g2 - g1) * t),
        round(b1 + (b2 - b1) * t),
    )


def spaced(text: str) -> str:
    """Simula espaçamento entre letras (o Tk não suporta tracking)."""
    return "   ".join(" ".join(word) for word in text.split(" "))


def chamfer(x1: float, y1: float, x2: float, y2: float, c: float) -> list[float]:
    """Pontos de um retângulo com cantos cortados (visual de console)."""
    return [
        x1 + c, y1, x2 - c, y1, x2, y1 + c, x2, y2 - c,
        x2 - c, y2, x1 + c, y2, x1, y2 - c, x1, y1 + c,
    ]


def pick_family(root: tk.Tk, candidates: tuple[str, ...], fallback: str = "Courier") -> str:
    """Escolhe a primeira família de fonte disponível no sistema."""
    try:
        available = {name.lower(): name for name in tkfont.families(root)}
    except tk.TclError:
        return fallback
    for name in candidates:
        if name.lower() in available:
            return available[name.lower()]
    return fallback


# --------------------------------------------------------------------------- #
# Aplicação
# --------------------------------------------------------------------------- #


class AetherOSApp:
    """Tela inicial do AetherOS desenhada inteiramente em um Canvas."""

    def __init__(self, root: tk.Tk, fullscreen: bool = False,) -> None:
        self.root = root
        self.w = 0
        self.h = 0
        self.horizon = 0
        self._fullscreen = False
        self._drawn_size: tuple[int, int] | None = None
        self._redraw_job: str | None = None
        self._tick_job: str | None = None
        self._t0 = time.monotonic()
        self._fonts: dict[tuple[int, bool], tkfont.Font] = {}
       
        # Itens animados (recriados a cada redesenho)
        self._glow_rings: list[tuple[int, float]] = []
        self._btn_border: int | None = None
        self._icon_items: list[int] = []
        self._helper_text: int | None = None
        self._twinkles: list[tuple[int, float, float, float]] = []

        self.family = pick_family(root, MONO_CANDIDATES)
        self._configure_window()
        self._create_canvas()
        self._bind_events()

        if fullscreen:
            # Pequeno atraso: alguns gerenciadores de janela só aceitam
            # tela cheia depois que a janela foi mapeada.
            self.root.after(150, self.toggle_fullscreen)
        self._tick()

    # ---- janela e eventos ------------------------------------------------- #

    def _configure_window(self) -> None:
        self.root.title("AetherOS")
        self.root.configure(bg=BG)
        self.root.minsize(640, 400)
        width, height = 1280, 720
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_canvas(self) -> None:
        self.canvas = tk.Canvas(
            self.root, bg=BG, highlightthickness=0, bd=0, takefocus=1
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

    def _bind_events(self) -> None:
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.quit)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.canvas.bind("<Configure>", self._schedule_redraw)

    def toggle_fullscreen(self, _event: tk.Event | None = None) -> str:
        self._fullscreen = not self._fullscreen
        try:
            self.root.attributes("-fullscreen", self._fullscreen)
        except tk.TclError:
            self._fullscreen = False
            print("Aviso: este sistema não aceitou o modo tela cheia.", file=sys.stderr)
        # Em tela cheia o cursor some, como em um console de verdade.
        self.canvas.configure(cursor="none" if self._fullscreen else "")
        if self._fullscreen:
            self.root.after(400, self._ensure_fullscreen)
        return "break"

    def _ensure_fullscreen(self) -> None:
        """Garantia extra: se não houver gerenciador de janelas (ex.: Pi sem
        desktop) e o atributo -fullscreen for ignorado, ocupa a tela à mão."""
        try:
            if self._fullscreen and not self.root.attributes("-fullscreen"):
                sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                self.root.geometry(f"{sw}x{sh}+0+0")
        except tk.TclError:
            pass

    def quit(self, _event: tk.Event | None = None) -> None:
        for job in (self._redraw_job, self._tick_job):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        self.root.destroy()

    # ---- redesenho responsivo -------------------------------------------- #

    def _schedule_redraw(self, _event: tk.Event | None = None) -> None:
        """Agrupa eventos de redimensionamento para evitar redesenhos em excesso."""
        if self._redraw_job is not None:
            self.root.after_cancel(self._redraw_job)
        self._redraw_job = self.root.after(70, self._redraw)

    def _redraw(self) -> None:
        self._redraw_job = None
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 100 or h < 100 or (w, h) == self._drawn_size:
            return
        self._drawn_size = (w, h)
        self.w, self.h = w, h
        self.horizon = int(h * 0.64)

        self.canvas.delete("all")
        self._glow_rings = []
        self._btn_border = None
        self._icon_items = []
        self._helper_text = None
        self._twinkles = []

        cx = w / 2
        layers = (
            self._draw_background,
            self._draw_pixel_field,
            self._draw_side_geometry,
            self._draw_grid_floor,
            self._draw_scanlines,
            self._draw_hud_frame,
            lambda: self._draw_emblem(cx, h * 0.20),
            lambda: self._draw_logotype(cx, h * 0.41),
            lambda: self._draw_subtitle(cx, h * 0.515),
            lambda: self._draw_tagline(cx, h * 0.585),
            lambda: self._draw_start_button(cx, h * 0.735),
            self._draw_status_bar,
        )
        for layer in layers:
            # Uma camada com defeito não deve derrubar a tela inteira.
            try:
                layer()
            except Exception:  # noqa: BLE001
                traceback.print_exc()

    # ---- primitivas ------------------------------------------------------- #

    def _font(self, size_px: int, bold: bool = False) -> tkfont.Font:
        key = (size_px, bold)
        if key not in self._fonts:
            self._fonts[key] = tkfont.Font(
                root=self.root, family=self.family, size=-size_px,
                weight="bold" if bold else "normal",
            )
        return self._fonts[key]

    def _radial_glow(self, cx: float, cy: float, rx: float, ry: float,
                     color: str, strength: float, steps: int = 16) -> None:
        """Brilho suave feito de elipses concêntricas (sem imagens)."""
        for i in range(steps, 0, -1):
            f = i / steps
            alpha = strength * (1 - f) ** 1.7
            self.canvas.create_oval(
                cx - rx * f, cy - ry * f, cx + rx * f, cy + ry * f,
                fill=blend(BG, color, alpha), outline="",
            )

    def _draw_bitmap(self, rows: list[str], x0: float, y0: float, px: int,
                     color: str, gap: int = 0) -> None:
        for ry, row in enumerate(rows):
            for rx, ch in enumerate(row):
                if ch == "#":
                    x, y = x0 + rx * px, y0 + ry * px
                    self.canvas.create_rectangle(
                        x, y, x + px - gap, y + px - gap, fill=color, outline=""
                    )

    # ---- camadas de fundo ------------------------------------------------- #

    def _draw_background(self) -> None:
        w, h = self.w, self.h
        self.canvas.create_rectangle(0, 0, w, h, fill=BG, outline="")
        # Halo central que dá profundidade ao fundo.
        self._radial_glow(w / 2, h * 0.38, w * 0.50, h * 0.55, PURPLE, 0.17, steps=18)

    def _draw_pixel_field(self) -> None:
        """Campo de pixels dispersos, como estrelas digitais."""
        w, h = self.w, self.h
        rng = random.Random(1987)  # semente fixa: o fundo é sempre o mesmo
        unit = max(2, round(h / 360))
        top = int(h * 0.62)

        def in_content_zone(x: int, y: int) -> bool:
            return 0.22 * w < x < 0.78 * w and 0.08 * h < y < 0.60 * h

        for _ in range(int(w * h / 9000)):
            x = rng.randrange(0, w) // unit * unit
            y = rng.randrange(0, top) // unit * unit
            if in_content_zone(x, y) and rng.random() < 0.85:
                continue  # mantém a área do logotipo limpa
            size = unit * rng.choice((1, 1, 1, 2))
            color = blend(BG, VIOLET, rng.uniform(0.08, 0.30))
            self.canvas.create_rectangle(x, y, x + size, y + size, fill=color, outline="")

        # Poucos pontos mais luminosos que cintilam devagar.
        placed = 0
        while placed < 10:
            x = rng.randrange(0, w) // unit * unit
            y = rng.randrange(0, top) // unit * unit
            if in_content_zone(x, y):
                continue
            item = self.canvas.create_rectangle(
                x, y, x + unit * 2, y + unit * 2, fill=VIOLET, outline=""
            )
            self._twinkles.append((item, rng.uniform(0.45, 0.8),
                                   rng.uniform(0, math.tau), rng.uniform(0.6, 1.4)))
            placed += 1

    def _draw_side_geometry(self) -> None:
        """Losangos vazados e discretos nas laterais (camada de profundidade)."""
        w, h = self.w, self.h
        if w / h < 1.3:
            return  # em janelas estreitas isso poluiria o centro
        for cx, cy, r in ((0.09 * w, 0.31 * h, 0.12 * h), (0.91 * w, 0.43 * h, 0.09 * h)):
            for scale, alpha in ((1.0, 0.18), (0.62, 0.11), (0.28, 0.08)):
                rr = r * scale
                self.canvas.create_polygon(
                    cx, cy - rr, cx + rr, cy, cx, cy + rr, cx - rr, cy,
                    fill="", outline=blend(BG, PURPLE, alpha), width=1,
                )

    def _draw_grid_floor(self) -> None:
        """Piso em perspectiva com horizonte iluminado."""
        w, h = self.w, self.h
        y0, vx = self.horizon, w / 2
        depth = h - y0

        self.canvas.create_rectangle(0, y0, w, h, fill=blend(BG, SURFACE, 0.8), outline="")

        # Linhas horizontais: espaçamento cresce com a proximidade.
        n = 14
        for k in range(1, n + 1):
            t = k / n
            y = y0 + depth * t ** 2.2
            self.canvas.create_line(0, y, w, y, fill=blend(BG, PURPLE, 0.05 + 0.25 * t))

        # Linhas verticais convergindo ao ponto de fuga, mais fortes perto da tela.
        spacing = w / 10
        segments = 3
        for i in range(-12, 13):
            xb = vx + i * spacing
            for s in range(segments):
                t0, t1 = s / segments, (s + 1) / segments
                self.canvas.create_line(
                    vx + (xb - vx) * t0, y0 + depth * t0,
                    vx + (xb - vx) * t1, y0 + depth * t1,
                    fill=blend(BG, PURPLE, 0.05 + 0.22 * t1),
                )

        # Brilho de horizonte: faixa suave acima da linha + linha nítida.
        step = max(3, int(h * 0.006))
        bands = 8
        for j in range(bands, 0, -1):
            alpha = 0.14 * (1 - (j - 1) / bands) ** 1.5
            self.canvas.create_rectangle(
                0, y0 - j * step, w, y0, fill=blend(BG, PURPLE, alpha), outline=""
            )
        self.canvas.create_line(0, y0, w, y0, fill=blend(BG, VIOLET, 0.65), width=2)

    def _draw_scanlines(self) -> None:
        """Linhas de varredura CRT muito sutis, abaixo do conteúdo."""
        step = 3 if self.h < 800 else 4
        color = blend(BG, "#000000", 0.45)
        for y in range(0, self.h, step):
            self.canvas.create_line(0, y, self.w, y, fill=color)

    def _draw_hud_frame(self) -> None:
        """Cantoneiras que enquadram a tela como o visor de um console."""
        w, h = self.w, self.h
        base = min(w, h)
        m, length, t = int(base * 0.03), int(base * 0.06), max(2, base // 360)
        color = blend(BG, PURPLE, 0.55)
        for sx, sy, ax, ay in ((m, m, 1, 1), (w - m, m, -1, 1),
                               (m, h - m, 1, -1), (w - m, h - m, -1, -1)):
            self.canvas.create_line(sx, sy, sx + ax * length, sy, fill=color, width=t)
            self.canvas.create_line(sx, sy, sx, sy + ay * length, fill=color, width=t)

    # ---- conteúdo central ------------------------------------------------- #

    def _draw_emblem(self, cx: float, cy: float) -> None:
        """Símbolo do sistema: um cristal ("éter") em órbita, em pixel art."""
        cell = max(3, int(self.h * 0.0095))
        gap = 1 if cell >= 5 else 0
        self._radial_glow(cx, cy, cell * 13, cell * 13, VIOLET, 0.26, steps=14)

        for dy in range(-8, 9):
            for dx in range(-8, 9):
                r = abs(dx) + abs(dy)
                if r == 0:
                    color = TEXT
                elif r == 1:
                    color = VIOLET
                elif r == 2:
                    color = PURPLE
                elif r == 4 and dx % 2 == 0:
                    color = blend(BG, VIOLET, 0.55)
                elif r == 6:
                    color = PURPLE
                elif r == 8 and (dx == 0 or dy == 0):
                    color = VIOLET
                else:
                    continue
                x = cx + (dx - 0.5) * cell
                y = cy + (dy - 0.5) * cell
                self.canvas.create_rectangle(
                    x, y, x + cell - gap, y + cell - gap, fill=color, outline=""
                )

    def _draw_logotype(self, cx: float, cy: float) -> None:
        """Logotipo 'AETHEROS' desenhado com a fonte pixel própria."""
        letters = []  # (glifo, cor, coluna extra antes da letra)
        for part_i, (word, color) in enumerate(LOGO_PARTS):
            for ch_i, ch in enumerate(word):
                extra = 1 if (part_i > 0 and ch_i == 0) else 0
                letters.append((GLYPHS[ch], color, extra))

        cols = len(letters) * 5 + (len(letters) - 1) + sum(e for _, _, e in letters)
        px = max(3, int(min(self.w * 0.62 / cols, self.h * 0.14 / 7)))
        gap = max(1, px // 10)
        x0, y0 = cx - cols * px / 2, cy - 7 * px / 2

        self._radial_glow(cx, cy, cols * px * 0.55, px * 6, PURPLE, 0.10, steps=12)

        positions, x = [], x0
        for glyph, color, extra in letters:
            x += extra * px
            positions.append((x, glyph, color))
            x += 6 * px

        shadow, off = blend(BG, PURPLE, 0.40), max(2, round(px * 0.3))
        for x, glyph, _ in positions:
            self._draw_bitmap(glyph, x + off, y0 + off, px, shadow, gap)
        for x, glyph, color in positions:
            self._draw_bitmap(glyph, x, y0, px, color, gap)

    def _draw_subtitle(self, cx: float, cy: float) -> None:
        font = self._font(max(11, int(self.h * 0.019)))
        label = spaced("RETRO GAMING SYSTEM")
        self.canvas.create_text(cx, cy, text=label, font=font, fill=TEXT_DIM)

        half = font.measure(label) / 2
        gap, length = 18, max(30, self.w * 0.05)
        line = blend(BG, PURPLE, 0.5)
        for sign in (-1, 1):
            xa = cx + sign * (half + gap)
            self.canvas.create_line(xa, cy, xa + sign * length, cy, fill=line)

    def _draw_tagline(self, cx: float, cy: float) -> None:
        font = self._font(max(13, int(self.h * 0.026)), bold=True)
        self.canvas.create_text(
            cx, cy, text=spaced("YOUR NEXT LEVEL STARTS HERE"), font=font, fill=VIOLET
        )

    def _draw_start_button(self, cx: float, cy: float) -> None:
        """Indicador 'PRESS X' com contorno pulsante (única animação central)."""
        h = self.h
        bh = max(52, int(h * 0.085))
        font = self._font(max(18, int(bh * 0.42)), bold=True)
        label = "PRESS X"
        icon_d, gap = int(bh * 0.5), int(bh * 0.28)
        content_w = icon_d + gap + font.measure(label)
        bw = int(content_w + bh * 1.8)
        x1, y1, x2, y2 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
        c = bh * 0.28

        # Anéis de brilho externos (cor atualizada em _tick).
        ring_step = max(3, int(h * 0.006))
        for k, strength in enumerate((0.5, 0.28, 0.12), start=1):
            e = k * ring_step
            ring = self.canvas.create_polygon(
                chamfer(x1 - e, y1 - e, x2 + e, y2 + e, c + e * 0.6),
                fill="", outline=blend(BG, VIOLET, strength), width=2,
            )
            self._glow_rings.append((ring, strength))

        # Corpo do botão e filete interno.
        self._btn_border = self.canvas.create_polygon(
            chamfer(x1, y1, x2, y2, c), fill=SURFACE, outline=PURPLE, width=2
        )
        inset = max(5, int(bh * 0.08))
        self.canvas.create_polygon(
            chamfer(x1 + inset, y1 + inset, x2 - inset, y2 - inset, c * 0.6),
            fill="", outline=blend(SURFACE, PURPLE, 0.28), width=1,
        )

        # Ícone circular com um X + rótulo.
        xs = cx - content_w / 2
        icx, lw = xs + icon_d / 2, max(2, int(bh * 0.04))
        self._icon_items.append(self.canvas.create_oval(
            icx - icon_d / 2, cy - icon_d / 2, icx + icon_d / 2, cy + icon_d / 2,
            outline=VIOLET, width=lw, fill="",
        ))
        r = icon_d * 0.21
        for dx, dy in ((1, 1), (1, -1)):
            self._icon_items.append(self.canvas.create_line(
                icx - dx * r, cy - dy * r, icx + dx * r, cy + dy * r,
                fill=VIOLET, width=lw, capstyle="round",
            ))
        self.canvas.create_text(
            xs + icon_d + gap, cy, text=label, font=font, fill=TEXT, anchor="w"
        )

        helper_font = self._font(max(11, int(h * 0.019)))
        self._helper_text = self.canvas.create_text(
            cx, y2 + h * 0.06, text=spaced("PRESSIONE PARA COMEÇAR"),
            font=helper_font, fill=TEXT_DIM,
        )

    # ---- informações secundárias ----------------------------------------- #

    def _draw_status_bar(self) -> None:
        """Cantos da tela: status, controle (demo), dicas de teclado e versão."""
        w, h = self.w, self.h
        pad = int(min(w, h) * 0.075)
        font = self._font(max(10, int(h * 0.0165)))

        # Superior esquerdo: LED + SYSTEM READY
        led = max(6, int(h * 0.011))
        self.canvas.create_rectangle(
            pad - 3, pad - 3, pad + led + 3, pad + led + 3,
            outline=blend(BG, VIOLET, 0.3), width=1,
        )
        self.canvas.create_rectangle(pad, pad, pad + led, pad + led, fill=VIOLET, outline="")
        self.canvas.create_text(
            pad + led + 14, pad + led / 2, text="SYSTEM READY",
            font=font, fill=TEXT_DIM, anchor="w",
        )

        # Superior direito: ícone de controle + rótulo DEMO (não é detecção real)
        label = "CONTROLLER // DEMO"
        self.canvas.create_text(
            w - pad, pad + led / 2, text=label, font=font, fill=TEXT_DIM, anchor="e"
        )
        px = max(2, int(h * 0.0042))
        icon_w = len(GAMEPAD[0]) * px
        icon_x = w - pad - font.measure(label) - 16 - icon_w
        icon_y = pad + led / 2 - len(GAMEPAD) * px / 2
        self._draw_bitmap(GAMEPAD, icon_x, icon_y, px, blend(BG, VIOLET, 0.7))

        # Inferior esquerdo: dica de desenvolvimento
        self.canvas.create_text(
            pad, h - pad, text="F11 TELA CHEIA  //  ESC SAIR", font=font,
            fill=blend(BG, TEXT_DIM, 0.6), anchor="w",
        )
        # Inferior direito: versão
        self.canvas.create_text(
            w - pad, h - pad, text=VERSION_LABEL, font=font, fill=TEXT_DIM, anchor="e"
        )

    # ---- animação --------------------------------------------------------- #

    def _tick(self) -> None:
        """Atualiza apenas as cores dos itens animados (leve para o Raspberry Pi)."""
        now = time.monotonic() - self._t0
        # 0..1 suave, sem saltos (curva cosseno).
        pulse = (1 - math.cos(math.tau * now / PULSE_PERIOD)) / 2
        cfg = self.canvas.itemconfigure
        try:
            for item, strength in self._glow_rings:
                cfg(item, outline=blend(BG, VIOLET, strength * (0.25 + 0.75 * pulse)))
            if self._btn_border is not None:
                cfg(self._btn_border, outline=blend(blend(BG, PURPLE, 0.7), VIOLET, pulse))
            icon_color = blend(PURPLE, TEXT, pulse * 0.55)
            for item in self._icon_items:
                cfg(item, fill=icon_color) if self.canvas.type(item) == "line" \
                    else cfg(item, outline=icon_color)
            if self._helper_text is not None:
                cfg(self._helper_text, fill=blend(blend(BG, TEXT_DIM, 0.5), TEXT_DIM, pulse))
            for item, base, phase, speed in self._twinkles:
                a = base * (0.45 + 0.55 * (0.5 + 0.5 * math.sin(now * speed + phase)))
                cfg(item, fill=blend(BG, VIOLET, a))
        except tk.TclError:
            return  # janela fechada durante o quadro
        self._tick_job = self.root.after(FRAME_MS, self._tick)


# --------------------------------------------------------------------------- #
# Entrada
# --------------------------------------------------------------------------- #

def main() -> int:
    parser = argparse.ArgumentParser(description="AetherOS - tela inicial (demo visual)")
    parser.add_argument("--windowed", action="store_true",
                        help="abre em janela em vez de tela cheia (desenvolvimento)")
    args = parser.parse_args()

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Não foi possível abrir a janela (há um ambiente gráfico?): {exc}",
              file=sys.stderr)
        return 1

    AetherOSApp(root, fullscreen=not args.windowed)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0

if __name__ == "__main__":
    threading.Thread(
        target=controle,
        daemon=True
    ).start()

    sys.exit(main())   
