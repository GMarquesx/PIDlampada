import schemdraw
import schemdraw.elements as elm

schemdraw.config(font='DejaVu Sans', fontsize=9.5, lw=1.5, unit=2.5)
d = schemdraw.Drawing(show=False)

GY = '#7a8a99'
AM = '#b57a00'


def title(txt, xy, size=11):
    d.add(elm.Label().at(xy).label(txt, fontsize=size, color='#16212e', halign='left'))


# =====================================================================
# BLOCO 1 - ENTRADA, SELECAO DE FONTE E PROTECAO
# =====================================================================
title('[1]  ENTRADA · SELEÇÃO DE FONTE · PROTEÇÃO', (0, 26.8))

d += elm.Tag().at((2.0, 23.4)).left().label('ATX +12 V')
d += (bat := elm.Battery().at((1.2, 18.4)).up().length(2.4)
      .label('BT1  3S 18650\n12,6 V máx.', loc='left', ofst=0.35))
d += elm.Line().at(bat.end).up().length(1.2)
d += elm.Line().right().length(0.8)

d += (sw := elm.SwitchSpdt(flip=True).at((4.2, 21.4)).right()
      .label('SW1', loc='top', ofst=0.5))
d += elm.Line().at(sw.a).to((2.6, 23.4))
d += elm.Line().at(sw.b).to((2.6, 22.0))
d += elm.Line().at((2.6, 22.0)).to((2.0, 22.0))

d.here = sw.c
d += elm.Line().right().length(0.7)
d += elm.Fuse().right().length(2.4).label('F1\n3 A retard.', loc='top', ofst=0.3)
d += elm.Schottky().right().length(2.4).label('D1  SS34', loc='top', ofst=0.3)
d += elm.Line().right().length(1.0)
d += (na := elm.Dot())

d += elm.Zener().at(na.center).down().length(3.0).label('D2\nSMBJ15A', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Line().down().length(0.8)
d += (g1 := elm.Dot())

d += elm.Line().at(na.center).right().length(2.4)
d += (nb := elm.Dot())
d += elm.Capacitor(polar=True).down().length(3.0).label('C1\n1000 µF\n25 V', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Line().down().length(0.8)
d += (g2 := elm.Dot())

d += elm.Line().at(nb.center).right().length(2.4)
d += (nc := elm.Dot())
d += elm.Capacitor().down().length(3.0).label('C2\n100 nF', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Line().down().length(0.8)
d += (g3 := elm.Dot())

d += elm.Line().at(g1.center).to(g3.center)
d += elm.Ground().at(g2.center)

d += elm.Line().at(nc.center).right().length(1.6)
d += elm.Vdd().label('+12 V PROT', ofst=0.15)

# =====================================================================
# BLOCO 2 - CONVERSOR BUCK
# =====================================================================
title('[2]  REGULAÇÃO', (0, 14.6))

u1 = elm.Ic(pins=[elm.IcPin(name='GND', side='left', slot='1/2'),
                  elm.IcPin(name='VIN', side='left', slot='2/2'),
                  elm.IcPin(name='GND', side='right', slot='1/2'),
                  elm.IcPin(name='VOUT', side='right', slot='2/2')],
            size=(5.0, 3.6), plblofst=0.25)
d += (u1 := u1.at((5.0, 10.4)).right().label('U1   MP1584 / LM2596\nbuck 12 → 5 V', loc='top', ofst=0.35, fontsize=9.5))

d += elm.Line().at(u1.VIN).left().length(1.3)
d += elm.Vdd().label('+12 V PROT', ofst=0.15)
d += elm.Line().at(u1.inL1).left().length(0.9)
d += elm.Ground()
d += elm.Line().at(u1.inR1).right().length(0.9)
d += elm.Ground()

d += elm.Line().at(u1.VOUT).right().length(1.4)
d += (n5 := elm.Dot())
d += elm.Capacitor(polar=True).down().length(2.6).label('C3\n100 µF', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Ground()
d += elm.Line().at(n5.center).right().length(2.2)
d += (n5b := elm.Dot())
d += elm.Capacitor().down().length(2.6).label('C4\n10 µF', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Ground()
d += elm.Line().at(n5b.center).right().length(1.4)
d += elm.Vdd().label('+5 V', ofst=0.15)

# =====================================================================
# BLOCO 6 - MALHA DE POTENCIA
# =====================================================================
title('[6]  MALHA DE POTÊNCIA  (chaveamento low-side)', (0, 4.2))

XL, XR, YT = 12.0, 18.5, 0.6

d += elm.Vdd().at((1.4, YT)).label('+12 V PROT', ofst=0.15)
d.here = (1.4, YT)
d += elm.Line().right().length(0.7)
d += elm.Switch().right().length(3.2).label('TH1  KSD9700\n70 °C · NC', loc='top', ofst=0.35)
d += elm.Line().right().to((XL, YT))
d += elm.Dot()

d += elm.Lamp().at((XL, YT)).right().to((XR, YT)).label('EL1', loc='top', ofst=0.3)
d += elm.Dot().at((XR, YT))
d += elm.Line().at((XL, YT)).down().to((XL, YT - 2.8))
d += elm.Dot()
d += elm.Lamp().at((XL, YT - 2.8)).right().to((XR, YT - 2.8)).label('EL2', loc='top', ofst=0.3)
d += elm.Dot().at((XR, YT - 2.8))
d += elm.Line().at((XL, YT - 2.8)).down().to((XL, YT - 5.6))
d += elm.Lamp().at((XL, YT - 5.6)).right().to((XR, YT - 5.6)).label('EL3', loc='top', ofst=0.3)
d += elm.Line().at((XR, YT)).down().to((XR, YT - 5.6))

d += elm.Label().at((XR + 0.8, YT - 1.4)).label(
    '3 × W5W  12 V / 5 W\n15 W · 1,3 A · carga resistiva\n(sem diodo de roda livre)',
    fontsize=8.5, color=AM, halign='left')

# --- MOSFET de chaveamento (posicionado por coordenada, fiacao explicita) ---
d += (q1 := elm.NFet(bulk=False).right().reverse().at((XR, YT - 8.4)).anchor('drain'))
d += elm.Label().at((XR + 1.1, YT - 9.0)).label(
    'Q1  IRLZ44N\nlogic-level\nRDS(on) 28 mΩ @ VGS 4,5 V', fontsize=8.5, halign='left')
d += elm.Line().at((XR, YT - 5.6)).to(q1.drain)
d += elm.Line().at(q1.source).down().length(1.2)
d += elm.Ground()

gx, gy = q1.gate
d += elm.Line().at(q1.gate).left().to((gx - 1.2, gy))
d += (ng := elm.Dot())
d += elm.Resistor().left().length(2.8).label('R6  150 Ω', loc='top', ofst=0.3)
d += elm.Line().left().length(1.1)
d += elm.Tag().left().label('PWM_GATE')
d += elm.Resistor().at(ng.center).down().length(2.8)
d += elm.Label().at((ng.center[0] - 0.45, ng.center[1] - 1.4)).label('R7\n10 kΩ', fontsize=9.5, halign='right')
d += elm.Ground()

# =====================================================================
# BLOCO 3 - ESP32
# =====================================================================
title('[3]  CONTROLADOR', (26.4, 27.4))

esp = elm.Ic(pins=[elm.IcPin(name='GPIO16', side='right', slot='1/5'),
                   elm.IcPin(name='GPIO35', side='right', slot='2/5'),
                   elm.IcPin(name='GPIO34', side='right', slot='3/5'),
                   elm.IcPin(name='GPIO4', side='right', slot='4/5'),
                   elm.IcPin(name='GPIO25', side='right', slot='5/5'),
                   elm.IcPin(name='GND', side='left', slot='1/4'),
                   elm.IcPin(name='GND', side='left', slot='2/4'),
                   elm.IcPin(name='3V3', side='left', slot='3/4'),
                   elm.IcPin(name='VIN', side='left', slot='4/4')],
            size=(6.8, 12.0), plblofst=0.3)
d += (esp := esp.at((30.5, 20.0)).right().label('U2   ESP32 DevKit v1', loc='top', ofst=0.4, fontsize=10))

d += elm.Line().at(esp.VIN).left().length(1.5)
d += elm.Vdd().label('+5 V', ofst=0.15)
d += elm.Line().at(getattr(esp, '3V3')).left().length(1.5)
d += elm.Vdd().label('+3V3', ofst=0.15)
d += elm.Line().at(esp.inL1).left().length(1.1)
d += elm.Ground()
d += elm.Line().at(esp.inL2).left().length(1.1)
d += elm.Ground()

for pin, net in [(esp.GPIO25, 'PWM_GATE'), (esp.GPIO4, '1WIRE_DQ'),
                 (esp.GPIO34, 'V_SENSE'), (esp.GPIO35, 'PWR_OK_S'),
                 (esp.GPIO16, 'LED_ST')]:
    d += elm.Line().at(pin).right().length(2.0)
    d += elm.Tag().right().label(net)

# =====================================================================
# BLOCO 4 - SENSOR
# =====================================================================
title('[4]  SENSOR 1-WIRE', (38.4, 13.4))

ds = elm.Ic(pins=[elm.IcPin(name='GND', side='left', slot='1/3'),
                  elm.IcPin(name='DQ', side='left', slot='2/3'),
                  elm.IcPin(name='VDD', side='left', slot='3/3')],
            size=(4.4, 4.0), plblofst=0.25)
d += (ds := ds.at((44.5, 9.5)).right().label('TS1  DS18B20\nsonda estanque', loc='top', ofst=0.35, fontsize=9.5))

d += elm.Line().at(ds.VDD).left().length(3.0)
d += elm.Vdd().label('+3V3', ofst=0.15)
d += elm.Line().at(ds.inL1).left().length(3.0)
d += elm.Ground()

d += elm.Line().at(ds.DQ).left().length(1.8)
d += (nq := elm.Dot())
d += elm.Resistor().at(nq.center).up().length(3.2).label('R1  4,7 kΩ', loc='left', ofst=0.3)
d += elm.Vdd().label('+3V3', ofst=0.15)
d += elm.Line().at(nq.center).left().length(1.9)
d += elm.Tag().left().label('1WIRE_DQ')

# =====================================================================
# BLOCO 5 - MEDICAO ANALOGICA / STATUS
# =====================================================================
title('[5]  MEDIÇÃO ANALÓGICA · STATUS', (29.8, 5.2))

d += elm.Vdd().at((36.2, 2.6)).label('+12 V PROT', ofst=0.15)
d += elm.Resistor().at((36.2, 2.6)).down().length(2.8)
d += elm.Label().at((36.65, 1.3)).label('R2\n100 kΩ', fontsize=9.5, halign='left')
d += (nd := elm.Dot())
d += elm.Resistor().down().length(2.8)
d += elm.Label().at((36.65, -1.5)).label('R3\n27 kΩ', fontsize=9.5, halign='left')
d += elm.Ground()
d += elm.Line().at(nd.center).right().length(2.2)
d += elm.Capacitor().down().length(2.6).label('C5\n100 nF', loc='bottom', ofst=(0.15, 0.15), halign='left')
d += elm.Ground()
d += elm.Line().at(nd.center).left().length(2.1)
d += elm.Tag().left().label('V_SENSE')
d += elm.Label().at((31.4, -4.4)).label('12,6 V → 2,68 V  ·  usar ADC1\n(ADC2 conflita com Wi-Fi ativo)',
                                       fontsize=8.5, color=GY, halign='left')

d += elm.Tag().at((31.0, -7.6)).left().label('PWR_OK (ATX)')
d.here = (31.0, -7.6)
d += elm.Line().right().length(2.2)
d += elm.Resistor().right().length(2.8).label('R4  10 kΩ', loc='top', ofst=0.3)
d += (npk := elm.Dot())
d += elm.Resistor().down().length(2.8)
d += elm.Label().at((npk.center[0] + 0.45, npk.center[1] - 1.5)).label('R5\n20 kΩ', fontsize=9.5, halign='left')
d += elm.Ground()
d += elm.Line().at(npk.center).up().length(2.9)
d += elm.Tag().right().label('PWR_OK_S')

d += elm.Tag().at((31.0, -12.6)).left().label('LED_ST')
d.here = (31.0, -12.6)
d += elm.Line().right().length(1.1)
d += elm.Resistor().right().length(2.8).label('R8  220 Ω', loc='top', ofst=0.3)
d += elm.LED().down().length(2.8).label('LED1', loc='bottom', ofst=(0.2, 0.15), halign='left')
d += elm.Ground()

d.save('/home/claude/esq_raw.svg')
print('ok')
