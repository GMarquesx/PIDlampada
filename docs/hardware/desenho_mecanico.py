"""
Desenho mecanico - PIDlampada - PIDL-MEC-001, A3 paisagem, 2 folhas. Rev. A.

  folha 1: corte A-A da camara (1:2) com cotas e baloes, lista de materiais
           mecanica, dimensionamento termico e notas de montagem
  folha 2: plano de corte da chapa de policarbonato 1000 x 1000 x 6 (1:10),
           furacao dos cinco paineis (1:4), prateleira, cantoneiras e
           tabela de furos

Gera as versoes em portugues e em ingles.

Uso:
    python docs/hardware/desenho_mecanico.py

Saida (em docs/hardware/):
    Desenho_Mecanico_Rev_A.pdf          portugues
    Mechanical_Drawing_Rev_A_EN.pdf     ingles
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import folha_a3 as F            # noqa: E402
from folha_a3 import esc        # noqa: E402

BUILD = os.path.join(AQUI, 'build')
DES = 'PIDL-MEC-001'
REV = 'A'
DATA = '11/10/2026'
TOTAL = 2

AZUL = '#1d64c8'


def T(pt, en):
    return {'pt': pt, 'en': en}[LANG]


LANG = 'pt'

# ------------------------------------------------------------------ geometria (mm)
EXT = 250.0            # caixa externa 250 x 250 x 250 (paredes + tampa)
ESP = 6.0              # policarbonato
INT = EXT - 2 * ESP    # 238
H_PAR = 244.0          # altura das paredes
MDF = 15.0
BASE = 300.0
ANG = 25.0             # cantoneira 25 x 25 x 1,5
ANG_E = 1.5
SHELF = 70.0           # prateleira acima do piso
SHELF_W = 232.0
FAN_C = 62.0           # centro do cooler abaixo do topo da tampa
VENT_Y = (35.0, 50.0)  # fileiras de frestas, acima do piso
VENT_Z = [-72 + 18 * i for i in range(9)]
LAMP_X = [-90, -45, 0, 45, 90]
M2_Y = 36.0            # centro da M2 acima do piso
POST = 108.0           # espacadores em +-108

# furos de cada painel: (letra, diametro, [(x, y)]) em coordenadas do painel
# (origem no canto inferior esquerdo, vista de fora)
def _bordas(xs, y):
    return [(x, y) for x in xs]


FUROS = {
    'tampa': [   # 250 x 250, vista de cima, frente embaixo
        ('A', 5.0, _bordas((25, 75, 175, 225), 237.5)
         + [(12.5, y) for y in (31, 91, 159, 219)] + [(237.5, y) for y in (31, 91, 159, 219)]
         + [(50, 50), (200, 50), (50, 200), (200, 200)]),
        ('G', 6.0, [(125 + x, 125) for x in LAMP_X] + [(180, 170)]),
        ('E', 3.5, [(88, 170), (112, 170)]),
    ],
    'fundo': [   # 250 x 244, vista de tras
        ('A', 5.0, _bordas((25, 75, 175, 225), 12.5) + _bordas((25, 75, 175, 225), 235)
         + [(12.5, y) for y in (50, 125, 200)] + [(237.5, y) for y in (50, 125, 200)]),
        ('E', 3.5, [(100, M2_Y - 25), (150, M2_Y - 25), (100, M2_Y + 25), (150, M2_Y + 25)]),
        ('F', 12.5, [(40, 150), (210, 150)]),
    ],
    'porta': [   # 250 x 243, vista de frente
        ('A', 5.0, [(12, 45), (12, 65), (12, 185), (12, 205), (230, 93), (230, 157), (238, 125)]),
    ],
    'lat_e': [   # 238 x 244, vista de fora, frente a direita
        ('A', 5.0, _bordas((25, 85, 153, 213), 12.5) + _bordas((25, 85, 153, 213), 235)
         + [(9, y) for y in (50, 125, 200)] + [(226, 45), (226, 65), (226, 185), (226, 205)]),
        ('D', 8.0, [(119 + z, y) for y in VENT_Y for z in VENT_Z]),
    ],
    'lat_d': [   # 238 x 244, vista de fora, frente a esquerda
        ('A', 5.0, _bordas((25, 60, 178, 213), 12.5) + _bordas((25, 60, 178, 213), 235)
         + [(229, y) for y in (50, 125, 200)] + [(12, 125)]),
        ('B', 76.0, [(119, H_PAR + ESP - FAN_C)]),
        ('C', 4.5, [(119 + dx, H_PAR + ESP - FAN_C + dy) for dx in (-35.75, 35.75) for dy in (-35.75, 35.75)]),
    ],
}

# plano de corte: (nome, x, y, largura, altura) na chapa, origem no canto superior esquerdo
KERF = 3.0
PLANO = [
    ('1', 0, 0, 250, 250),
    ('2', 253, 0, 250, 244),
    ('3', 506, 0, 250, 243),
    ('4', 759, 0, 238, 244),
    ('5', 0, 253, 238, 244),
]


# ------------------------------------------------------------------ svg
class Svg:
    def __init__(self):
        self.p = []

    def add(self, s):
        self.p.append(s)

    def line(self, x1, y1, x2, y2, c='v', extra=''):
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" class="{c}" {extra}/>')

    def rect(self, x, y, w, h, c='v', fill=None, extra=''):
        f = f' style="fill:{fill}"' if fill else ''
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" class="{c}"{f} {extra}/>')

    def circle(self, cx, cy, r, c='v', fill=None):
        f = f' style="fill:{fill}"' if fill else ''
        self.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" class="{c}"{f}/>')

    def poly(self, pts, c='v', fill=None, closed=True):
        tag = 'polygon' if closed else 'polyline'
        f = f' style="fill:{fill}"' if fill else ''
        pp = ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)
        self.add(f'<{tag} points="{pp}" class="{c}"{f}/>')

    def text(self, x, y, s, size=2.3, anchor='middle', rot=0, weight='normal', cls='tx', fill=None):
        tr = f' transform="rotate({rot} {x:.2f} {y:.2f})"' if rot else ''
        f = f' fill="{fill}"' if fill else ''
        linhas = str(s).split('\n')
        for i, ln in enumerate(linhas):
            yy = y + i * size * 1.2
            self.add(f'<text x="{x:.2f}" y="{yy:.2f}" font-size="{size}" text-anchor="{anchor}" '
                     f'font-weight="{weight}" class="{cls}"{f}{tr}>{esc(ln)}</text>')

    def arrow(self, x, y, dx, dy, size=2.0, fill='#000'):
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        px, py = -uy, ux
        b = (x - ux * size, y - uy * size)
        self.poly([(x, y), (b[0] + px * size * 0.3, b[1] + py * size * 0.3),
                   (b[0] - px * size * 0.3, b[1] - py * size * 0.3)], 'fa', fill=fill)

    def svg(self):
        return ('<svg class="draw" viewBox="0 0 420 297" width="420mm" height="297mm">' + DEFS + ''.join(self.p) + '</svg>')


DEFS = '''<defs>
<pattern id="hw" width="1.4" height="1.4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="1.4" stroke="#000" stroke-width="0.13"/></pattern>
<pattern id="hp" width="0.9" height="0.9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
  <line x1="0" y1="0" x2="0" y2="0.9" stroke="#1d64c8" stroke-width="0.12"/></pattern>
<pattern id="hi" width="1.0" height="1.0" patternUnits="userSpaceOnUse">
  <circle cx="0.5" cy="0.5" r="0.16" fill="#000"/></pattern>
<pattern id="hf" width="2.0" height="2.0" patternUnits="userSpaceOnUse">
  <circle cx="1" cy="1" r="0.62" fill="none" stroke="#000" stroke-width="0.1"/></pattern>
</defs>'''


def dim_h(s, x1, x2, yf1, yf2, yd, txt, size=2.2):
    """Cota horizontal entre x1 e x2 (papel); yf = ponto da peca, yd = linha de cota."""
    for x, yf in ((x1, yf1), (x2, yf2)):
        sg = 1 if yd > yf else -1
        s.line(x, yf + sg * 0.8, x, yd + sg * 1.2, 't')
    s.line(x1, yd, x2, yd, 't')
    if x2 - x1 > 6:
        s.arrow(x1, yd, -1, 0)
        s.arrow(x2, yd, 1, 0)
    else:
        s.arrow(x1, yd, 1, 0)
        s.arrow(x2, yd, -1, 0)
        s.line(x1 - 3, yd, x1, yd, 't')
        s.line(x2, yd, x2 + 3, yd, 't')
    s.text((x1 + x2) / 2, yd - 0.7, txt, size=size)


def dim_v(s, y1, y2, xf1, xf2, xd, txt, size=2.2, lado=-1):
    """Cota vertical entre y1 e y2 (papel); texto girado, a esquerda da linha."""
    for y, xf in ((y1, xf1), (y2, xf2)):
        sg = 1 if xd > xf else -1
        s.line(xf + sg * 0.8, y, xd + sg * 1.2, y, 't')
    s.line(xd, y1, xd, y2, 't')
    a, b = min(y1, y2), max(y1, y2)
    if b - a > 6:
        s.arrow(xd, a, 0, -1)
        s.arrow(xd, b, 0, 1)
    else:
        s.arrow(xd, a, 0, 1)
        s.arrow(xd, b, 0, -1)
        s.line(xd, a - 3, xd, a, 't')
        s.line(xd, b, xd, b + 3, 't')
    s.text(xd + lado * 0.7, (a + b) / 2, txt, size=size, rot=-90)


def balao(s, x, y, n, bx, by):
    """Balao de item: ponto na peca (x, y), circulo em (bx, by)."""
    r = 2.6
    dx, dy = x - bx, y - by
    d = (dx * dx + dy * dy) ** 0.5 or 1
    s.circle(x, y, 0.45, 't', fill='#000')
    s.line(x, y, bx + dx / d * r, by + dy / d * r, 't')
    s.circle(bx, by, r, 'v', fill='#fff')
    s.text(bx, by + 0.85, n, size=2.4, weight='bold')


class Vista:
    """Transformacao mundo (mm, y para cima) -> papel."""

    def __init__(self, s, ox, oy, k):
        self.s, self.ox, self.oy, self.k = s, ox, oy, k

    def P(self, x, y):
        return self.ox + x * self.k, self.oy - y * self.k

    def rect(self, x0, y0, x1, y1, c='v', fill=None):
        X0, Y1 = self.P(min(x0, x1), max(y0, y1))
        self.s.rect(X0, Y1, abs(x1 - x0) * self.k, abs(y1 - y0) * self.k, c, fill)

    def line(self, x0, y0, x1, y1, c='v'):
        a, b = self.P(x0, y0)
        cc, d = self.P(x1, y1)
        self.s.line(a, b, cc, d, c)

    def poly(self, pts, c='v', fill=None, closed=True):
        self.s.poly([self.P(x, y) for x, y in pts], c, fill, closed)

    def circle(self, x, y, r, c='v', fill=None):
        X, Y = self.P(x, y)
        self.s.circle(X, Y, r * self.k, c, fill)


# ------------------------------------------------------------------ folha 1: corte A-A
def corte(s):
    k = 0.5
    v = Vista(s, 136, 197, k)
    P = v.P
    TOPO = MDF + H_PAR + ESP          # 265
    PISO = MDF

    # base de MDF e pes
    v.rect(-BASE / 2, 0, BASE / 2, MDF, 'v', 'url(#hw)')
    # paredes laterais cortadas (com furo da fresta e do cooler)
    fy = TOPO - FAN_C
    esq = [(PISO, PISO + VENT_Y[0] - 4), (PISO + VENT_Y[0] + 4, PISO + VENT_Y[1] - 4), (PISO + VENT_Y[1] + 4, PISO + H_PAR)]
    for a, b in esq:
        v.rect(-EXT / 2, a, -EXT / 2 + ESP, b, 'v', 'url(#hp)')
    for a, b in [(PISO, fy - 38), (fy + 38, PISO + H_PAR)]:
        v.rect(EXT / 2 - ESP, a, EXT / 2, b, 'v', 'url(#hp)')
    # tampa cortada, com furos das lampadas
    xs = [-EXT / 2] + sum([[x - 3, x + 3] for x in LAMP_X], []) + [EXT / 2]
    for i in range(0, len(xs), 2):
        v.rect(xs[i], PISO + H_PAR, xs[i + 1], TOPO, 'v', 'url(#hp)')
    # cantoneiras externas cortadas (arestas laterais)
    for sx in (-1, 1):
        x0 = sx * EXT / 2
        # inferior: aba na parede e aba sobre a base
        v.poly([(x0, PISO), (x0 + sx * ANG, PISO), (x0 + sx * ANG, PISO + ANG_E), (x0 + sx * ANG_E, PISO + ANG_E),
                (x0 + sx * ANG_E, PISO + ANG), (x0, PISO + ANG)], 'v', '#9aa3ab')
        # superior: aba na parede e aba sobre a tampa
        v.poly([(x0, TOPO), (x0 + sx * ANG_E, TOPO), (x0 + sx * ANG_E, TOPO + ANG_E - ANG), (x0, TOPO + ANG_E - ANG)], 'v', '#9aa3ab')
        v.poly([(x0 + sx * ANG_E, TOPO + ANG_E), (x0 - sx * (ANG - ANG_E), TOPO + ANG_E), (x0 - sx * (ANG - ANG_E), TOPO),
                (x0 + sx * ANG_E, TOPO)], 'v', '#9aa3ab')
        # cantoneira vertical do fundo, vista alem do corte
        v.rect(x0, PISO + ANG, x0 + sx * ANG_E, TOPO - ANG, 't')
        # parafusos (linhas de centro)
        for yy in (PISO + 12.5,):
            v.line(x0 - sx * 4, yy, x0 + sx * 4, yy, 'c')
        v.line(x0 + sx * 12.5, PISO - 6, x0 + sx * 12.5, PISO + 5, 'c')
        v.line(x0 - sx * 4, TOPO - 15, x0 + sx * 4, TOPO - 15, 'c')
        v.line(x0 - sx * 12.5, TOPO - 5, x0 - sx * 12.5, TOPO + 4, 'c')
    # isolante, manta e dissipadores (vistos alem do corte: o plano passa entre os dois)
    v.rect(-113, PISO, 113, PISO + 3, 'v', 'url(#hi)')
    v.rect(-100, PISO + 3, 100, PISO + 4.5, 'v', '#b8321f')
    v.rect(-100, PISO + 4.5, 100, PISO + 9.5, 'v', '#d5dade')
    pitch = 200 / 13
    for i in range(13):
        x = -100 + pitch * (i + 0.5)
        v.rect(x - 1.1, PISO + 9.5, x + 1.1, PISO + 33.5, 'v', '#d5dade')
    # TH2 na ponta do dissipador
    v.rect(100.2, PISO + 11, 104, PISO + 27, 'v', '#eef0f2')
    # M2 no fundo (oculta pelos dissipadores)
    v.rect(-30, PISO + M2_Y - 30, 30, PISO + M2_Y + 30, 'h')
    v.circle(0, PISO + M2_Y, 28, 'h')
    # espacadores e prateleira perfurada
    for sx in (-1, 1):
        v.rect(sx * POST - 3, PISO, sx * POST + 3, PISO + SHELF, 'v', '#eef0f2')
        v.line(sx * POST, PISO - 4, sx * POST, PISO + SHELF + 6, 'c')
    sy = PISO + SHELF
    x = -SHELF_W / 2
    while x < SHELF_W / 2 - 0.1:
        v.rect(x, sy, min(x + 3, SHELF_W / 2), sy + 1.5, 'v', '#9aa3ab')
        x += 8
    for sx in (-1, 1):
        v.rect(sx * SHELF_W / 2, sy + 1.5, sx * (SHELF_W / 2 - 1.5), sy - 10, 'v', '#9aa3ab')
    # amostras (linha fina, so referencia)
    v.rect(-80, sy + 1.5, -28, sy + 11, 't')
    v.rect(10, sy + 1.5, 60, sy + 9, 't')
    # refletor, soquetes e lampadas
    v.rect(-115, PISO + H_PAR - 1.0, 115, PISO + H_PAR - 0.5, 'v', '#9aa3ab')
    for lx in LAMP_X:
        v.rect(lx - 5, PISO + H_PAR - 9, lx + 5, PISO + H_PAR - 1, 'v', '#fff')
        X, Y = P(lx, PISO + H_PAR - 16)
        s.add(f'<ellipse cx="{X:.2f}" cy="{Y:.2f}" rx="{4.5 * k:.2f}" ry="{7 * k:.2f}" class="v" style="fill:#fff6d0"/>')
        v.line(lx, PISO + H_PAR - 30, lx, PISO + H_PAR + ESP + 6, 'c')
    # TH1 sob a tampa e LM35 pendurado (alem do corte)
    v.rect(-36, PISO + H_PAR - 7, -14, PISO + H_PAR - 1, 'v', '#eef0f2')
    v.rect(53, PISO + SHELF + 73, 57.5, PISO + SHELF + 78, 'v', '#111')
    v.line(55.2, PISO + SHELF + 78, 55.2, PISO + H_PAR - 1, 't')
    # cooler M1 por fora da lateral direita (cortado no centro)
    fx = EXT / 2
    v.rect(fx, fy - 40, fx + 25, fy - 36, 'v', '#555')
    v.rect(fx, fy + 36, fx + 25, fy + 40, 'v', '#555')
    v.rect(fx + 8, fy - 14, fx + 20, fy + 14, 'v', '#555')
    for sgn in (-1, 1):
        v.line(fx + 9, fy + sgn * 16, fx + 19, fy + sgn * 34, 'v')
    v.line(fx + 26.5, fy - 40, fx + 26.5, fy + 40, 'v')
    v.line(fx - 6, fy, fx + 32, fy, 'c')
    # parafusos M4 do cooler (centro)
    for dy in (-35.75, 35.75):
        v.line(fx - 9, fy + dy, fx + 28, fy + dy, 'c')
    # fluxo de ar
    ar = [
        [(-EXT / 2 - 30, PISO + VENT_Y[0]), (-EXT / 2 - 2, PISO + VENT_Y[0]), (-105, PISO + 40)],
        [(-EXT / 2 - 30, PISO + VENT_Y[1]), (-EXT / 2 - 2, PISO + VENT_Y[1]), (-105, PISO + 52)],
        [(-100, PISO + 40), (-45, PISO + 46), (-12, PISO + 100), (-18, PISO + 160), (25, PISO + 200), (100, TOPO - FAN_C + 4)],
        [(-100, PISO + 52), (25, PISO + 54), (52, PISO + 105), (80, PISO + 160), (104, TOPO - FAN_C - 10)],
        [(EXT / 2 + 28, TOPO - FAN_C - 4), (EXT / 2 + 48, TOPO - FAN_C - 26)],
    ]
    for pts in ar:
        pp = [P(x, y) for x, y in pts]
        d = 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in pp)
        s.add(f'<path d="{d}" class="air"/>')
        (x1, y1), (x2, y2) = pp[-2], pp[-1]
        s.arrow(x2, y2, x2 - x1, y2 - y1, 1.8, fill=AZUL)
    s.text(*P(-EXT / 2 - 32, PISO + 62), T('ar frio', 'cool air'), size=2.2, anchor='start', fill=AZUL)
    s.text(*P(EXT / 2 + 36, TOPO - FAN_C - 33), T('ar quente', 'warm air'), size=2.2, anchor='start', fill=AZUL)

    # ---- cotas
    y0p = P(0, 0)[1]
    dim_h(s, P(-BASE / 2, 0)[0], P(BASE / 2, 0)[0], y0p, y0p, y0p + 6, '300')
    yt = P(0, TOPO + ANG_E)[1]
    dim_h(s, P(-EXT / 2, 0)[0], P(EXT / 2, 0)[0], yt, yt, yt - 7, '250')
    yi = P(0, PISO + H_PAR - 40)[1]
    dim_h(s, P(-INT / 2, 0)[0], P(INT / 2, 0)[0], yi, yi, yi, '238 ' + T('(interno)', '(inside)'))
    xl = P(-BASE / 2, 0)[0]
    dim_v(s, P(0, 0)[1], P(0, PISO)[1], xl, xl, xl - 4, '15')
    xw = P(-EXT / 2, 0)[0]
    dim_v(s, P(0, PISO)[1], P(0, PISO + H_PAR)[1], xw - 1.5, xw - 1.5, xl - 4, '244')
    dim_v(s, P(0, PISO + H_PAR)[1], P(0, TOPO)[1], xw, xw, xl - 4, '6')
    dim_v(s, P(0, 0)[1], P(0, TOPO)[1], xl, xw, xl - 11, '265')
    xs_ = P(-90, 0)[0]
    dim_v(s, P(0, PISO)[1], P(0, PISO + SHELF)[1], xs_, xs_, xs_, '70')
    xu = P(-22, 0)[0]
    dim_v(s, P(0, PISO + SHELF + 1.5)[1], P(0, PISO + H_PAR - 23)[1], xu, xu, xu, T('≈ 148 útil', '≈ 148 clear'))
    xf = P(EXT / 2 + 34, 0)[0]
    dim_v(s, P(0, TOPO)[1], P(0, TOPO - FAN_C)[1], P(EXT / 2, 0)[0], P(EXT / 2 + 27, 0)[0], xf, '62', lado=1)
    xv = P(-EXT / 2 - 12, 0)[0]
    dim_v(s, P(0, PISO)[1], P(0, PISO + VENT_Y[0])[1], P(-EXT / 2 - 1.5, 0)[0], P(-EXT / 2, 0)[0], xv, '35')
    dim_v(s, P(0, PISO + VENT_Y[0])[1], P(0, PISO + VENT_Y[1])[1], P(-EXT / 2, 0)[0], P(-EXT / 2, 0)[0], xv, '15')
    xh = P(-104, 0)[0]
    dim_v(s, P(0, PISO)[1], P(0, PISO + 33.5)[1], P(-100, 0)[0], P(-100, 0)[0], xh - 3, '33,5' if LANG == 'pt' else '33.5')

    # ---- baloes (item da lista de materiais)
    B = [
        ('1', (-30, TOPO), (-30, TOPO + 26)),
        ('4', (-EXT / 2 + 3, PISO + 150), (-EXT / 2 - 26, PISO + 150)),
        ('5', (EXT / 2 - 3, PISO + 110), (EXT / 2 + 30, PISO + 110)),
        ('6', (100, 7), (115, -22)),
        ('7', (EXT / 2 + ANG_E / 2, TOPO - 12), (EXT / 2 + 14, TOPO + 18)),
        ('8', (-108 + 30, PISO + 1.5), (-60, -22)),
        ('9', (-40, PISO + 3.8), (-25, -22)),
        ('10', (-56, PISO + 25), (-85, PISO + 120)),
        ('11', (-60, PISO + SHELF + 0.8), (-110, PISO + 190)),
        ('12', (-POST, PISO + 40), (-75, -22)),
        ('13', (100, PISO + H_PAR - 0.8), (95, TOPO + 26)),
        ('14', (45, PISO + H_PAR - 16), (55, TOPO + 26)),
        ('15', (EXT / 2 + 14, TOPO - FAN_C - 8), (EXT / 2 + 30, TOPO - FAN_C - 52)),
        ('16', (25, PISO + M2_Y + 20), (60, PISO + 52)),
        ('17', (-25, PISO + H_PAR - 4), (-60, TOPO + 26)),
        ('17', (102, PISO + 19), (90, PISO + 50)),
        ('18', (55.2, PISO + SHELF + 75), (85, PISO + SHELF + 95)),
    ]
    for n, (x, y), (bx, by) in B:
        X, Y = P(x, y)
        BX, BY = P(bx, by)
        balao(s, X, Y, n, BX, BY)
    # plano do corte e notas da vista
    s.text(31, 31, T('Corte no plano médio\n(frente removida;\nolhando para o fundo)',
                                                  'Cut at mid-depth\n(front removed;\nlooking at the back)'),
           size=2.1, anchor='start')


# ------------------------------------------------------------------ folha 2: paineis
def painel(s, x, y, w, h, wp, hp, chave, k=0.25, frente=None, cotas=(), linha_corte=None):
    """Desenha um painel de wp x hp mm em escala k dentro do quadro (x, y, w, h)."""
    pw, ph = wp * k, hp * k
    x0 = x + 11 + (w - 14 - pw) / 2
    y0 = y + 13
    s.rect(x0, y0, pw, ph, 'v', 'rgba(29,100,200,0.06)')

    def Pp(xp, yp):
        return x0 + xp * k, y0 + (hp - yp) * k

    for letra, d, pts in FUROS[chave]:
        r = max(d / 2 * k, 0.32)
        for xp, yp in pts:
            X, Y = Pp(xp, yp)
            s.circle(X, Y, r, 'v', '#fff')
            if d >= 30:
                s.line(X - r - 1.5, Y, X + r + 1.5, Y, 'c')
                s.line(X, Y - r - 1.5, X, Y + r + 1.5, 'c')
        # etiqueta do grupo junto ao primeiro furo
        X, Y = Pp(*pts[0])
        s.text(X + r + 0.6, Y - r - 0.3, letra, size=1.9, anchor='start', weight='bold', fill=AZUL)
    dim_h(s, x0, x0 + pw, y0, y0, y0 - 4, f'{wp:g}', size=2.0)
    dim_v(s, y0, y0 + ph, x0, x0, x0 - 4, f'{hp:g}', size=2.0)
    for tipo, a, b, at, txt in cotas:
        if tipo == 'h':
            (X1, Y1), (X2, _) = Pp(a, at), Pp(b, at)
            yd = Y1 if at >= 0 else Y1
            dim_h(s, X1, X2, Y1, Y1, yd, txt, size=1.9)
        else:
            (X1, Y1), (_, Y2) = Pp(at, a), Pp(at, b)
            dim_v(s, Y1, Y2, X1, X1, X1, txt, size=1.9, lado=1)
    if frente:
        lado, rot = frente
        fx, fy = {'b': (x0 + pw / 2, y0 + ph + 3.2), 'r': (x0 + pw + 2.2, y0 + ph / 2),
                  'l': (x0 - 9.5, y0 + ph / 2 + 9)}[lado]
        s.text(fx, fy, T('FRENTE', 'FRONT'), size=1.9, rot=rot, fill='#555')
    if linha_corte is not None:
        X1, Y = Pp(0, linha_corte)
        X2, _ = Pp(wp, linha_corte)
        s.line(X1 - 4, Y, X2 + 4, Y, 'cc')
        for xx, sg in ((X1 - 4, 1), (X2 + 4, -1)):
            s.line(xx, Y, xx, Y + 3.5, 'v')
            s.arrow(xx + sg * 0.01, Y + 4.8, 0, 1, 1.6)
            s.text(xx - sg * 1.6, Y + 6.2, 'A', size=2.6, weight='bold')
    return Pp


def plano(s, x, y):
    k = 0.1
    x0, y0 = x + 13, y + 15
    s.rect(x0, y0, 100, 100, 'v', 'url(#hw)')
    s.add(f'<rect x="{x0}" y="{y0}" width="100" height="100" class="v" style="fill:rgba(255,255,255,0.55)"/>')
    for n, px, py, pw, ph in PLANO:
        s.rect(x0 + px * k, y0 + py * k, pw * k, ph * k, 'v', '#e8f0fb')
        s.text(x0 + (px + pw / 2) * k, y0 + (py + ph / 2) * k + 0.9, n, size=2.6, weight='bold')
        s.text(x0 + (px + pw / 2) * k, y0 + (py + ph / 2) * k + 4.1, f'{pw:g}×{ph:g}', size=1.6)
    s.text(x0 + 70, y0 + 72, T('SOBRA ≈ 0,69 m²\n(reposição ou 2ª câmara)', 'OFFCUT ≈ 0.69 m²\n(spares or a 2nd chamber)'),
           size=2.0, fill='#333')
    dim_h(s, x0, x0 + 100, y0, y0, y0 - 4, '1000', size=2.0)
    dim_v(s, y0, y0 + 100, x0, x0, x0 - 4, '1000', size=2.0)
    dim_v(s, y0, y0 + 25, x0 + 100, x0 + 100, x0 + 103, '250', size=1.8, lado=1)
    s.text(x0 + 70, y0 + 86, T('chapa PC compacto cristal 6 mm\nkerf 3 mm', 'clear solid PC sheet 6 mm\nkerf 3 mm'),
           size=2.0)


def prateleira(s, x, y):
    k = 0.25
    L = SHELF_W * k
    x0, y0 = x + 8 + (71 - 12 - L) / 2, y + 14
    s.rect(x0, y0, L, L, 'v', 'url(#hf)')
    for cx, cy in ((8, 8), (8, 224), (224, 8), (224, 224)):
        s.circle(x0 + cx * k, y0 + cy * k, 2.25 * k + 0.3, 'v', '#fff')
    dim_h(s, x0, x0 + L, y0, y0, y0 - 4, '232', size=2.0)
    dim_v(s, y0, y0 + L, x0, x0, x0 - 4, '232', size=2.0)
    s.text(x0 + L / 2, y0 + L + 5, T('Al 1,5 mm · furos Ø5 passo 8 (40 %)\n4 × Ø4,5 a 8 mm dos cantos · dobra 10 mm',
                                     'Al 1.5 mm · Ø5 holes, 8 pitch (40 %)\n4 × Ø4.5 at 8 mm from corners · 10 mm flange'),
           size=1.8)


def cantoneiras(s, x, y):
    # perfil 1:1
    px, py = x + 6, y + 14
    s.poly([(px, py), (px + 1.5, py), (px + 1.5, py + 23.5), (px + 25, py + 23.5), (px + 25, py + 25), (px, py + 25)], 'v', '#9aa3ab')
    dim_h(s, px, px + 25, py + 25, py + 25, py + 29, '25', size=1.9)
    dim_v(s, py, py + 25, px, px, px - 3, '25', size=1.9)
    s.text(px + 13, py + 35, T('PERFIL 1:1\nesp. 1,5', 'PROFILE 1:1\nthk. 1.5'), size=1.8)
    # barras de 1 m (1:10)
    bx = x + 40
    barras = [[('a', 250), ('a', 250), ('b', 238), ('b', 238)], [('b', 238), ('b', 238), ('c', 200), ('c', 200)]]
    for i, barra in enumerate(barras):
        yy = y + 16 + i * 13
        s.rect(bx, yy, 100 * 0.93, 3.5, 't', '#f2f2f2')
        cx = bx
        for letra, comp in barra:
            w = comp * 0.093
            s.rect(cx, yy, w, 3.5, 'v', '#c9ced3')
            s.text(cx + w / 2, yy + 2.6, f'{letra} {comp}', size=1.6)
            cx += w + 3 * 0.093
        s.text(bx - 1.5, yy + 2.6, T(f'barra {i + 1}', f'bar {i + 1}'), size=1.7, anchor='end')
    s.text(bx + 46, y + 47, T('2 barras de 1 m · escala 1:10', '2 bars of 1 m · scale 1:10'), size=1.8, fill='#333')
    linhas = T(
        [('a', '250', '2', 'base e topo do fundo'), ('b', '238', '4', 'base e topo das laterais'),
         ('c', '200', '2', 'verticais do fundo')],
        [('a', '250', '2', 'back, bottom and top'), ('b', '238', '4', 'sides, bottom and top'),
         ('c', '200', '2', 'back verticals')])
    return linhas


# ------------------------------------------------------------------ textos
def textos():
    return {
        'pt': dict(
            arquivo='Desenho_Mecanico_Rev_A.pdf', titulo='CÂMARA TÉRMICA COM CONTROLE PWM',
            sub=['MONTAGEM · CORTE A-A · LISTA DE MATERIAIS', 'PLANO DE CORTE · FURAÇÃO DOS PAINÉIS'],
            folha='FOLHA', revs=[('A', 'Release inicial: câmara de PC 6 mm 250 × 250 × 250 (Rev. D do PIDL-ESQ-001).', DATA)],
            corte='CORTE A-A · ESCALA 1:2', bom='LISTA DE MATERIAIS (MECÂNICA)',
            bom_h=('ITEM', 'DESCRIÇÃO', 'ESPECIFICAÇÃO', 'QTD.'),
            termico='DIMENSIONAMENTO TÉRMICO', notas='NOTAS DE MONTAGEM',
            plano='PLANO DE CORTE · 1:10', tampa='[1] TAMPA · 1:4', fundo='[2] FUNDO · 1:4 (vista de trás)',
            porta='[3] PORTA · 1:4', lat_e='[4] LATERAL ESQ. · 1:4', lat_d='[5] LATERAL DIR. · 1:4',
            prat='[11] PRATELEIRA · 1:4', cant='[7] CANTONEIRAS', furos='TABELA DE FUROS',
            furos_h=('FURO', 'Ø', 'QTD.', 'PAINÉIS', 'FUNÇÃO'),
            cant_h=('POS.', 'COMPR.', 'QTD.', 'ONDE'),
            escala1='1:2', escala2='INDICADA',
            nota2='Cotas em mm. Furos sem cota de posição: ver coordenadas no arquivo desenho_mecanico.py (dicionário FUROS).',
        ),
        'en': dict(
            arquivo='Mechanical_Drawing_Rev_A_EN.pdf', titulo='THERMAL CHAMBER WITH PWM CONTROL',
            sub=['ASSEMBLY · SECTION A-A · BILL OF MATERIALS', 'CUTTING PLAN · PANEL DRILLING'],
            folha='SHEET', revs=[('A', 'Initial release: 6 mm PC chamber 250 × 250 × 250 (Rev. D of PIDL-ESQ-001).', DATA)],
            corte='SECTION A-A · SCALE 1:2', bom='BILL OF MATERIALS (MECHANICAL)',
            bom_h=('ITEM', 'DESCRIPTION', 'RATING', 'QTY'),
            termico='THERMAL SIZING', notas='ASSEMBLY NOTES',
            plano='CUTTING PLAN · 1:10', tampa='[1] TOP · 1:4', fundo='[2] BACK · 1:4 (seen from behind)',
            porta='[3] DOOR · 1:4', lat_e='[4] LEFT SIDE · 1:4', lat_d='[5] RIGHT SIDE · 1:4',
            prat='[11] SHELF · 1:4', cant='[7] ANGLES', furos='HOLE TABLE',
            furos_h=('HOLE', 'Ø', 'QTY', 'PANELS', 'PURPOSE'),
            cant_h=('POS.', 'LENGTH', 'QTY', 'WHERE'),
            escala1='1:2', escala2='AS SHOWN',
            nota2='Dimensions in mm. Holes without a position dimension: see the coordinates in desenho_mecanico.py (FUROS dict).',
        ),
    }


BOM = [
    ('1', 'Tampa · PC compacto cristal', 'Top · clear solid PC', '250 × 250 × 6', '1'),
    ('2', 'Fundo · PC', 'Back · PC', '250 × 244 × 6', '1'),
    ('3', 'Porta · PC', 'Door · PC', '250 × 243 × 6', '1'),
    ('4', 'Lateral esquerda (frestas) · PC', 'Left side (vents) · PC', '238 × 244 × 6', '1'),
    ('5', 'Lateral direita (cooler) · PC', 'Right side (fan) · PC', '238 × 244 × 6', '1'),
    ('6', 'Base de MDF + 4 pés de borracha', 'MDF base + 4 rubber feet', '300 × 300 × 15', '1'),
    ('7', 'Cantoneira de alumínio (ver folha 2)', 'Aluminium angle (see sheet 2)', '25 × 25 × 1,5|25 × 25 × 1.5', '8'),
    ('8', 'Isolante de fibra cerâmica', 'Ceramic-fibre insulation', '226 × 226 × 3', '1'),
    ('9', 'Manta de silicone H1 (PIDL-ESQ-001)', 'Silicone heater H1 (PIDL-ESQ-001)', '200 × 200 · 80 W', '1'),
    ('10', 'Dissipador aletado de alumínio', 'Finned aluminium heatsink', '200 × 100 × 30', '2'),
    ('11', 'Prateleira de alumínio perfurado', 'Perforated aluminium shelf', '232 × 232 × 1,5|232 × 232 × 1.5', '1'),
    ('12', 'Espaçador: tubo Al + parafuso M4 × 90 + porca-garra', 'Spacer: Al tube + M4 × 90 screw + tee nut',
     'Ø8 × 70', '4'),
    ('13', 'Refletor de alumínio', 'Aluminium reflector', '230 × 230 × 0,5|230 × 230 × 0.5', '1'),
    ('14', 'Soquete T10 + lâmpada W5W (EL1-EL5)', 'T10 socket + W5W lamp (EL1-EL5)', '12 V · 5 W', '5'),
    ('15', 'Ventoinha de exaustão M1 + grade', 'Exhaust fan M1 + grille', '80 × 80 × 25', '1'),
    ('16', 'Ventoinha de circulação M2', 'Circulation fan M2', '60 × 60 × 15', '1'),
    ('17', 'Termostato KSD301 (TH1 ar, TH2 dissipador)', 'KSD301 thermostat (TH1 air, TH2 heatsink)', '85 °C · 120 °C', '2'),
    ('18', 'Sensor LM35DZ (TS1)', 'LM35DZ sensor (TS1)', 'TO-92', '1'),
    ('19', 'Dobradiça de canto inox', 'Stainless corner hinge', '40 mm', '2'),
    ('20', 'Puxador', 'Handle', 'entre furos 64|64 mm centres', '1'),
    ('21', 'Fecho magnético de móvel', 'Magnetic cabinet catch', '—', '1'),
    ('22', 'Vedação perfil D de silicone', 'Silicone D-profile seal', '9 × 8 · 1 m', '1'),
    ('23', 'Prensa-cabo PG7', 'PG7 cable gland', 'cabo Ø3-6,5|cable Ø3-6.5', '2'),
    ('24', 'Parafuso M4 × 12 inox + porca autotravante + 2 arruelas', 'Stainless M4 × 12 screw + lock nut + 2 washers',
     'A2', '64'),
    ('25', 'Parafusos M4 × 35 (M1) · M3 × 30 (M2) · M3 × 10 (TH1)', 'Screws M4 × 35 (M1) · M3 × 30 (M2) · M3 × 10 (TH1)',
     'A2', '4+4+2'),
    ('26', 'Parafuso para madeira (cantoneiras na base)', 'Wood screw (angles to base)', '3,5 × 16|3.5 × 16', '12'),
    ('27', 'Silicone RTV alta temperatura + pasta térmica', 'High-temp RTV silicone + thermal paste', '≥ 250 °C', '1'),
]

NOTAS = {
    'pt': [
        'Policarbonato compacto cristal 6 mm: uso contínuo até ~115 °C. TH1 (85 °C) e o corte do firmware (78 °C) deixam margem.',
        'Cortar com serra de dente fino (≥ 60 dentes) ou lâmina para acrílico, com o filme protetor. Lixar e quebrar as bordas 0,5 mm.',
        'Furar com broca afiada em baixa rotação e madeira por baixo. Furos A em Ø5 para M4: folga para a dilatação do PC (~1 mm em 250 mm de 20 a 80 °C).',
        'Não usar cola de solvente, cianoacrilato nem óleo de corte: trincam o PC por tensão. Vedar frestas com silicone RTV neutro de alta temperatura.',
        'Cantoneiras por fora nas 8 arestas fixas; a frente fica livre para a porta. M4 inox com arruela dos dois lados, aperto leve.',
        'Ordem: cantoneiras inferiores na base → fundo e laterais → verticais do fundo → tampa e cantoneiras superiores → porta, fecho e vedação.',
        'Manta colada sob os dissipadores com pasta térmica, sobre o isolante. TH2 parafusado na ponta do dissipador. Nada de PC a menos de 15 mm das aletas.',
        'M2 no fundo, sob a prateleira, soprando ao longo das aletas. A prateleira sai pela porta, apoiada nos 4 espaçadores.',
        'TH1 sob a tampa; LM35 pendurado ~75 mm acima da prateleira, fora do feixe das lâmpadas. Fios saem pelos prensa-cabos do fundo.',
        'Fluxo de ar: entra pelas frestas da lateral esquerda (embaixo), passa pelos dissipadores, sobe pela prateleira e sai pelo cooler M1 (lateral direita, em cima).',
        'Remover o filme protetor só no fim da montagem.',
    ],
    'en': [
        '6 mm clear solid polycarbonate: continuous use up to ~115 °C. TH1 (85 °C) and the firmware cut-off (78 °C) leave margin.',
        'Cut with a fine-tooth blade (≥ 60 teeth) or an acrylic blade, with the protective film on. Sand and break the edges 0.5 mm.',
        'Drill with a sharp bit at low speed, wood backing underneath. A holes are Ø5 for M4: clearance for PC expansion (~1 mm over 250 mm from 20 to 80 °C).',
        'Do not use solvent cement, cyanoacrylate or cutting oil: they stress-crack PC. Seal gaps with neutral high-temperature RTV silicone.',
        'Angles outside on the 8 fixed edges; the front stays free for the door. Stainless M4 with a washer on both sides, light torque.',
        'Order: bottom angles on the base → back and sides → back verticals → top and top angles → door, catch and seal.',
        'Heater bonded under the heatsinks with thermal paste, on the insulation. TH2 screwed to the heatsink end. No PC within 15 mm of the fins.',
        'M2 on the back, under the shelf, blowing along the fins. The shelf comes out through the door, resting on the 4 spacers.',
        'TH1 under the top; LM35 hanging ~75 mm above the shelf, out of the lamp beam. Wires exit through the cable glands on the back.',
        'Airflow: in through the left-side vents (low), across the heatsinks, up through the shelf and out through fan M1 (right side, high).',
        'Remove the protective film only at the end of assembly.',
    ],
}

TERMICO = {
    'pt': [('Volume interno', '238 × 238 × 244 mm = 13,8 L'), ('Área útil da prateleira', '232 × 232 mm, ~148 mm livres'),
           ('Perda térmica', 'UA ≈ 1,6 W/K (PC U ≈ 3,9 W/m²K + base)'), ('Capacidade · constante', '≈ 1640 J/K · τ ≈ 1000 s'),
           ('Potência', '5 × 5 W lâmpadas + 80 W manta = 105 W'), ('ΔT de regime (100 %)', 'só lâmpadas +16 °C · com manta +66 °C'),
           ('Simulado (amb. 25 °C)', '25→45 °C 12 min · 45→70 °C 20 min · 70→35 °C 8 min'),
           ('Dissipador', 'máx. ≈ 89 °C a 70 °C no ar (TH2 abre a 120 °C)')],
    'en': [('Inside volume', '238 × 238 × 244 mm = 13.8 L'), ('Shelf area', '232 × 232 mm, ~148 mm clear'),
           ('Heat loss', 'UA ≈ 1.6 W/K (PC U ≈ 3.9 W/m²K + base)'), ('Capacity · time constant', '≈ 1640 J/K · τ ≈ 1000 s'),
           ('Power', '5 × 5 W lamps + 80 W heater = 105 W'), ('Steady ΔT (100 %)', 'lamps only +16 °C · with heater +66 °C'),
           ('Simulated (25 °C amb.)', '25→45 °C 12 min · 45→70 °C 20 min · 70→35 °C 8 min'),
           ('Heatsink', 'max. ≈ 89 °C at 70 °C air (TH2 opens at 120 °C)')],
}

FUROS_TAB = {
    'pt': [('A', '5,0', '64', '1 2 3 4 5', 'M4: cantoneiras, dobradiças, puxador, fecho, refletor'),
           ('B', '76', '1', '5', 'abertura do cooler M1'), ('C', '4,5', '4', '5', 'fixação do M1 (quadrado 71,5)'),
           ('D', '8,0', '18', '4', 'frestas de entrada (2 × 9, passo 18)'),
           ('E', '3,5', '6', '1 2', 'M3: M2 (quadrado 50) e TH1 (entre furos 24)'),
           ('F', '12,5', '2', '2', 'prensa-cabos PG7'), ('G', '6,0', '6', '1', 'fios das lâmpadas (5) e do LM35 (1)')],
    'en': [('A', '5.0', '64', '1 2 3 4 5', 'M4: angles, hinges, handle, catch, reflector'),
           ('B', '76', '1', '5', 'fan M1 opening'), ('C', '4.5', '4', '5', 'M1 mounting (71.5 square)'),
           ('D', '8.0', '18', '4', 'intake vents (2 × 9, 18 pitch)'),
           ('E', '3.5', '6', '1 2', 'M3: M2 (50 square) and TH1 (24 centres)'),
           ('F', '12.5', '2', '2', 'PG7 cable glands'), ('G', '6.0', '6', '1', 'lamp (5) and LM35 (1) wires')],
}


# ------------------------------------------------------------------ html
def caixa(x, y, w, h, titulo, corpo=''):
    return (f'<div class="blk box" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">'
            f'<div class="bt">{esc(titulo)}</div><div class="boxbody">{corpo}</div></div>')


def tabela(cab, linhas, larg):
    if any(cab):
        th = '<tr>' + ''.join(f'<th{f" style=\"width:{w}mm\"" if w else ""}>{esc(c)}</th>' for c, w in zip(cab, larg)) + '</tr>'
    else:
        th = '<tr>' + ''.join(f'<td style="width:{w}mm;padding:0;border:0;height:0"></td>' if w else '<td style="padding:0;border:0;height:0"></td>' for w in larg) + '</tr>'
    tr = ''.join('<tr>' + ''.join(f'<td>{esc(str(c))}</td>' for c in ln) + '</tr>' for ln in linhas)
    return f'<table class="grid">{th}{tr}</table>'


def furos_conferidos():
    """Conta os furos de cada letra (confere a tabela)."""
    cont = {}
    for grupos in FUROS.values():
        for letra, _, pts in grupos:
            cont[letra] = cont.get(letra, 0) + len(pts)
    return cont


def folha1(t, lang):
    s = Svg()
    corte(s)
    out = [f'<section class="sheet">{F.borda(t["folha"] + " 1/2", DES, REV)}']
    out.append(caixa(27, 17, 239, 196, t['corte']))
    pt = lang == 'pt'

    def sp(v):
        return v.split('|')[0 if pt else 1] if '|' in v else v
    linhas = [(n, a if pt else b, sp(c), q) for n, a, b, c, q in BOM]
    out.append(caixa(268, 33, 137, 125, t['bom'], tabela(t['bom_h'], linhas, [9, None, 30, 11])))
    out.append(caixa(268, 160, 137, 62, t['termico'], tabela(('', ''), TERMICO[lang], [40, None])))
    nts = ''.join(f'<li>{esc(n)}</li>' for n in NOTAS[lang])
    out.append(caixa(27, 215, 239, 65, t['notas'], f'<ol class="ng">{nts}</ol>'))
    out.append(f'<div class="svgbox" style="left:0;top:0">{s.svg()}</div>')
    out.append(F.tabela_revisoes(lang, t['revs']))
    out.append(F.carimbo(lang, DES, REV, DATA, 1, TOTAL, t['titulo'], t['sub'][0], t['escala1']))
    out.append('</section>')
    return ''.join(out)


def folha2(t, lang):
    s = Svg()
    out = [f'<section class="sheet">{F.borda(t["folha"] + " 2/2", DES, REV)}']
    Q = {
        'plano': (27, 17, 126, 117), 'tampa': (155, 17, 82, 117), 'fundo': (239, 17, 82, 117),
        'porta': (323, 17, 82, 117), 'lat_e': (27, 136, 82, 86), 'lat_d': (111, 136, 82, 86),
        'prat': (195, 136, 71, 86), 'cant': (268, 136, 137, 86),
    }
    for chave, (x, y, w, h) in Q.items():
        out.append(caixa(x, y, w, h, t[chave]))
    plano(s, *Q['plano'][:2])
    x, y, w, h = Q['tampa']
    painel(s, x, y + 6, w, h, 250, 250, 'tampa', frente=('b', 0), linha_corte=125,
           cotas=[('h', 35, 80, 112, '45'), ('v', 125, 170, 12, '45')])
    x, y, w, h = Q['fundo']
    painel(s, x, y + 6, w, h, 250, 244, 'fundo',
           cotas=[('h', 100, 150, M2_Y + 37, '50'), ('v', 0, M2_Y, 160, f'{M2_Y:g}'), ('v', 0, 150, 228, '150')])
    x, y, w, h = Q['porta']
    painel(s, x, y + 6, w, h, 250, 243, 'porta',
           cotas=[('v', 93, 157, 222, '64'), ('v', 0, 45, 30, '45'), ('v', 185, 243, 30, '58')])
    x, y, w, h = Q['lat_e']
    painel(s, x, y - 2, w, h, 238, 244, 'lat_e', frente=('r', 90),
           cotas=[('h', 47, 65, 64, '18'), ('v', 0, VENT_Y[0], 205, '35'), ('v', VENT_Y[0], VENT_Y[1], 205, '15')])
    x, y, w, h = Q['lat_d']
    fc = H_PAR + ESP - FAN_C
    painel(s, x, y - 2, w, h, 238, 244, 'lat_d', frente=('l', -90),
           cotas=[('h', 83.25, 154.75, fc + 46, '71,5' if lang == 'pt' else '71.5'), ('v', 0, fc, 200, f'{fc:g}')])
    prateleira(s, *Q['prat'][:2])
    linhas_c = cantoneiras(s, *Q['cant'][:2])
    out.append(f'<div class="ctab" style="left:{268 + 3}mm;top:{136 + 55}mm;width:131mm">'
               + tabela(t['cant_h'], linhas_c, [10, 16, 11, None]) + '</div>')
    cont = furos_conferidos()
    tab = []
    for row in FUROS_TAB[lang]:
        assert int(row[2]) == cont[row[0]], (row[0], row[2], cont[row[0]])
        tab.append(row)
    corpo = tabela(t['furos_h'], tab, [11, 12, 11, 22, None]) + f'<p class="rem">{esc(t["nota2"])}</p>'
    out.append(caixa(27, 224, 239, 56, t['furos'], corpo))
    out.append(f'<div class="svgbox" style="left:0;top:0">{s.svg()}</div>')
    out.append(F.carimbo(lang, DES, REV, DATA, 2, TOTAL, t['titulo'], t['sub'][1], t['escala2']))
    out.append('</section>')
    return ''.join(out)


CSS_EXTRA = '''
.box .boxbody { position: absolute; top: 8.5mm; left: 3mm; right: 3mm; bottom: 2mm; overflow: hidden; }
table.grid th, table.grid td { border: 0.25mm solid #000; font-size: 2.3mm; padding: 0.55mm 1.1mm;
  text-align: left; vertical-align: top; }
table.grid th { font-size: 2.05mm; background: #eee; }
.box .rem { font-size: 2.2mm; margin: 1.4mm 0 0; }
ol.ng { margin: 0; padding-left: 5mm; font-size: 2.4mm; line-height: 1.3; }
ol.ng li { margin-bottom: 0.5mm; }
.ctab { position: absolute; }
.ctab table.grid th, .ctab table.grid td { font-size: 2.1mm; padding: 0.4mm 1mm; }
.rt th, .rt td { font-size: 2.2mm; padding: 0.55mm 1.1mm; }
.svgbox { pointer-events: none; }
svg.draw text { font-family: "DejaVu Sans Condensed", "Arial Narrow", Arial, sans-serif; fill: #000; }
svg.draw .v { stroke: #000; stroke-width: 0.3; fill: none; }
svg.draw .t { stroke: #000; stroke-width: 0.15; fill: none; }
svg.draw .h { stroke: #000; stroke-width: 0.18; fill: none; stroke-dasharray: 1.4 0.7; }
svg.draw .c { stroke: #000; stroke-width: 0.13; fill: none; stroke-dasharray: 3 0.7 0.6 0.7; }
svg.draw .cc { stroke: #000; stroke-width: 0.35; fill: none; stroke-dasharray: 5 1 1 1; }
svg.draw .fa { stroke: none; }
svg.draw .air { stroke: #1d64c8; stroke-width: 0.32; fill: none; stroke-dasharray: 1.6 0.8; }
'''


def gerar(lang):
    global LANG
    LANG = lang
    t = textos()[lang]
    corpo = folha1(t, lang) + folha2(t, lang)
    doc = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{DES} rev {REV}</title>'
           f'<style>{F.CSS}{CSS_EXTRA}</style></head><body>{corpo}</body></html>')
    caminho = os.path.join(BUILD, f'mecanico_{lang}.html')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'{lang}: {caminho}')
    return caminho, t['arquivo']


if __name__ == '__main__':
    os.makedirs(BUILD, exist_ok=True)
    for lg in ('pt', 'en'):
        h, nome = gerar(lg)
        F.pdf(h, os.path.join(AQUI, nome))
