# Hardware

| Arquivo | Conteudo |
|---------|----------|
| `Proposta_Camara_Termica_ESP32.pdf` | Folha A4 de proposta (camara compacta original) |
| `Esquema_Eletrico_Rev_D.pdf` | **Revisao atual** do PIDL-ESQ-001, A3, 3 folhas: potencia com tabela de revisoes, redes de alimentacao e condutores (folha 1); controle e medicao, notas gerais e interligacao das redes (folha 2); pinagem, notas de projeto e lista de materiais eletrica (folha 3) |
| `Electrical_Schematic_Rev_D_EN.pdf` | O mesmo desenho em ingles |
| `Desenho_Mecanico_Rev_A.pdf` | PIDL-MEC-001, A3, 2 folhas: corte A-A da camara de policarbonato (1:2) com baloes, lista de materiais mecanica, dimensionamento termico e notas de montagem (folha 1); plano de corte da chapa 1000 x 1000 (1:10), furacao dos cinco paineis e da prateleira (1:4), cantoneiras e tabela de furos (folha 2) |
| `Mechanical_Drawing_Rev_A_EN.pdf` | O mesmo desenho em ingles |
| `latex/` | O esquema Rev. D em LaTeX (circuitikz): `esquema_eletrico.tex` e o PDF compilado |
| `Esquema_Eletrico_Rev_A/B/C.pdf`, `Electrical_Schematic_Rev_B/C_EN.pdf` | Revisoes anteriores (historico) |
| `esquema_blocos.py` | Os dez blocos do esquema em SchemDraw (textos PT/EN) |
| `esquema_dados.py` | Revisoes, textos, pinagem, notas, redes e lista de materiais do esquema |
| `esquema_eletrico.py` | Monta as 3 folhas do esquema e gera os dois PDFs |
| `desenho_mecanico.py` | Desenha o PIDL-MEC-001 (corte, paineis, furos em `FUROS`) e gera os dois PDFs |
| `folha_a3.py` | Moldura com zonas, carimbo e tabela de revisoes, comuns aos dois desenhos |
| `esquema_rev_a.py` | Script da Rev. A (historico) |

Para regerar os PDFs apos uma alteracao:

```powershell
pip install schemdraw playwright
python -m playwright install chromium
cd docs\hardware
python esquema_eletrico.py
python desenho_mecanico.py
```

Sem o Playwright, os scripts deixam o HTML em `build\`: abra no navegador e
imprima em PDF (A3 paisagem, margens "nenhuma").

Para uma nova revisao do esquema: acrescente a linha em `REVISOES`
(`esquema_dados.py`), atualize `REV` e `DATA`, mude `REV_ATUAL` em
`esquema_blocos.py` e marque com `rev(d, (x, y), 'E')` o que mudou.

## O que mudou da Rev. C para a Rev. D

A camara compacta de acrilico virou uma caixa de **policarbonato compacto
cristal de 6 mm, 250 x 250 x 250 mm** (desenho PIDL-MEC-001), com a manta e os
dissipadores no piso e uma prateleira de aluminio perfurado a 70 mm por cima,
para as amostras. A caixa grande perde ~1,6 W/K, entao a potencia subiu:

- **[6] Lampadas:** 3 -> 5 x W5W (25 W). Sozinhas elas so levam a camara a
  ambiente + 16 degC; cinco e' um bom limite (cada uma a mais da ~3 degC).
- **[9] Manta:** H1 de 100 x 100 / 30 W para **200 x 200 mm / 80 W** (1,8 ohm,
  6,7 A), sob dois dissipadores aletados de 200 x 100 mm. Q3 passa a IRLB8721
  (8,7 mohm: ~0,4 W a 6,7 A).
- **[7] Ventilacao:** cooler M1 de 40 para **80 mm**; nova ventoinha de
  circulacao **M2 60 mm**, sempre ligada, soprando ao longo das aletas (C11).
- **[10] Cadeia de seguranca (novo):** com 8,8 A de carga os termostatos nao
  podem mais passar a corrente. TH1 (KSD301 85 degC, no ar) e TH2 (KSD301
  120 degC, no dissipador) ficam em serie com a **bobina do rele automotivo
  K1** (~80 mA), com D5 1N4007 de roda livre. O contato NA do K1 gera a rede
  `+12V_TH` (lampadas + manta). Ventoinhas e ESP32 ficam fora da cadeia.
- **[1] Entrada:** D1 trocado pelo **P-MOSFET Q4 IRF4905** (R14 10 k, zener D4
  15 V): 20 mohm em vez de ~5 W de perda num Schottky. F1 15 A lamina, SW1
  15 A, C1 2200 uF, BT1 3S2P (BMS >= 15 A).
- **Firmware:** setpoint maximo 60 -> 70 degC, corte 68 -> 78 degC, Kp 0,080,
  Ki 0,000100; o rele aberto corta lampadas e manta tambem no modelo.

## BOM — itens novos ou alterados da Rev. D

| Ref | Peca | Qtd |
|-----|------|-----|
| EL4, EL5 | Lampada W5W 12 V 5 W + soquete T10 | 2 |
| H1 | Manta de silicone 200 x 200 mm 12 V 80 W (substitui a de 30 W) | 1 |
| — | Dissipador aletado de aluminio 200 x 100 x 30 mm | 2 |
| Q3 | IRLB8721 (substitui o IRLZ44N) | 1 |
| M1 | Ventoinha 80 x 80 x 25 mm 12 V (substitui a de 40 mm) | 1 |
| M2 | Ventoinha 60 x 60 x 15 mm 12 V | 1 |
| C11 | 100 nF ceramico | 1 |
| K1 | Rele automotivo 12 V 30 A NA + soquete | 1 |
| D5 | 1N4007 | 1 |
| TH1 | KSD301 85 degC NF (substitui o de 70 degC) | 1 |
| TH2 | KSD301 120 degC NF (substitui o de 100 degC) | 1 |
| Q4 | IRF4905 + dissipador pequeno (substitui o D1) | 1 |
| D4 | Zener 15 V 0,5 W | 1 |
| R14 | 10 k 1/4 W | 1 |
| F1 | Fusivel lamina 15 A + porta-fusivel | 1 |
| SW1 | Chave SPDT 15 A | 1 |
| C1 | 2200 uF 25 V (substitui o de 1000 uF) | 1 |
| BT1 | Pack 3S2P 18650 alto dreno, BMS >= 15 A | 1 |

A parte mecanica (chapa de PC, cantoneiras, base de MDF, prateleira,
dobradicas, parafusos) esta na lista do PIDL-MEC-001.

## O que mudou da Rev. B para a Rev. C

- **[9] Manta (novo):** manta de silicone H1 12 V / 30 W (4,8 ohms) colada sob
  um dissipador de aluminio aletado, com isolante de fibra ceramica embaixo.
  Q3 IRLZ44N low-side no GPIO27 (HEAT_GATE, LEDC canal 1), R12 150 ohms,
  R13 10 k. TH2 KSD301 100 degC NF no dissipador, em serie com a manta.
  Carga resistiva: sem diodo de roda livre.
- **[6] TH1:** KSD9700 trocado por KSD301 70 degC **10 A**, porque agora
  passam lampadas + manta (~3,75 A). A saida dele vira a rede `+12V_TH`, que
  alimenta tambem o bloco [9].
- **[1] Entrada:** F1 3 A -> 6,3 A retardado, D1 SS34 -> SB560 (5 A), SW1 de
  10 A, BMS do pack com pelo menos 8 A.
- **[3] ESP32:** GPIO27 passa a HEAT_GATE; o botao reservado vai para o GPIO13.

## O que mudou da Rev. A para a Rev. B

- **[4] Sensor:** DS18B20 trocado pelo **LM35DZ (TS1)**, como na proposta. Vai
  no **+5 V** (precisa de 4 a 30 V), com C8 100 nF no VS e filtro R11 75 ohm +
  C9 1 uF na saida. Entrada no GPIO32 (ADC1_CH4). R1 (pull-up 1-Wire) saiu.
- **[7] Cooler (novo):** ventoinha 40 mm 12 V (M1), Q2 low-side (IRLZ44N ou
  AO3400) no GPIO26, R9 100 ohm no gate, R10 10 k de pull-down, **D3 SS14**
  em antiparalelo com o motor e C6 100 nF nos terminais. Alimentado antes do
  TH1, para continuar girando se o termostato abrir.
- **[8] Display (novo):** TM1637 de 4 digitos (DS1) no 3V3, CLK GPIO18, DIO
  GPIO19, C10 100 nF de desacoplamento.
- **[3] ESP32:** LED de status no GPIO2 (o da placa), no lugar do GPIO16.
- **[1] Entrada:** ligacao da chave SW1 redesenhada (entrada ATX designada J1).

## Por que diodo no cooler e nao nas lampadas

Lampada halogena e' carga **resistiva**: ao cortar a corrente nao sobra
energia guardada, e o Q1 nao precisa de diodo de roda livre (a protecao do
lado das lampadas e' o D2 SMBJ15A no barramento e o D1 contra inversao).
O motor do cooler e' **indutivo**: ao cortar o PWM a bobina tenta manter a
corrente e a tensao no dreno do Q2 dispara. O D3 da um caminho para essa
corrente voltar ao +12 V. Schottky porque e' rapido e o PWM e' de 25 kHz.

## BOM — itens novos da Rev. C

| Ref | Peca | Qtd |
|-----|------|-----|
| H1 | Manta de silicone 100 x 100 mm 12 V 30 W | 1 |
| — | Dissipador de aluminio aletado 100 x 100 mm | 1 |
| — | Papel de fibra ceramica 2 mm (isolante) | 1 |
| TH2 | KSD301 100 degC NF 10 A | 1 |
| TH1 | KSD301 70 degC NF 10 A (substitui o KSD9700) | 1 |
| Q3 | IRLZ44N | 1 |
| R12 | 150 ohm 1/4 W | 1 |
| R13 | 10 k 1/4 W | 1 |
| F1 | Fusivel retardado 6,3 A (substitui o de 3 A) | 1 |
| D1 | SB560 (substitui o SS34) | 1 |
| SW1 | Chave SPDT 10 A (substitui a de 3 A) | 1 |

## BOM — itens novos da Rev. B

| Ref | Peca | Qtd |
|-----|------|-----|
| M1 | Ventoinha 40x40x10 mm 12 V, 2 fios (~0,1 A) | 1 |
| Q2 | IRLZ44N (ou AO3400 SOT-23) | 1 |
| D3 | SS14 ou 1N5819 (Schottky 1 A 40 V) | 1 |
| DS1 | Modulo TM1637 4 digitos, com ponto decimal | 1 |
| TS1 | LM35DZ (substitui o DS18B20) | 1 |
| R9 | 100 ohm 1/4 W | 1 |
| R10 | 10 k 1/4 W | 1 |
| R11 | 75 ohm 1/4 W | 1 |
| C6, C8, C10 | 100 nF ceramico | 3 |
| C9 | 1 uF ceramico | 1 |
