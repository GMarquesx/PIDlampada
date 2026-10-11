# Hardware

| Arquivo | Conteudo |
|---------|----------|
| `Proposta_Camara_Termica_ESP32.pdf` | Folha A4 de proposta — vista isometrica, BOM, cadeia de potencia |
| `Esquema_Eletrico_Rev_A.pdf` | Esquema eletrico Rev. A — seis blocos, pinagem, notas de projeto |
| `esquema_rev_a.py` | Script que gera a Rev. A (SchemDraw) |
| `Esquema_Eletrico_Rev_B.pdf` | **Revisao atual**, desenho PIDL-ESQ-001, A3, 2 folhas: esquema com tabela de revisoes e carimbo (folha 1); pinagem, notas de projeto e lista de materiais (folha 2) |
| `Electrical_Schematic_Rev_B_EN.pdf` | O mesmo desenho em ingles |
| `esquema_blocos.py` | Os oito blocos do esquema em SchemDraw (textos PT/EN) |
| `esquema_rev_b.py` | Monta as folhas (moldura com zonas, revisoes, carimbo, tabelas) e gera os dois PDFs |

Para regerar os PDFs apos uma alteracao:

```powershell
pip install schemdraw playwright
python -m playwright install chromium
cd docs\hardware
python esquema_rev_b.py
```

Sem o Playwright, o script deixa `build\folha_pt.html` e `build\folha_en.html`:
abra no navegador e imprima em PDF (A3 paisagem, margens "nenhuma").

Para uma nova revisao: acrescente a linha na tabela de revisoes (`TXT[...]['rev_c']`
e `tabela_revisoes()`), atualize `REV` e as datas, e marque com `rev(d, (x, y))` o que mudou
em `esquema_blocos.py`.

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
