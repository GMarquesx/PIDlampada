"""
Dados do esquema eletrico PIDL-ESQ-001 (revisoes, textos PT/EN, pinagem,
notas de projeto, lista de materiais e interligacao das redes).
Usado por esquema_eletrico.py.
"""

DES = 'PIDL-ESQ-001'
REV = 'D'
DATA = '11/10/2026'

REVISOES = {
    'pt': [
        ('A', 'Release inicial.', '10/10/2026'),
        ('B', 'Cooler M1 (Q2, D3, C6, R9, R10). Display DS1 TM1637 (C10). LM35DZ TS1 no lugar do DS18B20 (C8, R11, C9). '
              'Entrada ATX = J1. Removidos R1, R8, LED1.', '11/10/2026'),
        ('C', 'Manta H1 30 W com Q3, R12, R13 e TH2. TH1 KSD301 10 A. F1 6,3 A, D1 SB560, SW1 10 A. GPIO27 = HEAT_GATE.',
         '11/10/2026'),
        ('D', 'Câmara de policarbonato 25 cm (PIDL-MEC-001): 5 lâmpadas, manta 80 W com Q3 IRLB8721, cooler 80 mm e '
              'ventoinha de circulação M2 (C11). Cadeia de segurança TH1 85 °C + TH2 120 °C na bobina do relé K1 (D5), '
              'que gera +12V_TH. Q4 IRF4905 no lugar do D1 (R14, D4). F1 15 A, SW1 15 A, C1 2200 µF, BT1 3S2P. '
              'Desenho em 3 folhas.', '11/10/2026'),
    ],
    'en': [
        ('A', 'Initial release.', '10/10/2026'),
        ('B', 'Fan M1 (Q2, D3, C6, R9, R10). Display DS1 TM1637 (C10). LM35DZ TS1 replaces DS18B20 (C8, R11, C9). '
              'ATX input = J1. Removed R1, R8, LED1.', '11/10/2026'),
        ('C', 'Heater H1 30 W with Q3, R12, R13 and TH2. TH1 KSD301 10 A. F1 6.3 A, D1 SB560, SW1 10 A. GPIO27 = HEAT_GATE.',
         '11/10/2026'),
        ('D', 'Polycarbonate chamber 25 cm (PIDL-MEC-001): 5 lamps, 80 W heater with Q3 IRLB8721, 80 mm fan and '
              'circulation fan M2 (C11). Safety chain TH1 85 °C + TH2 120 °C on the coil of relay K1 (D5), which '
              'feeds +12V_TH. Q4 IRF4905 replaces D1 (R14, D4). F1 15 A, SW1 15 A, C1 2200 µF, BT1 3S2P. '
              'Drawing split into 3 sheets.', '11/10/2026'),
    ],
}

TXT = {
    'pt': dict(
        arquivo='Esquema_Eletrico_Rev_D.pdf',
        titulo='CÂMARA TÉRMICA COM CONTROLE PWM',
        sub=['ESQUEMA ELÉTRICO · POTÊNCIA', 'ESQUEMA ELÉTRICO · CONTROLE E MEDIÇÃO',
             'PINAGEM · NOTAS DE PROJETO · LISTA DE MATERIAIS'],
        folha='FOLHA', escala='S/ ESC.',
        notas_gerais='NOTAS GERAIS',
        ng=[
            'Folha 1: potência. Folha 2: controle e medição. Folha 3: pinagem, notas e materiais.',
            'Triângulo com "D": incluído ou alterado nesta revisão. Revisões anteriores na tabela da folha 1.',
            'Etiquetas de rede com o mesmo nome estão interligadas, inclusive entre folhas.',
            'Todos os símbolos de terra são o mesmo nó: GND do pack, do ATX, do U1 e do U2.',
            'Resistores 1/4 W 5 %. Capacitores cerâmicos X7R 50 V. Salvo indicação.',
            'Malha de potência (+12 V PROT, K1, +12V_TH, EL1-EL5, H1, Q1, Q3, Q4): fio de 1,5 mm² (15 A).',
            'Montagem mecânica, furação e plano de corte da chapa: desenho PIDL-MEC-001.',
        ],
        alim_t='REDES DE ALIMENTAÇÃO', alim_h=('REDE', 'ORIGEM', 'CARGAS', 'CORRENTE'),
        alim=[('+12 V PROT', 'J1 ou BT1, via SW1, F1 e Q4', 'K1 e cadeia TH1/TH2, M1, M2, U1, R2/R3', '≈ 9,1 A máx.'),
              ('+12V_TH', 'contato NA do K1', 'EL1-EL5 (25 W), H1 (80 W)', '≈ 8,8 A máx.'),
              ('+5 V', 'U1 (buck)', 'U2 (VIN), TS1', '≈ 0,3 A pico'),
              ('+3V3', 'regulador da placa U2', 'DS1', '≤ 30 mA')],
        fonte='Fonte: ATX ≥ 300 W com 12 V ≥ 12 A. A bateria 3S2P mantém 45 °C por ~1,5 h.',
        legenda='LEGENDA',
        leg=['alteração desta revisão', 'etiqueta de rede (liga pelo nome)', 'terra comum', 'junção'],
        fios_t='CONDUTORES', fios_h=('CIRCUITO', 'SEÇÃO'),
        fios=[('Entrada, K1, +12V_TH, EL1-EL5, H1, Q1, Q3, Q4', '1,5 mm²'),
              ('M1, M2, bobina do K1, TH1, TH2, U1', '0,5 mm²'),
              ('Sinais, TS1 (par trançado), DS1, +5 V', '0,25 mm²')],
        folhas_t='FOLHAS DESTE DESENHO',
        folhas=['Potência: blocos [1] [2] [6] [7] [9] [10]', 'Controle e medição: blocos [3] [4] [5] [8]',
                'Pinagem, notas de projeto e materiais'],
        redes_t='INTERLIGAÇÃO DAS REDES', redes_h=('REDE', 'ORIGEM', 'DESTINO', 'FOLHAS'),
        pin_t='PINAGEM · U2 ESP32 DEVKIT V1', pino='PINO', rede='REDE', tipo='TIPO', funcao='FUNÇÃO', rev='REV.',
        notas_t='NOTAS DE PROJETO',
        bom_t='LISTA DE MATERIAIS (ELÉTRICA)', item='ITEM', ref='REF.', qtd='QTD.', descr='DESCRIÇÃO',
        espec='ESPECIFICAÇÃO',
        bom_obs='Peças mecânicas (chapa de PC, cantoneiras, base de MDF, dobradiças): lista do PIDL-MEC-001. '
                'Removidos ao longo das revisões: R1, R8, LED1, DS18B20 (B) e D1 (D, trocado por Q4).',
        idioma='pt',
    ),
    'en': dict(
        arquivo='Electrical_Schematic_Rev_D_EN.pdf',
        titulo='THERMAL CHAMBER WITH PWM CONTROL',
        sub=['ELECTRICAL SCHEMATIC · POWER', 'ELECTRICAL SCHEMATIC · CONTROL AND SENSING',
             'PINOUT · DESIGN NOTES · BILL OF MATERIALS'],
        folha='SHEET', escala='NTS',
        notas_gerais='GENERAL NOTES',
        ng=[
            'Sheet 1: power. Sheet 2: control and sensing. Sheet 3: pinout, notes and materials.',
            'Triangle with "D": added or changed in this revision. Earlier revisions in the table on sheet 1.',
            'Net labels with the same name are connected, also across sheets.',
            'All ground symbols are the same node: pack, ATX, U1 and U2 GND.',
            'Resistors 1/4 W 5 %. Ceramic capacitors X7R 50 V. Unless noted.',
            'Power loop (+12 V PROT, K1, +12V_TH, EL1-EL5, H1, Q1, Q3, Q4): 1.5 mm² wire (15 A).',
            'Mechanical assembly, drilling and sheet cutting plan: drawing PIDL-MEC-001.',
        ],
        alim_t='POWER NETS', alim_h=('NET', 'SOURCE', 'LOADS', 'CURRENT'),
        alim=[('+12 V PROT', 'J1 or BT1, via SW1, F1 and Q4', 'K1 and TH1/TH2 chain, M1, M2, U1, R2/R3', '≈ 9.1 A max.'),
              ('+12V_TH', 'K1 NO contact', 'EL1-EL5 (25 W), H1 (80 W)', '≈ 8.8 A max.'),
              ('+5 V', 'U1 (buck)', 'U2 (VIN), TS1', '≈ 0.3 A peak'),
              ('+3V3', 'U2 on-board regulator', 'DS1', '≤ 30 mA')],
        fonte='Supply: ATX ≥ 300 W with 12 V ≥ 12 A. The 3S2P battery holds 45 °C for ~1.5 h.',
        legenda='LEGEND',
        leg=['change in this revision', 'net label (connects by name)', 'common ground', 'junction'],
        fios_t='WIRING', fios_h=('CIRCUIT', 'SIZE'),
        fios=[('Input, K1, +12V_TH, EL1-EL5, H1, Q1, Q3, Q4', '1.5 mm²'),
              ('M1, M2, K1 coil, TH1, TH2, U1', '0.5 mm²'),
              ('Signals, TS1 (twisted pair), DS1, +5 V', '0.25 mm²')],
        folhas_t='SHEETS IN THIS DRAWING',
        folhas=['Power: blocks [1] [2] [6] [7] [9] [10]', 'Control and sensing: blocks [3] [4] [5] [8]',
                'Pinout, design notes and materials'],
        redes_t='NET INTERCONNECTION', redes_h=('NET', 'SOURCE', 'DESTINATION', 'SHEETS'),
        pin_t='PINOUT · U2 ESP32 DEVKIT V1', pino='PIN', rede='NET', tipo='TYPE', funcao='FUNCTION', rev='REV.',
        notas_t='DESIGN NOTES',
        bom_t='BILL OF MATERIALS (ELECTRICAL)', item='ITEM', ref='REF.', qtd='QTY', descr='DESCRIPTION', espec='RATING',
        bom_obs='Mechanical parts (PC sheet, angles, MDF base, hinges): list on PIDL-MEC-001. '
                'Removed over the revisions: R1, R8, LED1, DS18B20 (B) and D1 (D, replaced by Q4).',
        idioma='en',
    ),
}

REDES = [
    ('PWM_GATE', '[3] U2 GPIO25', '[6] Q1', '2 → 1'),
    ('HEAT_GATE', '[3] U2 GPIO27', '[9] Q3', '2 → 1'),
    ('FAN_GATE', '[3] U2 GPIO26', '[7] Q2', '2 → 1'),
    ('TEMP_S', '[4] TS1 via R11/C9', '[3] U2 GPIO32', '2'),
    ('V_SENSE', '[5] R2/R3', '[3] U2 GPIO34', '2'),
    ('PWR_OK_S', '[5] R4/R5', '[3] U2 GPIO35', '2'),
    ('DISP_CLK · DISP_DIO', '[3] U2 GPIO18 · GPIO19', '[8] DS1', '2'),
    ('+12 V PROT', '[1]', '[2] [7] [10] · [5]', '1 → 1, 2'),
    ('+12V_TH', '[10] contato do K1', '[6] [9]', '1'),
    ('+5 V', '[2] U1', '[3] U2 · [4] TS1', '1 → 2'),
    ('+3V3', '[3] U2', '[8] DS1', '2'),
]

# (pino, rede, tipo pt, tipo en, funcao pt, funcao en, rev)
PINOS = [
    ('GPIO25', 'PWM_GATE', 'saída', 'output', 'Gate do Q1 (5 lâmpadas) · LEDC canal 0, 500 Hz, 10 bits',
     'Q1 gate (5 lamps) · LEDC channel 0, 500 Hz, 10 bit', 'A'),
    ('GPIO27', 'HEAT_GATE', 'saída', 'output', 'Gate do Q3 (manta 80 W) · LEDC canal 1, mesmo timer das lâmpadas',
     'Q3 gate (80 W heater) · LEDC channel 1, same timer as the lamps', 'C'),
    ('GPIO26', 'FAN_GATE', 'saída', 'output', 'Gate do Q2 (cooler 80 mm) · LEDC canal 2, 25 kHz, 8 bits',
     'Q2 gate (80 mm fan) · LEDC channel 2, 25 kHz, 8 bit', 'B'),
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
    ('GPIO13', 'BTN_MODE', 'entrada', 'input', 'Reservado: botão de modo', 'Reserved: mode button', 'C'),
    ('VIN', '+5 V', 'alimentação', 'supply', 'Entrada de 5 V vinda do U1', '5 V input from U1', 'A'),
    ('3V3', '+3V3', 'alimentação', 'supply', 'Saída do regulador da placa → DS1', 'On-board regulator output → DS1', 'A'),
    ('GND', 'GND', 'terra', 'ground', 'Terra comum', 'Common ground', 'A'),
]

NOTAS = {
    'pt': [
        ('Diodos de roda livre só nas cargas indutivas.',
         'Lâmpadas e manta são resistivas e dispensam diodo. O motor do cooler (D3) e a bobina do relé K1 (D5) são '
         'indutivos: ao desligar, a corrente do enrolamento precisa de caminho e, sem o diodo, vira um pico de tensão '
         'que queima o MOSFET ou o termostato. D3 é Schottky porque o PWM é de 25 kHz.'),
        ('Ventoinhas fora da cadeia de segurança.',
         'Em sobretemperatura K1 corta lâmpadas e manta e o firmware põe o cooler a 100 %. Se as ventoinhas também '
         'fossem cortadas, a câmara esfriaria só por convecção.'),
        ('Faixa dividida (split-range).',
         'Um único PI com saída de −1 a 1: positivo aciona lâmpadas e manta, negativo aciona o cooler, nunca os dois '
         'juntos. O cooler tem rotação mínima de 30 % e histerese de liga/desliga.'),
        ('Canais LEDC.',
         'Os canais andam em pares que dividem um timer (0-1, 2-3...). Lâmpadas (0) e manta (1) dividem de propósito '
         'o timer de 500 Hz; o cooler fica no canal 2 para os 25 kHz dele não mudarem essa frequência.'),
        ('LM35 em 5 V.',
         'O LM35 pede de 4 a 30 V. A saída, de 0,25 a 0,70 V na faixa útil, entra no ADC sem divisor. O LM35DZ mede '
         'de 0 a 100 °C: o teto de 70 °C no setpoint deixa folga.'),
        ('TM1637 em 3,3 V.',
         'Os pull-ups do módulo vão no VCC. Com o módulo em 5 V o pino DIO do ESP32 receberia acima do limite.'),
        ('Proteções da entrada.',
         'Q4 (P-MOSFET) faz a proteção contra inversão: conduz com 20 mΩ na polaridade certa e corta na invertida. '
         'D4 limita o VGS. D2 absorve transitórios de hot-plug; F1 é lento para o inrush das lâmpadas frias e do C1. '
         'R7, R10 e R13 seguram os gates em 0 V durante o boot.'),
        ('Compensação de tensão.',
         'Com bateria a tensão cai de 12,6 para ~10 V. O firmware corrige o duty das lâmpadas e da manta por (12/V)² '
         'e o do cooler por 12/V, medindo V pelo V_SENSE.'),
        ('Manta, dissipadores e prateleira.',
         'H1 vai colada sob dois dissipadores aletados, sobre isolante de fibra cerâmica. A ventoinha M2, sempre '
         'ligada, sopra o ar pelas aletas; o ar quente sobe pelos furos da prateleira de alumínio perfurado, onde '
         'ficam as amostras. Lâmpadas e manta recebem o mesmo comando; o feedforward usa o ganho somado (16 + 50 °C).'),
        ('Cadeia de segurança.',
         'TH1 (85 °C, no ar) e TH2 (120 °C, no dissipador) em série com a bobina do K1. Qualquer um que abra solta o '
         'relé e tira a energia de lâmpadas e manta; o firmware ainda corta tudo acima de 78 °C. Os termostatos '
         'só conduzem os ~80 mA da bobina, não os 8,8 A da carga.'),
        ('Câmara de policarbonato.',
         'PC compacto cristal de 6 mm (U ≈ 3,9 W/m²K) aguenta uso contínuo até ~115 °C. Câmara de 25 × 25 × 25 cm: '
         'UA ≈ 1,6 W/K e constante de tempo ≈ 1000 s, por isso a potência subiu para 105 W. Ver PIDL-MEC-001.'),
    ],
    'en': [
        ('Flyback diodes only on inductive loads.',
         'Lamps and heater are resistive and need no diode. The fan motor (D3) and the coil of relay K1 (D5) are '
         'inductive: at turn-off the winding current needs a path and, without the diode, becomes a voltage spike that '
         'kills the MOSFET or the thermostat. D3 is a Schottky because the PWM runs at 25 kHz.'),
        ('Fans outside the safety chain.',
         'On over-temperature K1 cuts lamps and heater and the firmware drives the fan at 100 %. If the fans were cut '
         'too, the chamber would only cool by convection.'),
        ('Split-range control.',
         'A single PI with output from −1 to 1: positive drives lamps and heater, negative drives the fan, never both. '
         'The fan has a 30 % minimum speed and on/off hysteresis.'),
        ('LEDC channels.',
         'Channels come in pairs sharing one timer (0-1, 2-3...). Lamps (0) and heater (1) share the 500 Hz timer on '
         'purpose; the fan uses channel 2 so its 25 kHz does not change that frequency.'),
        ('LM35 at 5 V.',
         'The LM35 needs 4 to 30 V. Its output, 0.25 to 0.70 V over the useful range, goes to the ADC with no divider. '
         'The LM35DZ reads 0 to 100 °C: the 70 °C setpoint ceiling leaves margin.'),
        ('TM1637 at 3.3 V.',
         'The module pull-ups go to VCC. With the module at 5 V the ESP32 DIO pin would see more than its limit.'),
        ('Input protection.',
         'Q4 (P-MOSFET) is the reverse-polarity protection: it conducts with 20 mΩ when polarity is right and blocks '
         'when reversed. D4 clamps VGS. D2 absorbs hot-plug transients; F1 is slow for the inrush of cold lamps and C1. '
         'R7, R10 and R13 hold the gates at 0 V during boot.'),
        ('Voltage compensation.',
         'On battery the bus drops from 12.6 to ~10 V. The firmware scales the lamp and heater duty by (12/V)² and '
         'the fan duty by 12/V, reading V on V_SENSE.'),
        ('Heater, heatsinks and shelf.',
         'H1 is bonded under two finned heatsinks, on ceramic-fibre insulation. Fan M2, always on, blows air through '
         'the fins; the warm air rises through the holes of the perforated aluminium shelf that holds the samples. '
         'Lamps and heater get the same command; the feedforward uses the combined gain (16 + 50 °C).'),
        ('Safety chain.',
         'TH1 (85 °C, in the air) and TH2 (120 °C, on the heatsink) in series with the coil of K1. Either one opening '
         'drops the relay and removes power from lamps and heater; the firmware also cuts everything above 78 °C. The '
         'thermostats only carry the ~80 mA coil current, not the 8.8 A load.'),
        ('Polycarbonate chamber.',
         '6 mm clear solid PC (U ≈ 3.9 W/m²K) withstands continuous use up to ~115 °C. 25 × 25 × 25 cm chamber: '
         'UA ≈ 1.6 W/K and time constant ≈ 1000 s, which is why power went up to 105 W. See PIDL-MEC-001.'),
    ],
}

# (ref, qtd, desc pt, desc en, espec pt, espec en, rev)
BOM = [
    ('BT1', 1, 'Pack 3S2P 18650 (alto dreno) com BMS', '3S2P 18650 pack (high drain) with BMS', '12,6 V · BMS ≥ 15 A', '12.6 V · BMS ≥ 15 A', 'D'),
    ('J1', 1, 'Conector ATX (Molex 4 vias), fonte ≥ 300 W', 'ATX connector (4-pin Molex), PSU ≥ 300 W', '12 V ≥ 12 A', '12 V ≥ 12 A', 'D'),
    ('SW1', 1, 'Chave seletora SPDT', 'SPDT selector switch', '15 A · ATX / bateria', '15 A · ATX / battery', 'D'),
    ('F1', 1, 'Fusível lâmina + porta-fusível', 'Blade fuse + holder', '15 A retardado', '15 A slow', 'D'),
    ('Q4', 1, 'MOSFET canal P IRF4905 + dissipador', 'IRF4905 P-channel MOSFET + heatsink', '55 V · 20 mΩ', '55 V · 20 mΩ', 'D'),
    ('D4', 1, 'Diodo zener', 'Zener diode', '15 V · 0,5 W', '15 V · 0.5 W', 'D'),
    ('D2', 1, 'Supressor TVS SMBJ15A', 'SMBJ15A TVS suppressor', '15 V · 600 W', '15 V · 600 W', 'A'),
    ('C1', 1, 'Capacitor eletrolítico', 'Electrolytic capacitor', '2200 µF · 25 V', '2200 µF · 25 V', 'D'),
    ('C2, C5, C6, C8, C10, C11', 6, 'Capacitor cerâmico', 'Ceramic capacitor', '100 nF · 50 V', '100 nF · 50 V', 'D'),
    ('U1', 1, 'Módulo buck MP1584 / LM2596', 'MP1584 / LM2596 buck module', '12 → 5 V · 3 A', '12 → 5 V · 3 A', 'A'),
    ('C3 · C4', 2, 'Eletrolítico · cerâmico', 'Electrolytic · ceramic', '100 µF · 10 µF, 16 V', '100 µF · 10 µF, 16 V', 'A'),
    ('U2', 1, 'Placa ESP32 DevKit v1', 'ESP32 DevKit v1 board', '30 pinos', '30-pin', 'A'),
    ('TH1', 1, 'Termostato bimetálico KSD301 (no ar)', 'KSD301 bimetal thermostat (in the air)', '85 °C · NF', '85 °C · NC', 'D'),
    ('TH2', 1, 'Termostato bimetálico KSD301 (no dissipador)', 'KSD301 bimetal thermostat (on heatsink)', '120 °C · NF', '120 °C · NC', 'D'),
    ('K1', 1, 'Relé automotivo + soquete', 'Automotive relay + socket', '12 V · 30 A · NA', '12 V · 30 A · NO', 'D'),
    ('D5', 1, 'Diodo retificador 1N4007', '1N4007 rectifier diode', '1 A · 1000 V', '1 A · 1000 V', 'D'),
    ('EL1-EL5', 5, 'Lâmpada halógena W5W com soquete T10', 'W5W halogen lamp with T10 socket', '12 V · 5 W', '12 V · 5 W', 'D'),
    ('Q1, Q2', 2, 'MOSFET canal N IRLZ44N (Q2 alt. AO3400)', 'IRLZ44N N-channel MOSFET (Q2 alt. AO3400)', 'logic-level', 'logic-level', 'A'),
    ('Q3', 1, 'MOSFET canal N IRLB8721', 'IRLB8721 N-channel MOSFET', '8,7 mΩ @ 4,5 V', '8.7 mΩ @ 4.5 V', 'D'),
    ('H1', 1, 'Manta de silicone 200 × 200 mm', '200 × 200 mm silicone heater pad', '12 V · 80 W · 1,8 Ω', '12 V · 80 W · 1.8 Ω', 'D'),
    ('M1', 1, 'Ventoinha de exaustão 80 × 80 × 25 mm', '80 × 80 × 25 mm exhaust fan', '12 V · 0,15 A', '12 V · 0.15 A', 'D'),
    ('M2', 1, 'Ventoinha de circulação 60 × 60 × 15 mm', '60 × 60 × 15 mm circulation fan', '12 V · 0,1 A', '12 V · 0.1 A', 'D'),
    ('D3', 1, 'Diodo Schottky SS14 (alt. 1N5819)', 'SS14 Schottky diode (alt. 1N5819)', '1 A · 40 V', '1 A · 40 V', 'B'),
    ('TS1', 1, 'Sensor de temperatura LM35DZ', 'LM35DZ temperature sensor', '10 mV/°C · TO-92', '10 mV/°C · TO-92', 'B'),
    ('C9', 1, 'Capacitor cerâmico', 'Ceramic capacitor', '1 µF · 16 V', '1 µF · 16 V', 'B'),
    ('DS1', 1, 'Módulo display TM1637', 'TM1637 display module', '4 dígitos com ponto', '4 digits with point', 'B'),
    ('R2 · R3 · R5', 3, 'Resistor', 'Resistor', '100 kΩ · 27 kΩ · 20 kΩ', '100 kΩ · 27 kΩ · 20 kΩ', 'A'),
    ('R4, R7, R10, R13, R14', 5, 'Resistor', 'Resistor', '10 kΩ', '10 kΩ', 'D'),
    ('R6, R12 · R9 · R11', 4, 'Resistor', 'Resistor', '150 Ω · 100 Ω · 75 Ω', '150 Ω · 100 Ω · 75 Ω', 'C'),
]
