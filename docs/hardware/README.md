# Hardware

| Arquivo | Conteudo |
|---------|----------|
| `Proposta_Camara_Termica_ESP32.pdf` | Folha A4 de proposta — vista isometrica, BOM, cadeia de potencia |
| `Esquema_Eletrico_Rev_A.pdf` | Rev. A — seis blocos, pinagem, notas de projeto |
| `esquema_rev_a.py` | Script que gera a Rev. A (SchemDraw) |
| `Esquema_Eletrico_Rev_B.pdf`, `Electrical_Schematic_Rev_B_EN.pdf` | Rev. B (historico): cooler, display, LM35 |
| `Esquema_Eletrico_Rev_C.pdf` | **Revisao atual**, desenho PIDL-ESQ-001, A3, 2 folhas: nove blocos com tabela de revisoes e carimbo (folha 1); pinagem, notas de projeto, notas gerais, redes de alimentacao e lista de materiais (folha 2) |
| `Electrical_Schematic_Rev_C_EN.pdf` | O mesmo desenho em ingles |
| `esquema_blocos.py` | Os nove blocos do esquema em SchemDraw (textos PT/EN) |
| `esquema_eletrico.py` | Monta as folhas (moldura com zonas, revisoes, carimbo, tabelas) e gera os dois PDFs |

Para regerar os PDFs apos uma alteracao:

```powershell
pip install schemdraw playwright
python -m playwright install chromium
cd docs\hardware
python esquema_eletrico.py
```

Sem o Playwright, o script deixa `build\folha_pt.html` e `build\folha_en.html`:
abra no navegador e imprima em PDF (A3 paisagem, margens "nenhuma").

Para uma nova revisao: acrescente o texto `rev_d` em `TXT` e a linha em
`tabela_revisoes()`, atualize `REV` e as datas, e marque com `rev(d, (x, y), 'D')`
o que mudou em `esquema_blocos.py`.

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
