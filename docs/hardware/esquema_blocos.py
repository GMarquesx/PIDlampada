"""
Blocos do esquema eletrico Rev. B - PIDlampada (SchemDraw).

Cada bloco funcional e' um desenho separado, salvo como SVG. A folha
(esquema_rev_b.py) posiciona todos na mesma escala - 1 unidade SchemDraw
= ESCALA_MM mm no papel - para que simbolos e textos tenham o mesmo
tamanho em todo o desenho, como num CAD.

Textos em portugues e ingles: T('pt', 'en'), escolhido por gerar(lang=).
Marcador de revisao: triangulo com "B" ao lado do que entrou ou mudou
na Rev. B.
"""
import os
import schemdraw
import schemdraw.elements as elm
from schemdraw.segments import SegmentPoly, SegmentText

schemdraw.use('svg')
schemdraw.config(font='DejaVu Sans Condensed', fontsize=17, lw=2.0, unit=2.5)

ESCALA_MM = 6.0          # mm de papel por unidade SchemDraw
NOTA = '#333333'
FS_NOTA = 15
TAG_W = 3.3              # largura das etiquetas de rede

LANG = 'pt'


def T(pt, en):
    return pt if LANG == 'pt' else en


class RevMark(elm.Element):
    """Triangulo de revisao (padrao de desenho tecnico)."""

    def __init__(self, rev='B', size=0.85, **kwargs):
        super().__init__(**kwargs)
        h = size * 0.866
        self.segments.append(SegmentPoly([(0, 0), (size, 0), (size / 2, h)], lw=1.8))
        self.segments.append(SegmentText((size / 2, h * 0.34), rev, fontsize=14,
                                         align=('center', 'center')))
        self.params['drop'] = (0, 0)


def rev(d, xy):
    d += RevMark().at(xy).theta(0)


def txt(d, xy, s, halign='left', size=FS_NOTA, color=NOTA):
    d += elm.Label().at(xy).label(s, fontsize=size, color=color, halign=halign)


def ref(d, xy, s, halign='left'):
    """Designador + valor, no tamanho dos rotulos de componente."""
    txt(d, xy, s, halign=halign, size=17, color='black')


def tag(d, side, s, at=None):
    t = elm.Tag(width=TAG_W)
    if at is not None:
        t = t.at(at)
    d += getattr(t, side)().label(s, fontsize=14)


def novo():
    return schemdraw.Drawing(show=False)


# ---------------------------------------------------------------------
# [1] ENTRADA, SELECAO DE FONTE E PROTECAO
# ---------------------------------------------------------------------
def bloco_entrada():
    d = novo()
    # chave de 2 posicoes: comum a direita, ATX em cima, bateria embaixo
    d += (sw := elm.SwitchSpdt2().at((7.0, 21.0)).left())
    txt(d, (6.6, 22.4), 'SW1', halign='center', size=17, color='black')
    ax, ay = sw.c          # entrada ATX
    bx, by = sw.b          # entrada bateria

    # J1: ATX +12 V (amarelo); GND do ATX vai ao terra comum
    tag(d, 'left', T('J1  ATX +12 V', 'J1  ATX +12 V'), at=(1.4, ay))
    d += elm.Line().at((1.4, ay)).to((ax, ay))

    # BT1: pack 3S - o polo + sobe e entra pela esquerda na outra posicao
    d += (bat := elm.Battery().at((2.6, by - 3.6)).up().length(2.6))
    ref(d, (2.0, by - 2.3), T('BT1\n3S 18650\n12,6 V máx.', 'BT1\n3S 18650\n12.6 V max.'), halign='right')
    d += elm.Line().at(bat.end).to((2.6, by))
    d += elm.Line().at((2.6, by)).to((bx, by))
    d += elm.Ground().at(bat.start)

    # comum -> F1 -> D1 -> no protegido
    d += elm.Line().at(sw.a).right().length(0.6)
    d += elm.Fuse().right().length(2.8).label(T('F1\n3 A retard.', 'F1\n3 A slow'), loc='top', ofst=0.3)
    d += elm.Schottky().right().length(2.8).label('D1  SS34', loc='top', ofst=0.3)
    d += elm.Line().right().length(0.8)
    d += (na := elm.Dot())

    d += elm.Zener().at(na.center).down().length(3.2)
    ref(d, (na.center[0] + 0.35, na.center[1] - 1.6), 'D2\nSMBJ15A')
    d += elm.Line().down().length(0.8)
    d += (g1 := elm.Dot())

    d += elm.Line().at(na.center).right().length(3.0)
    d += (nb := elm.Dot())
    d += elm.Capacitor(polar=True).down().length(3.2)
    ref(d, (nb.center[0] + 0.35, nb.center[1] - 1.6), 'C1\n1000 µF\n25 V')
    d += elm.Line().down().length(0.8)
    d += (g2 := elm.Dot())

    d += elm.Line().at(nb.center).right().length(3.0)
    d += (nc := elm.Dot())
    d += elm.Capacitor().down().length(3.2)
    ref(d, (nc.center[0] + 0.35, nc.center[1] - 1.6), 'C2\n100 nF')
    d += elm.Line().down().length(0.8)
    d += (g3 := elm.Dot())

    d += elm.Line().at(g1.center).to(g3.center)
    d += elm.Ground().at(g2.center)

    d += elm.Line().at(nc.center).right().length(1.8)
    d += elm.Vdd().label('+12 V PROT', ofst=0.15)
    return d


# ---------------------------------------------------------------------
# [2] REGULACAO 12 -> 5 V
# ---------------------------------------------------------------------
def bloco_regulacao():
    d = novo()
    u1 = elm.Ic(pins=[elm.IcPin(name='GND', side='left', slot='1/2'),
                      elm.IcPin(name='VIN', side='left', slot='2/2'),
                      elm.IcPin(name='GND', side='right', slot='1/2'),
                      elm.IcPin(name='VOUT', side='right', slot='2/2')],
                size=(5.0, 3.4), plblofst=0.25, pinspacing=1.4)
    d += (u1 := u1.at((5.0, 10.4)).right()
          .label(T('U1  MP1584 / LM2596\nbuck 12 → 5 V · 3 A', 'U1  MP1584 / LM2596\nbuck 12 → 5 V · 3 A'),
                 loc='top', ofst=0.35))
    d += elm.Line().at(u1.VIN).left().length(1.6)
    d += elm.Vdd().label('+12 V PROT', ofst=0.15)
    d += elm.Line().at(u1.inL1).left().length(0.9)
    d += elm.Ground()
    d += elm.Line().at(u1.inR1).right().length(0.9)
    d += elm.Ground()

    d += elm.Line().at(u1.VOUT).right().length(1.6)
    d += (n5 := elm.Dot())
    d += elm.Capacitor(polar=True).down().length(2.8)
    d += elm.Ground()
    ref(d, (n5.center[0] + 0.35, n5.center[1] - 1.4), 'C3\n100 µF')
    d += elm.Line().at(n5.center).right().length(2.6)
    d += (n5b := elm.Dot())
    d += elm.Capacitor().down().length(2.8)
    d += elm.Ground()
    ref(d, (n5b.center[0] + 0.35, n5b.center[1] - 1.4), 'C4\n10 µF')
    d += elm.Line().at(n5b.center).right().length(1.8)
    d += elm.Vdd().label('+5 V', ofst=0.15)
    return d


# ---------------------------------------------------------------------
# [3] CONTROLADOR
# ---------------------------------------------------------------------
def bloco_controlador():
    d = novo()
    pinos = [('GPIO19', 'DISP_DIO'), ('GPIO18', 'DISP_CLK'), ('GPIO35', 'PWR_OK_S'),
             ('GPIO34', 'V_SENSE'), ('GPIO32', 'TEMP_S'), ('GPIO26', 'FAN_GATE'),
             ('GPIO25', 'PWM_GATE')]
    n = len(pinos)
    pins = [elm.IcPin(name=p, side='right', slot=f'{i + 1}/{n}') for i, (p, _) in enumerate(pinos)]
    pins += [elm.IcPin(name='GND', side='left', slot='1/4'),
             elm.IcPin(name='GND', side='left', slot='2/4'),
             elm.IcPin(name='3V3', side='left', slot='3/4'),
             elm.IcPin(name='VIN', side='left', slot='4/4')]
    esp = elm.Ic(pins=pins, size=(5.6, 12.0), plblofst=0.3)
    d += (esp := esp.at((0, 0)).right().label('U2  ESP32 DevKit v1', loc='top', ofst=0.4))

    d += elm.Line().at(esp.VIN).left().length(1.6)
    d += elm.Vdd().label('+5 V', ofst=0.15)
    d += elm.Line().at(getattr(esp, '3V3')).left().length(1.6)
    d += elm.Vdd().label('+3V3', ofst=0.15)
    d += elm.Line().at(esp.inL1).left().length(1.0)
    d += elm.Ground()
    d += elm.Line().at(esp.inL2).left().length(1.0)
    d += elm.Ground()

    novos = {'GPIO26', 'GPIO18', 'GPIO19', 'GPIO32'}
    for pino, rede in pinos:
        p = getattr(esp, pino)
        d += elm.Line().at(p).right().length(1.4)
        tag(d, 'right', rede)
        if pino in novos:
            rev(d, (p[0] + 1.4 + TAG_W + 0.35, p[1] - 0.3))
    txt(d, (esp.inL1[0] - 1.6, esp.inL1[1] - 2.7),
        T('GPIO2: LED de status da própria placa.\nGPIO33 e GPIO27: reservados, sem ligação.',
          'GPIO2: on-board status LED.\nGPIO33 and GPIO27: reserved, not connected.'))
    return d


# ---------------------------------------------------------------------
# [4] SENSOR LM35DZ
# ---------------------------------------------------------------------
def bloco_sensor():
    d = novo()
    lm = elm.Ic(pins=[elm.IcPin(name='GND', side='left', slot='1/3'),
                      elm.IcPin(name='VOUT', side='left', slot='2/3'),
                      elm.IcPin(name='VS', side='left', slot='3/3')],
                size=(3.6, 4.2), plblofst=0.25)
    d += (lm := lm.at((0, 0)).right().label('TS1  LM35DZ\n10 mV/°C', loc='top', ofst=0.35))
    rev(d, (lm.VS[0] + 3.9, lm.VS[1] + 2.0))

    d += elm.Line().at(lm.VS).left().length(1.8)
    d += (nvs := elm.Dot())
    d += elm.Capacitor().at(nvs.center).up().length(2.0)
    d += elm.Ground().flip()
    ref(d, (nvs.center[0] + 0.35, nvs.center[1] + 1.1), 'C8\n100 nF')
    d += elm.Line().at(nvs.center).left().length(1.6)
    d += elm.Vdd().label('+5 V', ofst=0.15)

    d += elm.Line().at(lm.VOUT).left().length(0.6)
    d += elm.Resistor().left().length(2.6).label('R11  75 Ω', loc='top', ofst=0.25)
    d += (nt := elm.Dot())
    d += elm.Capacitor().at(nt.center).down().length(2.4)
    d += elm.Ground()
    ref(d, (nt.center[0] + 0.35, nt.center[1] - 1.2), 'C9\n1 µF')
    d += elm.Line().at(nt.center).left().length(1.2)
    tag(d, 'left', 'TEMP_S')

    d += elm.Line().at(lm.inL1).left().length(0.8)
    d += elm.Ground()
    txt(d, (-6.0, -4.6), T('Filtro R11 + C9 do datasheet: o LM35\noscila com capacitor direto na saída.',
                           'R11 + C9 filter per datasheet: the LM35\noscillates with a capacitor right at VOUT.'))
    return d


# ---------------------------------------------------------------------
# [5] MEDICAO ANALOGICA
# ---------------------------------------------------------------------
def bloco_medicao():
    d = novo()
    d += elm.Vdd().at((0, 0)).label('+12 V PROT', ofst=0.15)
    d += elm.Resistor().at((0, 0)).down().length(3.0)
    ref(d, (0.45, -1.5), 'R2\n100 kΩ')
    d += (nd := elm.Dot())
    d += elm.Resistor().down().length(3.0)
    ref(d, (0.45, -4.5), 'R3\n27 kΩ')
    d += elm.Ground()
    d += elm.Line().at(nd.center).right().length(2.8)
    d += elm.Capacitor().down().length(3.0)
    ref(d, (3.15, -4.5), 'C5\n100 nF')
    d += elm.Ground()
    d += elm.Line().at(nd.center).left().length(1.6)
    tag(d, 'left', 'V_SENSE')
    txt(d, (-4.9, -8.6), T('12,6 V → 2,68 V no ADC1.\nO ADC2 conflita com o Wi-Fi.',
                           '12.6 V → 2.68 V on ADC1.\nADC2 conflicts with Wi-Fi.'))

    X = 9.0
    tag(d, 'left', 'PWR_OK', at=(X, -0.9))
    d.here = (X, -0.9)
    d += elm.Line().right().length(0.6)
    d += elm.Resistor().right().length(2.8).label('R4  10 kΩ', loc='top', ofst=0.3)
    d += (npk := elm.Dot())
    d += elm.Resistor().down().length(3.0)
    ref(d, (npk.center[0] + 0.45, npk.center[1] - 1.5), 'R5\n20 kΩ')
    d += elm.Ground()
    d += elm.Line().at(npk.center).right().length(1.4)
    tag(d, 'right', 'PWR_OK_S')
    txt(d, (X - 3.3, -6.6), T('PWR_OK do ATX: 5 V → 3,3 V.\nSem ATX fica em 0 V (= bateria).',
                              'ATX PWR_OK: 5 V → 3.3 V.\nNo ATX reads 0 V (= battery).'))
    return d


# ---------------------------------------------------------------------
# [6] MALHA DE POTENCIA - LAMPADAS
# ---------------------------------------------------------------------
def bloco_potencia():
    d = novo()
    XL, XR, YT = 10.4, 16.0, 0.0
    d += elm.Vdd().at((0, YT)).label('+12 V PROT', ofst=0.15)
    d += elm.Line().at((0, YT)).right().length(1.8)
    d += elm.Switch(nc=True).right().length(3.4).label(T('TH1  KSD9700\n70 °C · NF', 'TH1  KSD9700\n70 °C · NC'),
                                                loc='top', ofst=0.35)
    d += elm.Line().right().to((XL, YT))
    d += elm.Dot()

    for i, y in enumerate([YT, YT - 2.8, YT - 5.6]):
        d += elm.Lamp().at((XL, y)).right().to((XR, y)).label(f'EL{i + 1}', loc='top', ofst=0.3)
    d += elm.Line().at((XL, YT)).down().to((XL, YT - 5.6))
    d += elm.Dot().at((XL, YT - 2.8))
    d += elm.Line().at((XR, YT)).down().to((XR, YT - 5.6))
    d += elm.Dot().at((XR, YT))
    d += elm.Dot().at((XR, YT - 2.8))
    txt(d, (XR + 0.8, YT - 1.4), T('3 × W5W  12 V / 5 W\n15 W · 1,25 A total\ncarga RESISTIVA: sem\ndiodo de roda livre',
                                   '3 × W5W  12 V / 5 W\n15 W · 1.25 A total\nRESISTIVE load: no\nflyback diode needed'))

    d += (q1 := elm.NFet(bulk=False).right().reverse().at((XR, YT - 8.2)).anchor('drain'))
    ref(d, (XR + 1.1, YT - 8.9), T('Q1  IRLZ44N\nlogic-level\nRDS(on) 28 mΩ\n@ VGS 4,5 V',
                                   'Q1  IRLZ44N\nlogic-level\nRDS(on) 28 mΩ\n@ VGS 4.5 V'))
    d += elm.Line().at((XR, YT - 5.6)).to(q1.drain)
    d += elm.Line().at(q1.source).down().length(1.0)
    d += elm.Ground()

    gx, gy = q1.gate
    d += elm.Line().at(q1.gate).left().to((gx - 1.2, gy))
    d += (ng := elm.Dot())
    d += elm.Resistor().left().length(2.8).label('R6  150 Ω', loc='top', ofst=0.3)
    d += elm.Line().left().length(0.6)
    tag(d, 'left', 'PWM_GATE')
    d += elm.Resistor().at(ng.center).down().length(2.8)
    ref(d, (ng.center[0] - 0.45, ng.center[1] - 1.4), 'R7\n10 kΩ', halign='right')
    d += elm.Ground()
    return d


# ---------------------------------------------------------------------
# [7] COOLER DE EXAUSTAO - carga INDUTIVA
# ---------------------------------------------------------------------
def bloco_cooler():
    d = novo()
    XF, YF = 0.0, 0.0
    d += elm.Vdd().at((XF, YF + 1.0)).label('+12 V PROT', ofst=0.15)
    d += elm.Line().at((XF, YF + 1.0)).down().length(1.0)
    d += (ft := elm.Dot())
    d += elm.Motor().at((XF, YF)).down().length(3.4)
    d += (fb := elm.Dot())
    ref(d, (XF - 0.8, YF - 1.7), T('M1\ncooler 12 V\n40 mm · 0,1 A', 'M1\n12 V fan\n40 mm · 0.1 A'), halign='right')
    rev(d, (XF - 1.5, YF + 0.2))

    d += elm.Line().at(ft.center).right().length(2.8)
    d += elm.Schottky().at((XF + 2.8, YF - 3.4)).up().length(3.4)
    d += elm.Line().at(fb.center).right().length(2.8)
    ref(d, (XF + 3.25, YF - 1.7), T('D3  SS14\nroda livre\n(nota 1)', 'D3  SS14\nflyback\n(note 1)'))

    d += elm.Line().at((XF + 2.8, YF)).right().length(3.6)
    d += elm.Capacitor().at((XF + 6.4, YF)).down().length(3.4)
    d += elm.Line().at((XF + 2.8, YF - 3.4)).right().length(3.6)
    ref(d, (XF + 6.85, YF - 1.7), 'C6\n100 nF')

    d += (q2 := elm.NFet(bulk=False).right().reverse().at((XF, YF - 5.0)).anchor('drain'))
    d += elm.Line().at(fb.center).to(q2.drain)
    ref(d, (XF + 1.1, YF - 5.7), T('Q2  IRLZ44N\n(alt. AO3400)', 'Q2  IRLZ44N\n(alt. AO3400)'))
    d += elm.Line().at(q2.source).down().length(1.0)
    d += elm.Ground()

    gx2, gy2 = q2.gate
    d += elm.Line().at(q2.gate).left().to((gx2 - 1.2, gy2))
    d += (ng2 := elm.Dot())
    d += elm.Resistor().left().length(2.8).label('R9  100 Ω', loc='top', ofst=0.3)
    d += elm.Line().left().length(0.6)
    tag(d, 'left', 'FAN_GATE')
    d += elm.Resistor().at(ng2.center).down().length(2.8)
    ref(d, (ng2.center[0] - 0.45, ng2.center[1] - 1.4), 'R10\n10 kΩ', halign='right')
    d += elm.Ground()

    txt(d, (XF + 6.6, YF - 4.3), T('Motor = carga INDUTIVA.\nAlimentado ANTES do TH1:\nem sobretemperatura o\ncooler continua (nota 2).',
                                   'Motor = INDUCTIVE load.\nFed BEFORE TH1: on\nover-temperature the\nfan keeps running (note 2).'))
    txt(d, (XF + 6.6, YF - 8.6), T('PWM 25 kHz, LEDC canal 2.\nRotação mínima 30 %.',
                                   'PWM 25 kHz, LEDC channel 2.\nMinimum speed 30 %.'))
    return d


# ---------------------------------------------------------------------
# [8] DISPLAY
# ---------------------------------------------------------------------
def bloco_display():
    d = novo()
    tm = elm.Ic(pins=[elm.IcPin(name='GND', side='left', slot='1/4'),
                      elm.IcPin(name='DIO', side='left', slot='2/4'),
                      elm.IcPin(name='CLK', side='left', slot='3/4'),
                      elm.IcPin(name='VCC', side='left', slot='4/4')],
                size=(3.8, 4.6), plblofst=0.25)
    d += (tm := tm.at((0, 0)).right().label(T('DS1  TM1637\n4 dígitos', 'DS1  TM1637\n4 digits'),
                                            loc='top', ofst=0.35))
    rev(d, (tm.VCC[0] + 4.1, tm.VCC[1] + 2.0))

    d += elm.Line().at(tm.VCC).left().length(1.8)
    d += (nvc := elm.Dot())
    d += elm.Capacitor().at(nvc.center).up().length(1.8)
    d += elm.Ground().flip()
    ref(d, (nvc.center[0] + 0.35, nvc.center[1] + 1.0), 'C10\n100 nF')
    d += elm.Line().at(nvc.center).left().length(1.4)
    d += elm.Vdd().label('+3V3', ofst=0.15)
    d += elm.Line().at(tm.CLK).left().length(3.2)
    tag(d, 'left', 'DISP_CLK')
    d += elm.Line().at(tm.DIO).left().length(3.2)
    tag(d, 'left', 'DISP_DIO')
    d += elm.Line().at(tm.inL1).left().length(0.8)
    d += elm.Ground()
    txt(d, (tm.inL1[0] - 6.4, tm.inL1[1] - 2.1), T('VCC em 3,3 V: o ESP32 não tolera\n5 V no DIO (nota 6).',
                                                   'VCC at 3.3 V: the ESP32 does not\ntolerate 5 V on DIO (note 6).'))
    return d


def blocos():
    return {
        '1': (T('ENTRADA · SELEÇÃO DE FONTE · PROTEÇÃO', 'INPUT · SOURCE SELECTION · PROTECTION'), bloco_entrada),
        '2': (T('REGULAÇÃO 12 V → 5 V', '12 V → 5 V REGULATION'), bloco_regulacao),
        '3': (T('CONTROLADOR', 'CONTROLLER'), bloco_controlador),
        '4': (T('SENSOR DE TEMPERATURA', 'TEMPERATURE SENSOR'), bloco_sensor),
        '5': (T('MEDIÇÃO ANALÓGICA', 'ANALOG SENSING'), bloco_medicao),
        '6': (T('POTÊNCIA · LÂMPADAS (LOW-SIDE)', 'POWER STAGE · LAMPS (LOW-SIDE)'), bloco_potencia),
        '7': (T('COOLER DE EXAUSTÃO (LOW-SIDE)', 'EXHAUST FAN (LOW-SIDE)'), bloco_cooler),
        '8': (T('DISPLAY DE TEMPERATURA', 'TEMPERATURE DISPLAY'), bloco_display),
    }


def gerar(pasta, lang='pt'):
    """Salva cada bloco em <pasta>/bloco_N.svg. Devolve {N: (titulo, larg_mm, alt_mm)}."""
    global LANG
    LANG = lang
    os.makedirs(pasta, exist_ok=True)
    info = {}
    for k, (titulo, fn) in blocos().items():
        d = fn()
        bb = d.get_bbox()
        d.save(os.path.join(pasta, f'bloco_{k}.svg'))
        info[k] = (titulo, (bb.xmax - bb.xmin) * ESCALA_MM, (bb.ymax - bb.ymin) * ESCALA_MM)
    return info


if __name__ == '__main__':
    for k, (t, w, h) in gerar('build').items():
        print(f'[{k}] {w:6.1f} x {h:5.1f} mm  {t}')
