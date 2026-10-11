"""
Esquema eletrico Rev. B - PIDlampada - folha de desenho A3 (2 folhas).

Monta o desenho no formato de prancha de engenharia:
  folha 1: esquema completo, tabela de revisoes (canto superior direito),
           carimbo com elaborado/aprovado (canto inferior direito),
           moldura com zonas 1-8 / A-F
  folha 2: pinagem do U2, notas de projeto e lista de materiais

Gera as versoes em portugues e em ingles.

Uso:
    pip install schemdraw playwright
    python -m playwright install chromium
    python docs/hardware/esquema_rev_b.py

Saida (em docs/hardware/):
    Esquema_Eletrico_Rev_B.pdf          portugues
    Electrical_Schematic_Rev_B_EN.pdf   ingles
    build/                              HTML e SVG intermediarios
Sem o playwright, abra build/folha_pt.html no navegador e imprima em PDF
(A3 paisagem, margens "nenhuma").
"""
import html
import os
import re

import esquema_blocos as B

AQUI = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(AQUI, 'build')

# ------------------------------------------------------------------ dados
DES = 'PIDL-ESQ-001'
REV = 'B'
AUTOR = 'Gabriel Marques'
SIGLA = 'GM'
DATA_A = '10/10/2026'
DATA_B = '11/10/2026'

TXT = {
    'pt': dict(
        arquivo='Esquema_Eletrico_Rev_B.pdf',
        titulo='CÂMARA TÉRMICA COMPACTA COM CONTROLE PWM',
        subtitulo='ESQUEMA ELÉTRICO',
        sub2='PINAGEM · NOTAS DE PROJETO · LISTA DE MATERIAIS',
        inst='UNIP · ENGENHARIA DE COMPUTAÇÃO · PROJETO INTEGRADOR 2026',
        local='SÃO JOSÉ DOS CAMPOS - SP',
        revisoes='REVISÕES', rev='REV.', desc='DESCRIÇÃO', data='DATA', resp='RESP.',
        rev_a='Release inicial.',
        rev_b='Inclusão do cooler de exaustão M1 com Q2, R9, R10, diodo de roda livre D3 e C6. '
              'Display TM1637 (DS1) com C10. DS18B20 substituído pelo LM35DZ (TS1) com C8 e filtro '
              'R11/C9. Entrada ATX designada J1. Removidos R1, R8 e LED1.',
        func='', nome='NOME', sigla='SIGLA', elab='ELABORADO', aprov='APROVADO',
        n_des='Nº DO DESENHO', folha='FOLHA', escala='ESCALA', formato='FORMATO',
        sem_escala='S/ ESC.', projeto='PROJETO',
        notas_gerais='NOTAS GERAIS',
        ng=[
            'Pinagem do U2, notas de projeto e lista de materiais: ver folha 2.',
            'Triângulo com "B": componente ou ligação incluída ou alterada na revisão B.',
            'Etiquetas de rede com o mesmo nome estão interligadas.',
            'Todos os símbolos de terra são o mesmo nó: GND do pack, do ATX, do U1 e do U2.',
            'Resistores 1/4 W 5 %. Capacitores cerâmicos X7R 50 V. Salvo indicação.',
            'Malha de potência (+12 V PROT, EL1-EL3, Q1): condutores para no mínimo 2 A.',
        ],
        alim_t='REDES DE ALIMENTAÇÃO', alim_h=('REDE', 'ORIGEM', 'CARGAS', 'CORRENTE'),
        alim=[('+12 V PROT', 'J1 ou BT1, via SW1, F1, D1', 'EL1-EL3, M1, U1, R2/R3', '≈ 1,5 A'),
              ('+5 V', 'U1 (buck)', 'U2 (VIN), TS1', '≈ 0,3 A pico (Wi-Fi)'),
              ('+3V3', 'regulador da placa U2', 'DS1', '≤ 30 mA')],
        legenda='LEGENDA',
        leg=['alteração da revisão B', 'etiqueta de rede (liga pelo nome)', 'terra comum', 'junção'],
        pin_t='PINAGEM · U2 ESP32 DEVKIT V1', pino='PINO', rede='REDE', tipo='TIPO', funcao='FUNÇÃO',
        notas_t='NOTAS DE PROJETO',
        bom_t='LISTA DE MATERIAIS', item='ITEM', ref='REF.', qtd='QTD.', descr='DESCRIÇÃO', espec='ESPECIFICAÇÃO',
        removidos='Removidos na revisão B: R1 (pull-up 1-Wire), R8 e LED1 (LED de status externo) e o sensor DS18B20.',
        zonas='', idioma='PT',
    ),
    'en': dict(
        arquivo='Electrical_Schematic_Rev_B_EN.pdf',
        titulo='COMPACT THERMAL CHAMBER WITH PWM CONTROL',
        subtitulo='ELECTRICAL SCHEMATIC',
        sub2='PINOUT · DESIGN NOTES · BILL OF MATERIALS',
        inst='UNIP · COMPUTER ENGINEERING · CAPSTONE PROJECT 2026',
        local='SÃO JOSÉ DOS CAMPOS - SP · BRAZIL',
        revisoes='REVISIONS', rev='REV.', desc='DESCRIPTION', data='DATE', resp='BY',
        rev_a='Initial release.',
        rev_b='Added exhaust fan M1 with Q2, R9, R10, flyback diode D3 and C6. TM1637 display (DS1) '
              'with C10. DS18B20 replaced by LM35DZ (TS1) with C8 and R11/C9 filter. ATX input '
              'designated J1. Removed R1, R8 and LED1.',
        func='', nome='NAME', sigla='INIT.', elab='DRAWN', aprov='APPROVED',
        n_des='DRAWING No.', folha='SHEET', escala='SCALE', formato='SIZE',
        sem_escala='NTS', projeto='PROJECT',
        notas_gerais='GENERAL NOTES',
        ng=[
            'U2 pinout, design notes and bill of materials: see sheet 2.',
            'Triangle with "B": part or connection added or changed in revision B.',
            'Net labels with the same name are connected.',
            'All ground symbols are the same node: pack, ATX, U1 and U2 GND.',
            'Resistors 1/4 W 5 %. Ceramic capacitors X7R 50 V. Unless noted.',
            'Power loop (+12 V PROT, EL1-EL3, Q1): conductors rated 2 A minimum.',
        ],
        alim_t='POWER NETS', alim_h=('NET', 'SOURCE', 'LOADS', 'CURRENT'),
        alim=[('+12 V PROT', 'J1 or BT1, via SW1, F1, D1', 'EL1-EL3, M1, U1, R2/R3', '≈ 1.5 A'),
              ('+5 V', 'U1 (buck)', 'U2 (VIN), TS1', '≈ 0.3 A peak (Wi-Fi)'),
              ('+3V3', 'U2 on-board regulator', 'DS1', '≤ 30 mA')],
        legenda='LEGEND',
        leg=['revision B change', 'net label (connects by name)', 'common ground', 'junction'],
        pin_t='PINOUT · U2 ESP32 DEVKIT V1', pino='PIN', rede='NET', tipo='TYPE', funcao='FUNCTION',
        notas_t='DESIGN NOTES',
        bom_t='BILL OF MATERIALS', item='ITEM', ref='REF.', qtd='QTY', descr='DESCRIPTION', espec='RATING',
        removidos='Removed in revision B: R1 (1-Wire pull-up), R8 and LED1 (external status LED) and the DS18B20 sensor.',
        zonas='', idioma='EN',
    ),
}

# (pino, rede, tipo pt, tipo en, funcao pt, funcao en, rev)
PINOS = [
    ('GPIO25', 'PWM_GATE', 'saída', 'output', 'Gate do Q1 (lâmpadas) · LEDC canal 0, 500 Hz, 10 bits',
     'Q1 gate (lamps) · LEDC channel 0, 500 Hz, 10 bit', 'A'),
    ('GPIO26', 'FAN_GATE', 'saída', 'output', 'Gate do Q2 (cooler) · LEDC canal 2, 25 kHz, 8 bits',
     'Q2 gate (fan) · LEDC channel 2, 25 kHz, 8 bit', 'B'),
    ('GPIO32', 'TEMP_S', 'analógica', 'analog', 'ADC1_CH4 ← LM35 via filtro R11/C9',
     'ADC1_CH4 ← LM35 through R11/C9 filter', 'B'),
    ('GPIO34', 'V_SENSE', 'analógica', 'analog', 'ADC1_CH6 ← divisor R2/R3 (tensão do barramento)',
     'ADC1_CH6 ← R2/R3 divider (bus voltage)', 'A'),
    ('GPIO35', 'PWR_OK_S', 'analógica', 'analog', 'ADC1_CH7 ← divisor R4/R5 (PWR_OK do ATX)',
     'ADC1_CH7 ← R4/R5 divider (ATX PWR_OK)', 'A'),
    ('GPIO18', 'DISP_CLK', 'saída', 'output', 'Clock do TM1637 (DS1)', 'TM1637 clock (DS1)', 'B'),
    ('GPIO19', 'DISP_DIO', 'bidirecional', 'bidir.', 'Dados do TM1637, dreno aberto com pull-up no módulo',
     'TM1637 data, open drain, pull-up on module', 'B'),
    ('GPIO2', '—', 'saída', 'output', 'LED de status da própria placa', 'On-board status LED', 'B'),
    ('GPIO33', 'SETPOINT', 'analógica', 'analog', 'Reservado: potenciômetro de setpoint (só na simulação)',
     'Reserved: setpoint potentiometer (simulation only)', 'A'),
    ('GPIO27', 'BTN_MODE', 'entrada', 'input', 'Reservado: botão de modo', 'Reserved: mode button', 'A'),
    ('VIN', '+5 V', 'alimentação', 'supply', 'Entrada de 5 V vinda do U1', '5 V input from U1', 'A'),
    ('3V3', '+3V3', 'alimentação', 'supply', 'Saída do regulador da placa → DS1', 'On-board regulator output → DS1', 'A'),
    ('GND', 'GND', 'terra', 'ground', 'Terra comum', 'Common ground', 'A'),
]

NOTAS = {
    'pt': [
        ('Por que só agora existe diodo de roda livre.',
         'Lâmpada halógena é carga resistiva e dispensa diodo. O motor do cooler é indutivo: ao abrir Q2, '
         'a corrente do enrolamento precisa de caminho e, sem D3, vira um pico de tensão que pode passar '
         'dos 55 V do MOSFET. D3 é Schottky porque o PWM é de 25 kHz.'),
        ('O cooler não passa pelo TH1.',
         'Na sobretemperatura o KSD9700 corta as lâmpadas e o firmware põe o cooler a 100 % para tirar o calor. '
         'Se o TH1 cortasse os dois, a câmara esfriaria só por convecção.'),
        ('Faixa dividida (split-range).',
         'Um único PI com saída de −1 a 1: positivo aciona as lâmpadas, negativo aciona o cooler, nunca os dois '
         'juntos. O cooler tem rotação mínima de 30 % e histerese de liga/desliga.'),
        ('Canais LEDC.',
         'No ESP32 os canais andam em pares que dividem o mesmo timer (0-1, 2-3...). O cooler fica no canal 2 '
         'para os 25 kHz dele não mudarem a frequência das lâmpadas no canal 0.'),
        ('LM35 em 5 V.',
         'O LM35 pede de 4 a 30 V. A saída, de 0,25 a 0,60 V na faixa útil, entra no ADC sem divisor. '
         'R11 e C9 seguem o circuito do datasheet.'),
        ('TM1637 em 3,3 V.',
         'Os pull-ups do módulo vão no VCC. Com o módulo em 5 V o pino DIO do ESP32 receberia acima do limite.'),
        ('Mantidas da revisão A.',
         'SS34 contra inversão de polaridade, TVS SMBJ15A contra transitório de hot-plug, fusível retardado '
         'para o inrush, R7 e R10 segurando os gates em 0 V durante o boot.'),
        ('Compensação de tensão.',
         'Com bateria a tensão cai de 12,6 para ~9 V. O firmware corrige o duty das lâmpadas por (12/V)² e o '
         'do cooler por 12/V, medindo V pelo V_SENSE.'),
    ],
    'en': [
        ('Why a flyback diode only now.',
         'A halogen lamp is a resistive load and needs no diode. The fan motor is inductive: when Q2 turns off '
         'the winding current needs a path and, without D3, becomes a voltage spike that can exceed the 55 V '
         'MOSFET rating. D3 is a Schottky because the PWM runs at 25 kHz.'),
        ('The fan does not go through TH1.',
         'On over-temperature the KSD9700 cuts the lamps and the firmware drives the fan at 100 % to remove '
         'heat. If TH1 cut both, the chamber would only cool by convection.'),
        ('Split-range control.',
         'A single PI with output from −1 to 1: positive drives the lamps, negative drives the fan, never both. '
         'The fan has a 30 % minimum speed and on/off hysteresis.'),
        ('LEDC channels.',
         'On the ESP32 channels come in pairs sharing one timer (0-1, 2-3...). The fan uses channel 2 so its '
         '25 kHz does not change the lamp frequency on channel 0.'),
        ('LM35 at 5 V.',
         'The LM35 needs 4 to 30 V. Its output, 0.25 to 0.60 V over the useful range, goes to the ADC with no '
         'divider. R11 and C9 follow the datasheet circuit.'),
        ('TM1637 at 3.3 V.',
         'The module pull-ups go to VCC. With the module at 5 V the ESP32 DIO pin would see more than its limit.'),
        ('Kept from revision A.',
         'SS34 against reverse polarity, SMBJ15A TVS against hot-plug transients, slow-blow fuse for inrush, '
         'R7 and R10 holding the gates at 0 V during boot.'),
        ('Voltage compensation.',
         'On battery the bus drops from 12.6 to ~9 V. The firmware scales the lamp duty by (12/V)² and the fan '
         'duty by 12/V, reading V on V_SENSE.'),
    ],
}

# (ref, qtd, desc pt, desc en, espec pt, espec en, rev)
BOM = [
    ('BT1', 1, 'Pack de baterias 3S 18650 com BMS', '3S 18650 battery pack with BMS', '11,1 V nom. · 12,6 V máx.', '11.1 V nom. · 12.6 V max.', 'A'),
    ('J1', 1, 'Conector de entrada ATX (Molex 4 vias)', 'ATX input connector (4-pin Molex)', '+12 V / GND', '+12 V / GND', 'B'),
    ('SW1', 1, 'Chave seletora SPDT', 'SPDT selector switch', '3 A · ATX / bateria', '3 A · ATX / battery', 'A'),
    ('F1', 1, 'Fusível retardado', 'Slow-blow fuse', '3 A', '3 A', 'A'),
    ('D1', 1, 'Diodo Schottky SS34', 'SS34 Schottky diode', '3 A · 40 V', '3 A · 40 V', 'A'),
    ('D2', 1, 'Supressor TVS SMBJ15A', 'SMBJ15A TVS suppressor', '15 V · 600 W', '15 V · 600 W', 'A'),
    ('C1', 1, 'Capacitor eletrolítico', 'Electrolytic capacitor', '1000 µF · 25 V', '1000 µF · 25 V', 'A'),
    ('C2, C5', 2, 'Capacitor cerâmico', 'Ceramic capacitor', '100 nF · 50 V', '100 nF · 50 V', 'A'),
    ('U1', 1, 'Módulo buck MP1584 / LM2596', 'MP1584 / LM2596 buck module', '12 → 5 V · 3 A', '12 → 5 V · 3 A', 'A'),
    ('C3', 1, 'Capacitor eletrolítico', 'Electrolytic capacitor', '100 µF · 16 V', '100 µF · 16 V', 'A'),
    ('C4', 1, 'Capacitor cerâmico', 'Ceramic capacitor', '10 µF · 16 V', '10 µF · 16 V', 'A'),
    ('U2', 1, 'Placa ESP32 DevKit v1', 'ESP32 DevKit v1 board', '30 pinos', '30-pin', 'A'),
    ('R2', 1, 'Resistor', 'Resistor', '100 kΩ', '100 kΩ', 'A'),
    ('R3', 1, 'Resistor', 'Resistor', '27 kΩ', '27 kΩ', 'A'),
    ('R4, R7', 2, 'Resistor', 'Resistor', '10 kΩ', '10 kΩ', 'A'),
    ('R5', 1, 'Resistor', 'Resistor', '20 kΩ', '20 kΩ', 'A'),
    ('R6', 1, 'Resistor', 'Resistor', '150 Ω', '150 Ω', 'A'),
    ('TH1', 1, 'Termostato bimetálico KSD9700', 'KSD9700 bimetal thermostat', '70 °C · NF', '70 °C · NC', 'A'),
    ('EL1-EL3', 3, 'Lâmpada halógena W5W com soquete T10', 'W5W halogen lamp with T10 socket', '12 V · 5 W', '12 V · 5 W', 'A'),
    ('Q1', 1, 'MOSFET canal N IRLZ44N', 'IRLZ44N N-channel MOSFET', 'logic-level · TO-220', 'logic-level · TO-220', 'A'),
    ('TS1', 1, 'Sensor de temperatura LM35DZ', 'LM35DZ temperature sensor', '10 mV/°C · TO-92', '10 mV/°C · TO-92', 'B'),
    ('C6, C8, C10', 3, 'Capacitor cerâmico', 'Ceramic capacitor', '100 nF · 50 V', '100 nF · 50 V', 'B'),
    ('C9', 1, 'Capacitor cerâmico', 'Ceramic capacitor', '1 µF · 16 V', '1 µF · 16 V', 'B'),
    ('R11', 1, 'Resistor', 'Resistor', '75 Ω', '75 Ω', 'B'),
    ('M1', 1, 'Ventoinha 40 × 40 × 10 mm, 2 fios', '40 × 40 × 10 mm fan, 2-wire', '12 V · 0,1 A', '12 V · 0.1 A', 'B'),
    ('Q2', 1, 'MOSFET canal N IRLZ44N (alt. AO3400)', 'IRLZ44N N-channel MOSFET (alt. AO3400)', 'logic-level', 'logic-level', 'B'),
    ('D3', 1, 'Diodo Schottky SS14 (alt. 1N5819)', 'SS14 Schottky diode (alt. 1N5819)', '1 A · 40 V', '1 A · 40 V', 'B'),
    ('R9', 1, 'Resistor', 'Resistor', '100 Ω', '100 Ω', 'B'),
    ('R10', 1, 'Resistor', 'Resistor', '10 kΩ', '10 kΩ', 'B'),
    ('DS1', 1, 'Módulo display TM1637', 'TM1637 display module', '4 dígitos com ponto', '4 digits with point', 'B'),
]

# ------------------------------------------------------------------ geometria (mm)
W, H = 420.0, 297.0
BX0, BY0, BX1, BY1 = 20.0, 10.0, 410.0, 287.0          # borda
FX0, FY0, FX1, FY1 = 25.0, 15.0, 405.0, 282.0          # quadro interno (zonas por fora)
NCOL, NLIN = 8, 6
TB = (268.0, 224.0, 137.0, 58.0)                        # carimbo
RT = (268.0, 15.0, 137.0)                               # tabela de revisoes (x, y, largura)

# quadro de cada bloco: (x, y, largura, altura)
QUADROS = {
    '1': (27, 17, 145, 46),
    '2': (27, 65, 145, 44),
    '5': (27, 111, 145, 70),
    '3': (174, 17, 92, 100),
    '8': (174, 119, 92, 62),
    '4': (174, 183, 92, 97),
    '6': (268, 50, 137, 92),
    '7': (268, 144, 137, 78),
}
NOTAS_QUADRO = (27, 183, 145, 97)
TITULO_H, PAD = 7.0, 2.0

esc = html.escape


def borda(folha_txt):
    """Moldura, zonas e marcas de centro em SVG (mm)."""
    s = [f'<svg class="frame" viewBox="0 0 {W} {H}" width="{W}mm" height="{H}mm">']
    s.append(f'<rect x="{BX0}" y="{BY0}" width="{BX1 - BX0}" height="{BY1 - BY0}" fill="none" stroke="#000" stroke-width="0.7"/>')
    s.append(f'<rect x="{FX0}" y="{FY0}" width="{FX1 - FX0}" height="{FY1 - FY0}" fill="none" stroke="#000" stroke-width="0.35"/>')
    cw = (FX1 - FX0) / NCOL
    lh = (FY1 - FY0) / NLIN
    for i in range(NCOL + 1):
        x = FX0 + i * cw
        if 0 < i < NCOL:
            s.append(f'<line x1="{x}" y1="{BY0}" x2="{x}" y2="{FY0}" stroke="#000" stroke-width="0.25"/>')
            s.append(f'<line x1="{x}" y1="{FY1}" x2="{x}" y2="{BY1}" stroke="#000" stroke-width="0.25"/>')
        if i < NCOL:
            cx = x + cw / 2
            s.append(f'<text x="{cx}" y="{BY0 + 3.6}" class="zn">{i + 1}</text>')
            s.append(f'<text x="{cx}" y="{FY1 + 3.6}" class="zn">{i + 1}</text>')
    for j in range(NLIN + 1):
        y = FY0 + j * lh
        if 0 < j < NLIN:
            s.append(f'<line x1="{BX0}" y1="{y}" x2="{FX0}" y2="{y}" stroke="#000" stroke-width="0.25"/>')
            s.append(f'<line x1="{FX1}" y1="{y}" x2="{BX1}" y2="{y}" stroke="#000" stroke-width="0.25"/>')
        if j < NLIN:
            cy = y + lh / 2 + 1.2
            letra = 'ABCDEF'[j]
            s.append(f'<text x="{BX0 + 2.5}" y="{cy}" class="zn">{letra}</text>')
            s.append(f'<text x="{FX1 + 2.5}" y="{cy}" class="zn">{letra}</text>')
    # marcas de centro (ISO 5457)
    s.append(f'<line x1="{W / 2}" y1="{BY0 - 5}" x2="{W / 2}" y2="{FY0}" stroke="#000" stroke-width="0.7"/>')
    s.append(f'<line x1="{W / 2}" y1="{FY1}" x2="{W / 2}" y2="{BY1 + 5}" stroke="#000" stroke-width="0.7"/>')
    s.append(f'<line x1="{BX0 - 5}" y1="{H / 2}" x2="{FX0}" y2="{H / 2}" stroke="#000" stroke-width="0.7"/>')
    s.append(f'<line x1="{FX1}" y1="{H / 2}" x2="{BX1 + 5}" y2="{H / 2}" stroke="#000" stroke-width="0.7"/>')
    s.append(f'<text x="{BX0}" y="{BY1 + 6}" class="foot">{esc(DES)} · REV. {REV} · {esc(folha_txt)}</text>')
    s.append('</svg>')
    return ''.join(s)


def carimbo(t, folha):
    x, y, w, h = TB
    return f'''
<div class="tb" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">
  <table class="sign">
    <tr><th style="width:24mm"></th><th>{t['nome']}</th><th style="width:16mm">{t['sigla']}</th><th style="width:24mm">{t['data']}</th></tr>
    <tr><td class="k">{t['elab']}</td><td>{AUTOR}</td><td class="c">{SIGLA}</td><td class="c">{DATA_B}</td></tr>
    <tr><td class="k">{t['aprov']}</td><td>{AUTOR}</td><td class="c">{SIGLA}</td><td class="c">{DATA_B}</td></tr>
  </table>
  <div class="ttl">
    <div class="lbl">{t['projeto']} PIDlampada</div>
    <div class="t1">{t['titulo']}</div>
    <div class="t2">{t['subtitulo'] if folha == 1 else t['subtitulo'] + ' · ' + t['sub2']}</div>
  </div>
  <div class="inst"><span>{t['inst']}</span><span>{t['local']}</span></div>
  <table class="fld">
    <tr>
      <td style="width:38mm"><div class="lbl">{t['n_des']}</div><div class="v big">{DES}</div></td>
      <td style="width:14mm"><div class="lbl">{t['rev']}</div><div class="v big c">{REV}</div></td>
      <td style="width:18mm"><div class="lbl">{t['folha']}</div><div class="v c">{folha} / 2</div></td>
      <td style="width:18mm"><div class="lbl">{t['escala']}</div><div class="v c">{t['sem_escala']}</div></td>
      <td style="width:16mm"><div class="lbl">{t['formato']}</div><div class="v c">A3</div></td>
      <td><div class="lbl">{t['data']}</div><div class="v c">{DATA_B}</div></td>
    </tr>
  </table>
</div>'''


def tabela_revisoes(t):
    x, y, w = RT
    return f'''
<div class="rt" style="left:{x}mm;top:{y}mm;width:{w}mm">
  <table>
    <tr><th colspan="4" class="cap">{t['revisoes']}</th></tr>
    <tr><th style="width:10mm">{t['rev']}</th><th>{t['desc']}</th><th style="width:20mm">{t['data']}</th><th style="width:12mm">{t['resp']}</th></tr>
    <tr><td class="c b">A</td><td>{t['rev_a']}</td><td class="c">{DATA_A}</td><td class="c">{SIGLA}</td></tr>
    <tr><td class="c b">B</td><td>{t['rev_b']}</td><td class="c">{DATA_B}</td><td class="c">{SIGLA}</td></tr>
  </table>
</div>'''


def svg_inline(caminho, k):
    s = open(caminho, encoding='utf-8').read()
    s = re.sub(r'<\?xml[^>]*>', '', s)
    m = re.search(r'viewBox="([-\d.e]+) ([-\d.e]+) ([-\d.e]+) ([-\d.e]+)"', s)
    vw, vh = float(m.group(3)), float(m.group(4))
    wmm, hmm = vw / 36 * k, vh / 36 * k
    s = re.sub(r'height="[^"]*pt"', f'height="{hmm:.2f}mm"', s, count=1)
    s = re.sub(r'width="[^"]*pt"', f'width="{wmm:.2f}mm"', s, count=1)
    return s, wmm, hmm


def legenda_svg():
    return '''<svg width="11mm" height="26mm" viewBox="0 0 11 26" class="leg">
  <polygon points="1,6 7,6 4,0.8" fill="none" stroke="#000" stroke-width="0.3"/>
  <text x="4" y="5.2" font-size="2.6" text-anchor="middle">B</text>
  <polygon points="0.5,9 8,9 10,10.6 8,12.2 0.5,12.2" fill="none" stroke="#000" stroke-width="0.3"/>
  <line x1="4" y1="15" x2="4" y2="17" stroke="#000" stroke-width="0.3"/>
  <line x1="1.5" y1="17" x2="6.5" y2="17" stroke="#000" stroke-width="0.3"/>
  <line x1="2.5" y1="18" x2="5.5" y2="18" stroke="#000" stroke-width="0.3"/>
  <line x1="3.4" y1="19" x2="4.6" y2="19" stroke="#000" stroke-width="0.3"/>
  <line x1="0.5" y1="23.5" x2="8" y2="23.5" stroke="#000" stroke-width="0.3"/>
  <line x1="4" y1="20.5" x2="4" y2="23.5" stroke="#000" stroke-width="0.3"/>
  <circle cx="4" cy="23.5" r="0.7"/>
</svg>'''


def folha1(t, info, k):
    out = [f'<section class="sheet">{borda(t["folha"] + " 1/2")}']
    for n, (x, y, w, h) in QUADROS.items():
        titulo = info[n][0]
        svg, wmm, hmm = svg_inline(os.path.join(BUILD, t['idioma'].lower(), f'bloco_{n}.svg'), k)
        cx = x + (w - wmm) / 2
        cy = y + TITULO_H + (h - TITULO_H - hmm) / 2
        out.append(f'<div class="blk" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">'
                   f'<div class="bt">[{n}]&nbsp; {esc(titulo)}</div></div>')
        out.append(f'<div class="svgbox" style="left:{cx:.2f}mm;top:{cy:.2f}mm">{svg}</div>')
    x, y, w, h = NOTAS_QUADRO
    itens = ''.join(f'<li>{esc(n)}</li>' for n in t['ng'])
    leg = ''.join(f'<div>{esc(s)}</div>' for s in t['leg'])
    out.append(f'''<div class="blk notes" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">
      <div class="bt">{t['notas_gerais']}</div>
      <ol>{itens}</ol>
      <div class="bt2 al">{t['alim_t']}</div>
      <table class="alim"><tr>{''.join(f'<th>{h}</th>' for h in t['alim_h'])}</tr>
      {''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>' for row in t['alim'])}</table>
      <div class="bt2">{t['legenda']}</div>
      <div class="legrow">{legenda_svg()}<div class="legtxt">{leg}</div></div>
    </div>''')
    out.append(tabela_revisoes(t))
    out.append(carimbo(t, 1))
    out.append('</section>')
    return ''.join(out)


def folha2(t, lang):
    out = [f'<section class="sheet">{borda(t["folha"] + " 2/2")}']
    lin = ''.join(
        f'<tr><td class="b">{p}</td><td class="mono">{r}</td><td>{tp if lang == "pt" else te}</td>'
        f'<td>{fp if lang == "pt" else fe}</td><td class="c">{"△" + rv if rv == "B" else rv}</td></tr>'
        for p, r, tp, te, fp, fe, rv in PINOS)
    out.append('<div class="s2col" style="left:27mm;top:18mm;width:190mm">')
    out.append(f'''<div class="s2 pin">
      <div class="h2">{t['pin_t']}</div>
      <table><tr><th style="width:17mm">{t['pino']}</th><th style="width:24mm">{t['rede']}</th>
      <th style="width:22mm">{t['tipo']}</th><th>{t['funcao']}</th><th style="width:11mm">{t['rev']}</th></tr>{lin}</table>
    </div>''')
    notas = ''.join(f'<li><b>{esc(a)}</b> {esc(b)}</li>' for a, b in NOTAS[lang])
    out.append(f'''<div class="s2 nts">
      <div class="h2">{t['notas_t']}</div><ol>{notas}</ol></div></div>''')
    linhas = ''.join(
        f'<tr><td class="c">{i + 1}</td><td class="b">{r}</td><td class="c">{q}</td>'
        f'<td>{dp if lang == "pt" else de}</td><td>{ep if lang == "pt" else ee}</td>'
        f'<td class="c">{"△" + rv if rv == "B" else rv}</td></tr>'
        for i, (r, q, dp, de, ep, ee, rv) in enumerate(BOM))
    out.append(f'''<div class="s2 bom" style="left:223mm;top:18mm;width:180mm">
      <div class="h2">{t['bom_t']}</div>
      <table><tr><th style="width:9mm">{t['item']}</th><th style="width:20mm">{t['ref']}</th><th style="width:10mm">{t['qtd']}</th>
      <th>{t['descr']}</th><th style="width:40mm">{t['espec']}</th><th style="width:10mm">{t['rev']}</th></tr>{linhas}</table>
      <p class="rem">{esc(t['removidos'])}</p>
    </div>''')
    out.append(carimbo(t, 2))
    out.append('</section>')
    return ''.join(out)


CSS = '''
@page { size: 420mm 297mm; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; color: #000;
  font-family: "DejaVu Sans Condensed", "Arial Narrow", Arial, sans-serif; }
.sheet { position: relative; width: 420mm; height: 297mm; overflow: hidden; page-break-after: always; break-after: page; }
.sheet:last-child { page-break-after: auto; break-after: auto; }
.frame { position: absolute; left: 0; top: 0; }
.frame .zn { font-size: 3.2px; text-anchor: middle; font-family: inherit; }
.frame .foot { font-size: 2.4px; fill: #444; font-family: inherit; }
.blk { position: absolute; border: 0.25mm solid #000; }
.blk .bt { position: absolute; left: 0; top: 0; padding: 0.9mm 2.2mm; font-size: 2.9mm; font-weight: bold;
  border-right: 0.25mm solid #000; border-bottom: 0.25mm solid #000; letter-spacing: 0.02em; background: #fff; }
.svgbox { position: absolute; }
.svgbox svg { display: block; }
.notes ol { position: absolute; top: 9mm; left: 3mm; right: 3mm; margin: 0; padding-left: 5mm;
  font-size: 2.6mm; line-height: 1.32; }
.notes .bt2.al { top: 33mm; }
.notes table.alim { position: absolute; left: 3mm; top: 38mm; width: calc(100% - 6mm); }
.notes table.alim th, .notes table.alim td { border: 0.25mm solid #000; font-size: 2.4mm; padding: 0.7mm 1.2mm; text-align: left; }
.notes table.alim th { font-size: 2.1mm; background: #eee; }
.notes .bt2 { position: absolute; left: 3mm; top: 62mm; font-size: 2.6mm; font-weight: bold; }
.notes .legrow { position: absolute; left: 4mm; top: 67mm; display: flex; gap: 2mm; }
.notes .leg { width: 11mm; height: 26mm; flex: none; }
.notes .legtxt { font-size: 2.45mm; display: grid; grid-auto-rows: 6.2mm; padding-top: 0.6mm; }
.rt { position: absolute; }
table { border-collapse: collapse; width: 100%; }
.rt th, .rt td { border: 0.25mm solid #000; font-size: 2.35mm; padding: 0.7mm 1.2mm; vertical-align: top; }
.rt th { font-weight: bold; text-align: center; }
.rt th.cap { font-size: 2.7mm; letter-spacing: 0.08em; }
.c { text-align: center; } .b { font-weight: bold; }
.tb { position: absolute; border: 0.6mm solid #000; display: flex; flex-direction: column; }
.tb .sign th, .tb .sign td { border: 0.25mm solid #000; font-size: 2.35mm; padding: 0.6mm 1.2mm; height: 4.6mm; }
.tb .sign th { font-size: 2mm; font-weight: bold; }
.tb .sign td.k { font-size: 2.1mm; font-weight: bold; }
.tb .ttl { border-top: 0.5mm solid #000; padding: 1mm 2mm; height: 17mm; }
.tb .t1 { font-size: 3.9mm; font-weight: bold; letter-spacing: 0.01em; margin-top: 0.4mm; }
.tb .t2 { font-size: 2.6mm; margin-top: 0.6mm; }
.tb .lbl { font-size: 1.9mm; color: #333; letter-spacing: 0.04em; }
.tb .inst { border-top: 0.25mm solid #000; display: flex; justify-content: space-between; font-size: 2.15mm;
  padding: 1.2mm 2mm; height: 6.5mm; }
.tb .fld { border-top: 0.5mm solid #000; flex: 1; }
.tb .fld td { border-left: 0.25mm solid #000; padding: 0.6mm 1.2mm; vertical-align: top; }
.tb .fld td:first-child { border-left: 0; }
.tb .v { font-size: 3.2mm; margin-top: 2.6mm; }
.tb .v.big { font-size: 3.6mm; font-weight: bold; }
.s2col { position: absolute; display: flex; flex-direction: column; gap: 9mm; }
.s2col .s2 { position: static; }
.s2 { position: absolute; }
.s2 .h2 { font-size: 3.5mm; font-weight: bold; letter-spacing: 0.06em; border-bottom: 0.5mm solid #000; padding-bottom: 0.8mm; margin-bottom: 1.5mm; }
.s2 th, .s2 td { border: 0.25mm solid #000; font-size: 2.85mm; padding: 1mm 1.5mm; text-align: left; vertical-align: top; }
.s2 th { font-size: 2.5mm; background: #eee; }
.s2 td.c, .s2 th.c { text-align: center; }
.s2 .mono { font-family: "DejaVu Sans Mono", Consolas, monospace; font-size: 2.6mm; }
.s2.nts ol { margin: 0; padding-left: 6mm; font-size: 3.05mm; line-height: 1.4; }
.s2.nts li { margin-bottom: 1.5mm; }
.s2 .rem { font-size: 2.8mm; margin: 1.6mm 0 0; }
'''


def gerar_html(lang):
    t = TXT[lang]
    pasta = os.path.join(BUILD, lang)
    info = B.gerar(pasta, lang=lang)
    # escala unica: a maior que faz todos os blocos caberem nos quadros
    k = 6.0
    for n, (x, y, w, h) in QUADROS.items():
        _, bw, bh = info[n]
        fx = (w - 2 * PAD) / (bw / B.ESCALA_MM)
        fy = (h - TITULO_H - PAD) / (bh / B.ESCALA_MM)
        k = min(k, fx, fy)
    doc = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{DES} rev {REV}</title>'
           f'<style>{CSS}</style></head><body>{folha1(t, info, k)}{folha2(t, lang)}</body></html>')
    caminho = os.path.join(BUILD, f'folha_{lang}.html')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'{lang}: escala {k:.2f} mm/unidade -> {caminho}')
    return caminho, t['arquivo']


def pdf(html_path, destino):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('playwright ausente: abra', html_path, 'no navegador e imprima em PDF (A3 paisagem, sem margens)')
        return
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto('file://' + os.path.abspath(html_path))
        pg.wait_for_timeout(300)
        pg.pdf(path=destino, width='420mm', height='297mm', print_background=True, prefer_css_page_size=True)
        b.close()
    print('pdf:', destino)


if __name__ == '__main__':
    os.makedirs(BUILD, exist_ok=True)
    for lang in ('pt', 'en'):
        h, nome = gerar_html(lang)
        pdf(h, os.path.join(AQUI, nome))
