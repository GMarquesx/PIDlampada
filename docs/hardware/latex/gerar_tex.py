"""Gera esquema_eletrico.tex (PIDL-ESQ-001 Rev. D em LaTeX/circuitikz) a partir de esquema_dados.py."""
import sys

import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from esquema_dados import DES, REV, DATA, REVISOES, TXT, REDES, PINOS, NOTAS, BOM  # noqa: E402

t = TXT['pt']


def tex(s):
    rep = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}',
           '~': r'\textasciitilde{}', '^': r'\textasciicircum{}', 'Ω': r'\ensuremath{\Omega}', 'µ': r'\textmu{}', '≥': r'$\geq$',
           '≤': r'$\leq$', '≈': r'$\approx$', '→': r'$\rightarrow$', '←': r'$\leftarrow$', '²': r'$^2$', '·': r'$\cdot$',
           '−': r'$-$', '△': r'$\triangle$', '×': r'$\times$'}
    return ''.join(rep.get(c, c) for c in s)


PRE = r'''% PIDL-ESQ-001 - Esquema eletrico da camara termica PIDlampada - Rev. D
% Versao em LaTeX (circuitikz) do desenho gerado por esquema_eletrico.py.
% Compilar:  pdflatex esquema_eletrico.tex   (duas vezes, por causa do remember picture)
\documentclass{article}
\usepackage[a3paper,landscape,margin=0mm]{geometry}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{textcomp}
\usepackage[scaled=0.92]{helvet}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[siunitx,american,RPvoltages]{circuitikz}
\usetikzlibrary{shapes.symbols,shapes.geometric,calc,positioning}
\usepackage{array,tabularx,colortbl,xcolor}
\pagestyle{empty}
\setlength{\parindent}{0pt}
\definecolor{cinza}{HTML}{EEEEEE}
\definecolor{tinta}{HTML}{333333}
\renewcommand{\arraystretch}{1.18}
\ctikzset{bipoles/length=8mm, tripoles/mos style/arrows}
\tikzset{
  rot/.style={font=\scriptsize, align=left, inner sep=1pt},
  rotr/.style={font=\scriptsize, align=right, inner sep=1pt},
  nota/.style={font=\tiny, align=left, text=tinta, inner sep=1pt},
  rede/.style={draw, signal, signal to=east, signal from=west, font=\tiny, inner sep=1.2pt, minimum height=3.4mm, minimum width=16mm},
  redeL/.style={draw, signal, signal to=west, signal from=east, font=\tiny, inner sep=1.2pt, minimum height=3.4mm, minimum width=16mm},
  rev/.style={draw, isosceles triangle, isosceles triangle apex angle=60, shape border rotate=90, inner sep=0.4pt,
              minimum size=3.6mm, font=\tiny\bfseries},
}
% \bloco{x}{y}{w}{h}{titulo}: quadro com titulo, x/y = canto superior esquerdo em mm (como na prancha)
\newcommand{\bloco}[5]{%
  \draw[line width=0.25mm] (#1,297-#2-#4) rectangle (#1+#3,297-#2);
  \node[anchor=north west, draw, line width=0.25mm, fill=white, font=\footnotesize\bfseries, inner sep=1.4mm]
    at (#1,297-#2) {#5};}
% \caixa{x}{y}{w}{h}{titulo}{conteudo}: quadro com tabela/texto
\newcommand{\caixa}[6]{%
  \bloco{#1}{#2}{#3}{#4}{#5}
  \node[anchor=north west, inner sep=0] at (#1+3,297-#2-8.5) {\begin{minipage}[t]{\dimexpr #3mm-6mm\relax}\scriptsize #6\end{minipage}};}
\newcommand{\lab}[3]{\node[font=\scriptsize, align=left, inner sep=0.8pt, anchor=#2] at (#1) {#3};}
\newcommand{\motor}[2]{\draw (#1,#2) circle (3.3) node {\footnotesize M};}
\newcommand{\gnd}[1]{\node[ground] at (#1) {};}
'''


def moldura(folha, total, sub):
    """Borda com zonas 1-8 / A-F, marcas de centro, carimbo e rodape."""
    z = [r'\draw[line width=0.7mm] (20,10) rectangle (410,287);',
         r'\draw[line width=0.35mm] (25,15) rectangle (405,282);']
    cw, lh = 380 / 8, 267 / 6
    for i in range(1, 8):
        x = 25 + i * cw
        z.append(rf'\draw[line width=0.25mm] ({x:.2f},282) -- ({x:.2f},287) ({x:.2f},10) -- ({x:.2f},15);')
    for i in range(8):
        x = 25 + (i + .5) * cw
        z.append(rf'\node[font=\scriptsize] at ({x:.2f},284.5) {{{i + 1}}}; \node[font=\scriptsize] at ({x:.2f},12.5) {{{i + 1}}};')
    for j in range(1, 6):
        y = 282 - j * lh
        z.append(rf'\draw[line width=0.25mm] (20,{y:.2f}) -- (25,{y:.2f}) (405,{y:.2f}) -- (410,{y:.2f});')
    for j in range(6):
        y = 282 - (j + .5) * lh
        L = 'ABCDEF'[j]
        z.append(rf'\node[font=\scriptsize] at (22.5,{y:.2f}) {{{L}}}; \node[font=\scriptsize] at (407.5,{y:.2f}) {{{L}}};')
    z.append(r'\draw[line width=0.7mm] (210,5) -- (210,15) (210,282) -- (210,292) (15,148.5) -- (25,148.5) (405,148.5) -- (415,148.5);')
    z.append(rf'\node[anchor=south west, font=\tiny, text=tinta] at (20,3) {{{DES} $\cdot$ REV. {REV} $\cdot$ FOLHA {folha}/{total}}};')
    # carimbo (268, 224, 137 x 58)
    x0, y1 = 268, 297 - 224
    z.append(rf'''\draw[line width=0.6mm] ({x0},{y1 - 58}) rectangle ({x0 + 137},{y1});
\foreach \yy in {{4.6,9.3}} \draw[line width=0.25mm] ({x0},{y1}-\yy) -- ({x0 + 137},{y1}-\yy);
\foreach \xx in {{22,97,113}} \draw[line width=0.25mm] ({x0}+\xx,{y1}) -- ({x0}+\xx,{y1 - 14});
\node[font=\tiny\bfseries] at ({x0 + 59.5},{y1 - 2.3}) {{NOME}}; \node[font=\tiny\bfseries] at ({x0 + 105},{y1 - 2.3}) {{SIGLA}};
\node[font=\tiny\bfseries] at ({x0 + 125},{y1 - 2.3}) {{DATA}};
\foreach \yy/\rr in {{7/ELABORADO,11.65/APROVADO}} {{
  \node[font=\tiny\bfseries, anchor=west] at ({x0 + 1.5},{y1}-\yy) {{\rr}};
  \node[font=\scriptsize, anchor=west] at ({x0 + 24},{y1}-\yy) {{Gabriel Marques}};
  \node[font=\scriptsize] at ({x0 + 105},{y1}-\yy) {{GM}}; \node[font=\scriptsize] at ({x0 + 125},{y1}-\yy) {{{DATA}}};}}
\draw[line width=0.4mm] ({x0},{y1 - 14}) -- ({x0 + 137},{y1 - 14});
\node[anchor=north west, align=left, inner sep=0] at ({x0 + 2},{y1 - 15.5}) {{\tiny\color{{tinta}} PROJETO PIDlampada\\[0.6mm]
  \large\bfseries {tex(t['titulo'])}\\[0.4mm] \footnotesize {tex(sub)}}};
\draw[line width=0.25mm] ({x0},{y1 - 32}) -- ({x0 + 137},{y1 - 32});
\node[anchor=west, font=\tiny] at ({x0 + 2},{y1 - 35.5}) {{UNIP $\cdot$ ENGENHARIA DE COMPUTAÇÃO $\cdot$ PROJETO INTEGRADOR 2026}};
\node[anchor=east, font=\tiny] at ({x0 + 135},{y1 - 35.5}) {{SÃO JOSÉ DOS CAMPOS - SP}};
\draw[line width=0.4mm] ({x0},{y1 - 39}) -- ({x0 + 137},{y1 - 39});
\foreach \x in {{38,52,70,88,104}} \draw[line width=0.25mm] ({x0}+\x,{y1 - 39}) -- ({x0}+\x,{y1 - 58});
\foreach \x/\r in {{2/Nº DO DESENHO,40/REV.,54/FOLHA,72/ESCALA,90/FORMATO,106/DATA}}
  \node[anchor=north west, font=\tiny, text=tinta] at ({x0}+\x,{y1 - 40}) {{\r}};
\node[font=\large\bfseries] at ({x0 + 19},{y1 - 50}) {{{DES}}};
\node[font=\Large\bfseries] at ({x0 + 45},{y1 - 50}) {{{REV}}};
\node[font=\normalsize] at ({x0 + 61},{y1 - 50}) {{{folha} / {total}}};
\node[font=\normalsize] at ({x0 + 79},{y1 - 50}) {{S/ ESC.}};
\node[font=\normalsize] at ({x0 + 96},{y1 - 50}) {{A3}};
\node[font=\normalsize] at ({x0 + 120.5},{y1 - 50}) {{{DATA}}};''')
    return '\n'.join(z)


def revisoes():
    linhas = ''.join(rf'\bfseries {r} & {tex(d)} & {dt} & GM\\\hline' + '\n' for r, d, dt in REVISOES['pt'])
    return (r'\node[anchor=north west, inner sep=0] at (268,282) {\scriptsize\setlength{\tabcolsep}{1.2mm}'
            r'\begin{tabularx}{137mm}{|>{\centering\arraybackslash}p{6mm}|X|>{\centering\arraybackslash}p{15mm}|>{\centering\arraybackslash}p{7mm}|}\hline' + '\n'
            r'\multicolumn{4}{|c|}{\bfseries REVISÕES}\\\hline' + '\n'
            r'\bfseries\tiny REV. & \centering\bfseries\tiny DESCRIÇÃO & \bfseries\tiny DATA & \bfseries\tiny RESP.\\\hline' + '\n'
            + linhas + r'\end{tabularx}};')


def tabela(cab, linhas, spec):
    h = ' & '.join(rf'\bfseries\tiny {tex(c)}' for c in cab) + r'\\\hline'
    corpo = ''.join(' & '.join(tex(str(c)) for c in ln) + r'\\\hline' + '\n' for ln in linhas)
    return (rf'\begin{{tabularx}}{{\linewidth}}{{{spec}}}\hline\rowcolor{{cinza}}' + h + '\n' + corpo + r'\end{tabularx}')


# ------------------------------------------------------------------ blocos (coordenadas locais em mm)
B1 = r'''% [1] ENTRADA - SELECAO DE FONTE - PROTECAO   (quadro 156 x 53)
\begin{scope}[shift={(27,227)}]
  \node[spdt, xscale=-1] (sw) at (50,33) {};
  \lab{50,41}{south}{SW1 15 A}  \node[rev] at (41,42.5) {D};
  \node[redeL, anchor=east] (j1) at ($(sw.out 1)+(-14,0)$) {J1 ATX +12 V};
  \draw (j1.east) -- (sw.out 1);
  \draw (30,8) node[ground]{} to[battery1] (30,22) |- (sw.out 2);
  \lab{27,15}{east}{BT1 3S2P 18650\\12,6 V máx.\\BMS $\geq$ 15 A}  \node[rev] at (24,25) {D};
  \draw (sw.in) -- (58,33) to[fuse] (70,33) -- (74,33);
  \lab{64,36.5}{south}{F1 15 A}  \lab{64,29.5}{north}{lâmina retard.}  \node[rev] at (64,43.5) {D};
  \node[pmos, rotate=-90, xscale=-1] (q4) at (81,33) {};
  \draw (74,33) -- (q4.D);
  \lab{81,39.5}{south}{Q4 IRF4905}  \node[rev] at (92.5,42) {D};
  \draw (q4.G) -- (81,22) coordinate (g4) to[R] (81,9) node[ground]{};
  \lab{79,15.5}{east}{R14\\10 k\ensuremath{\Omega}}
  \draw (g4) -- (89,22) to[zDo] (89,33);
  \lab{92,27.5}{west}{D4\\15 V}
  \draw (q4.S) -- (89,33) -- (146,33) -- (146,36); \node[vcc] at (146,36) {}; \lab{146,40}{south}{+12 V PROT}
  \draw (102,12) to[zDo] (102,33);   \lab{105,22.5}{west}{D2\\SMBJ15A}
  \draw (118,33) to[eC] (118,12);    \lab{121,22.5}{west}{C1\\2200 \textmu F\\25 V}  \node[rev] at (118,39) {D};
  \draw (134,33) to[C] (134,12);     \lab{137,22.5}{west}{C2\\100 nF}
  \draw (102,12) -- (134,12); \draw (118,12) node[ground]{};
  \foreach \p in {(89,33),(102,33),(118,33),(134,33),(81,22),(118,12)} \fill \p circle (0.55);
  \node[nota, anchor=north west] at (92,8) {Q4: na polaridade certa conduz com 20 m\ensuremath{\Omega} ($\sim$1,7 W a 9 A);\\invertida, fica cortado. Um Schottky dissiparia $\sim$5 W.};
\end{scope}
'''

B7 = r'''% [7] VENTILACAO - EXAUSTAO E CIRCULACAO   (quadro 156 x 68)
\begin{scope}[shift={(27,157)}]
  \draw (46,49) -- (46,53); \node[vcc] at (46,53) {}; \lab{46,57}{south}{+12 V PROT}
  \motor{46}{40}  \draw (46,49) -- (46,43.3) (46,36.7) -- (46,30);
  \lab{41,40}{east}{M1 exaustão\\80 mm $\cdot$ 12 V\\0,15 A}  \node[rev] at (31,50) {D};
  \draw (46,30) -- (60,30) to[sD] (60,49) -- (46,49);
  \lab{63.5,40}{west}{D3 SS14\\roda livre}
  \draw (60,49) -- (82,49) to[C] (82,30) -- (60,30);
  \lab{85,40}{west}{C6\\100 nF}
  \foreach \p in {(46,49),(60,49),(46,30),(60,30)} \fill \p circle (0.55);
  \node[nmos, anchor=D] (q2) at (46,30) {}; \draw (q2.S) node[ground]{};
  \lab{50,21}{west}{Q2 IRLZ44N\\(alt. AO3400)}
  \draw (q2.G) -- ++(-12,0) coordinate (g2) to[R] ++(-14,0) coordinate (t2);
  \lab{$(g2)+(-7,2.8)$}{south}{R9 100 \ensuremath{\Omega}}
  \node[redeL, anchor=east] at (t2) {FAN\_GATE};
  \draw (g2) to[R] ++(0,-13) node[ground]{}; \fill (g2) circle (0.55);
  \lab{$(g2)+(-2,-6.5)$}{east}{R10\\10 k\ensuremath{\Omega}}
  \node[nota, anchor=north west] at (72,12) {Motor = carga INDUTIVA. Fora da cadeia do K1: em sobretemperatura\\as ventoinhas continuam. PWM 25 kHz, LEDC canal 2, rotação mínima 30 \%.};
  \draw (124,49) -- (124,53); \node[vcc] at (124,53) {}; \lab{124,57}{south}{+12 V PROT}
  \motor{124}{40}  \draw (124,49) -- (124,43.3) (124,36.7) -- (124,30) -- (124,27) node[ground]{};
  \draw (124,49) -- (140,49) to[C] (140,30) -- (124,30);
  \lab{143,40}{west}{C11\\100 nF}
  \foreach \p in {(124,49),(124,30)} \fill \p circle (0.55);
  \lab{119,40}{east}{M2 circulação\\60 mm $\cdot$ 12 V\\sempre ligada}  \node[rev] at (108,50) {D};
  \node[nota, anchor=north west] at (104,22) {Sopra ao longo das aletas, sob a\\prateleira: espalha o calor da manta.};
\end{scope}
'''

B9 = r'''% [9] MANTA DE AQUECIMENTO (LOW-SIDE)   (quadro 156 x 66)
\begin{scope}[shift={(27,89)}]
  \node[redeL, anchor=east] at (52,49) {+12V\_TH};
  \draw (52,49) -- (60,49) to[R] (60,33);
  \lab{63,41}{west}{H1 manta de silicone\\200 $\times$ 200 mm\\12 V $\cdot$ 80 W $\cdot$ 1,8 \ensuremath{\Omega}}  \node[rev] at (54,39) {D};
  \node[nmos, anchor=D] (q3) at (60,33) {}; \draw (q3.S) node[ground]{};
  \lab{64,24}{west}{Q3 IRLB8721\\8,7 m\ensuremath{\Omega} @ 4,5 V}  \node[rev] at (92,26) {D};
  \draw (q3.G) -- ++(-12,0) coordinate (g3) to[R] ++(-14,0) coordinate (t3);
  \lab{$(g3)+(-7,2.8)$}{south}{R12 150 \ensuremath{\Omega}}
  \node[redeL, anchor=east] at (t3) {HEAT\_GATE};
  \draw (g3) to[R] ++(0,-13) node[ground]{}; \fill (g3) circle (0.55);
  \lab{$(g3)+(-2,-6.5)$}{east}{R13\\10 k\ensuremath{\Omega}}
  \node[nota, anchor=north west] at (106,52) {Carga RESISTIVA: sem diodo de roda livre.\\Mesmo comando das lâmpadas (LEDC canal 1,\\mesmo timer do canal 0).\\6,7 A: Q3 dissipa $\sim$0,4 W.};
  \node[nota, anchor=north west] at (106,30) {Manta colada sob dois dissipadores\\aletados; isolante embaixo; prateleira\\perfurada por cima (nota 9).};
\end{scope}
'''

B10 = r'''% [10] CADEIA DE SEGURANCA TERMICA   (quadro 220 x 70)
\begin{scope}[shift={(185,167)}]
  \draw (80,54) -- (80,57); \node[vcc] at (80,57) {}; \lab{80,61}{south}{+12 V PROT}
  \draw (80,54) to[ncs] (80,44) to[ncs] (80,34) -- (80,32) coordinate (k1a) to[cute inductor] (80,18) coordinate (k1b) -- (80,15) node[ground]{};
  \lab{84,49}{west}{TH1 KSD301 85 °C $\cdot$ NF\\no ar, perto do teto}
  \lab{84,39}{west}{TH2 KSD301 120 °C $\cdot$ NF\\no dissipador}  \node[rev] at (72,39) {D};
  \lab{84,25}{west}{K1 relé automotivo\\12 V / 30 A (bobina)}
  \draw (k1b) -- (66,18) to[D] (66,32) -- (k1a);
  \lab{62.5,25}{east}{D5\\1N4007}  \node[rev] at (58,34) {D};
  \fill (k1a) circle (0.55); \fill (k1b) circle (0.55);
  \draw[dashed] (118,25) -- (144,25) -- (144,40.5) -- (147.5,40.5);
  \draw (150,50) -- (150,53); \node[vcc] at (150,53) {}; \lab{150,57}{south}{+12 V PROT}
  \draw (150,50) to[nos] (150,32) -- (150,24) -- (156,24);
  \lab{153,43}{west}{K1\\contato NA}
  \node[rede, anchor=west] at (156,24) {+12V\_TH};
  \node[nota, anchor=north west] at (174,58) {Qualquer termostato que abra\\solta K1: lâmpadas e manta\\ficam sem energia. Ventoinhas,\\ESP32 e display continuam.\\D5: a bobina é INDUTIVA.};
\end{scope}
'''

B6 = r'''% [6] LAMPADAS (LOW-SIDE)   (quadro 110 x 92)
\begin{scope}[shift={(185,73)}]
  \node[redeL, anchor=east] at (26,76) {+12V\_TH};
  \foreach \i in {0,...,4} {
    \draw (34,76-9*\i) to[lamp] (62,76-9*\i);
    \pgfmathtruncatemacro{\n}{\i+1}
    \node[font=\scriptsize] at (48,80.6-9*\i) {EL\n};
  }
  \foreach \i in {0,...,3} {\fill (34,76-9*\i) circle (0.55); \fill (62,76-9*\i) circle (0.55);}
  \draw (26,76) -- (34,76) -- (34,40); \draw (62,76) -- (62,30);
  \node[rev] at (70,54) {D};
  \node[nota, anchor=north west] at (70,82) {5 $\times$ W5W 12 V / 5 W\\25 W $\cdot$ 2,1 A total\\carga RESISTIVA:\\sem diodo de roda livre};
  \node[nmos, anchor=D] (q1) at (62,30) {}; \draw (q1.S) node[ground]{};
  \lab{66,21}{west}{Q1 IRLZ44N\\logic-level}
  \draw (q1.G) -- ++(-12,0) coordinate (g1) to[R] ++(-14,0) coordinate (t1);
  \lab{$(g1)+(-7,2.8)$}{south}{R6 150 \ensuremath{\Omega}}
  \node[redeL, anchor=east] at (t1) {PWM\_GATE};
  \draw (g1) to[R] ++(0,-13) node[ground]{}; \fill (g1) circle (0.55);
  \lab{$(g1)+(-2,-6.5)$}{east}{R7\\10 k\ensuremath{\Omega}}
\end{scope}
'''

B2 = r'''% [2] REGULACAO 12 V -> 5 V   (quadro 108 x 46)
\begin{scope}[shift={(297,119)}]
  \draw (14,28) -- (14,31); \node[vcc] at (14,31) {}; \lab{14,34.5}{south}{+12 V PROT}
  \draw (14,28) -- (28,28); \draw (28,10) rectangle (56,32);
  \node[font=\tiny, anchor=west] at (28.6,28) {VIN}; \node[font=\tiny, anchor=west] at (28.6,14) {GND};
  \node[font=\tiny, anchor=east] at (55.4,28) {VOUT}; \node[font=\tiny, anchor=east] at (55.4,14) {GND};
  \node[font=\scriptsize, align=center] at (42,21) {U1\\MP1584 / LM2596\\buck 12 $\rightarrow$ 5 V $\cdot$ 3 A};
  \draw (28,14) -- (22,14) -- (22,9) node[ground]{};
  \draw (56,28) -- (98,28) -- (98,31); \node[vcc] at (98,31) {}; \lab{98,34.5}{south}{+5 V}
  \draw (68,28) to[eC] (68,12);  \lab{71,20}{west}{C3\\100 \textmu F}
  \draw (84,28) to[C] (84,12);   \lab{87,20}{west}{C4\\10 \textmu F}
  \draw (56,14) -- (60,14) -- (60,12) -- (84,12); \draw (68,12) node[ground]{};
  \foreach \p in {(68,28),(84,28),(68,12)} \fill \p circle (0.55);
\end{scope}
'''

B3 = r'''% [3] CONTROLADOR - U2 ESP32 DEVKIT V1   (quadro 104 x 132)
\begin{scope}[shift={(27,148)}]
  \draw[line width=0.3mm] (28,14) rectangle (62,112);
  \node[font=\scriptsize\bfseries] at (45,116) {U2 ESP32 DevKit v1};
  \foreach \y/\p in {105/VIN, 90/3V3, 55/GND, 20/GND} {\node[font=\tiny, anchor=west] at (28.6,\y) {\p}; \draw (28,\y) -- (16,\y);}
  \draw (16,105) -- (16,108); \node[vcc] at (16,108) {}; \lab{16,111.5}{south}{+5 V}
  \draw (16,90) -- (16,93); \node[vcc] at (16,93) {}; \lab{16,96.5}{south}{+3V3}
  \draw (16,55) -- (16,51) node[ground]{}; \draw (16,20) -- (16,16) node[ground]{};
  \foreach \y/\p/\n in {105/GPIO25/PWM\_GATE, 97/GPIO27/HEAT\_GATE, 89/GPIO26/FAN\_GATE, 81/GPIO32/TEMP\_S,
                       73/GPIO34/V\_SENSE, 65/GPIO35/PWR\_OK\_S, 57/GPIO18/DISP\_CLK, 49/GPIO19/DISP\_DIO,
                       41/GPIO33/SETPOINT, 33/GPIO13/BTN\_MODE, 25/GPIO2/LED\_ST} {
    \node[font=\tiny, anchor=east] at (61.4,\y) {\p}; \draw (62,\y) -- (70,\y);
    \node[rede, anchor=west, minimum width=24mm] at (70,\y) {\n};}
  \node[nota, anchor=north west] at (6,9) {GPIO2: LED de status da placa. GPIO33 e GPIO13: reservados.};
\end{scope}
'''

B5 = r'''% [5] MEDICAO ANALOGICA   (quadro 165 x 84)
\begin{scope}[shift={(133,196)}]
  \draw (36,64) -- (36,67); \node[vcc] at (36,67) {}; \lab{36,70.5}{south}{+12 V PROT}
  \draw (36,64) to[R] (36,46) coordinate (vs) to[R] (36,28) -- (36,25) node[ground]{};
  \lab{38.5,55}{west}{R2\\100 k\ensuremath{\Omega}}  \lab{38.5,37}{west}{R3\\27 k\ensuremath{\Omega}}
  \draw (vs) -- (56,46) to[C] (56,28) -- (36,28);  \lab{58.5,37}{west}{C5\\100 nF}
  \foreach \p in {(36,46),(36,28),(56,46)} \fill \p circle (0.55);
  \draw (vs) -- (24,46); \node[redeL, anchor=east] at (24,46) {V\_SENSE};
  \node[nota, anchor=north west] at (6,16) {12,6 V $\rightarrow$ 2,68 V no ADC1.\\O ADC2 conflita com o Wi-Fi.};
  \node[redeL, anchor=east] at (100,58) {PWR\_OK (ATX)};
  \draw (100,58) to[R] (118,58) coordinate (po) -- (130,58);  \lab{109,61}{south}{R4 10 k\ensuremath{\Omega}}
  \node[rede, anchor=west] at (130,58) {PWR\_OK\_S};
  \draw (po) to[R] (118,40) -- (118,37) node[ground]{}; \fill (po) circle (0.55);
  \lab{120.5,49}{west}{R5\\20 k\ensuremath{\Omega}}
  \node[nota, anchor=north west] at (96,28) {PWR\_OK do ATX: 5 V $\rightarrow$ 3,3 V.\\Sem ATX fica em 0 V (= bateria).};
\end{scope}
'''

B4 = r'''% [4] SENSOR DE TEMPERATURA   (quadro 105 x 95)
\begin{scope}[shift={(300,185)}]
  \draw (70,30) rectangle (95,64); \node[font=\scriptsize, align=center] at (82.5,70) {TS1 LM35DZ\\10 mV/°C};
  \foreach \y/\p in {58/VS, 48/GND, 36/VOUT} {\node[font=\tiny, anchor=west] at (70.6,\y) {\p};}
  \draw (70,58) -- (44,58) -- (44,62); \node[vcc] at (44,62) {}; \lab{44,65.5}{south}{+5 V}
  \draw (56,58) to[C] (56,49) node[ground]{}; \fill (56,58) circle (0.55);  \lab{54,53.5}{east}{C8\\100 nF}
  \draw (70,48) -- (66,48) -- (66,45) node[ground]{};
  \draw (70,36) to[R] (54,36) coordinate (ts) -- (30,36);  \lab{62,39}{south}{R11 75 \ensuremath{\Omega}}
  \node[redeL, anchor=east] at (30,36) {TEMP\_S};
  \draw (ts) to[C] (54,22) node[ground]{}; \fill (ts) circle (0.55);  \lab{56,29}{west}{C9\\1 \textmu F}
  \node[nota, anchor=north west] at (8,14) {Filtro R11 + C9 do datasheet: o LM35 oscila\\com capacitor ligado direto na saída.};
\end{scope}
'''

B8 = r'''% [8] DISPLAY DE TEMPERATURA   (quadro 133 x 95)
\begin{scope}[shift={(133,99)}]
  \draw (78,22) rectangle (106,64); \node[font=\scriptsize, align=center] at (92,70) {DS1 TM1637\\4 dígitos};
  \foreach \y/\p in {58/VCC, 44/CLK, 36/DIO, 26/GND} {\node[font=\tiny, anchor=west] at (78.6,\y) {\p};}
  \draw (78,58) -- (52,58) -- (52,62); \node[vcc] at (52,62) {}; \lab{52,65.5}{south}{+3V3}
  \draw (64,58) to[C] (64,50) node[ground]{}; \fill (64,58) circle (0.55);  \lab{62,54}{east}{C10\\100 nF}
  \draw (78,44) -- (46,44); \node[redeL, anchor=east] at (46,44) {DISP\_CLK};
  \draw (78,36) -- (46,36); \node[redeL, anchor=east] at (46,36) {DISP\_DIO};
  \draw (78,26) -- (72,26) -- (72,22) node[ground]{};
  \node[nota, anchor=north west] at (8,14) {VCC em 3,3 V: o ESP32 não tolera 5 V no DIO.};
\end{scope}
'''


ICON_LEG = r'''\begin{tikzpicture}[x=1mm,y=1mm]
\node[rev] at (3,0) {D}; \node[anchor=west, font=\scriptsize] at (8,0) {alteração desta revisão};
\node[redeL, minimum width=8mm] at (6,-7) {}; \node[anchor=west, font=\scriptsize] at (16,-7) {etiqueta de rede (liga pelo nome)};
\node[ground] at (4,-12.5) {}; \node[anchor=west, font=\scriptsize] at (10,-14) {terra comum};
\draw (0,-21) -- (8,-21) (4,-21) -- (4,-18); \fill (4,-21) circle (0.55); \node[anchor=west, font=\scriptsize] at (10,-21) {junção};
\end{tikzpicture}'''


def folha1():
    s = [r'\begin{tikzpicture}[remember picture, overlay, x=1mm, y=1mm, shift={(current page.south west)}, font=\scriptsize]',
         moldura(1, 3, t['sub'][0]), revisoes()]
    for x, y, w, h, tit in [(27, 17, 156, 53, '[1] ENTRADA · SELEÇÃO DE FONTE · PROTEÇÃO'),
                            (27, 72, 156, 68, '[7] VENTILAÇÃO · EXAUSTÃO E CIRCULAÇÃO'),
                            (27, 142, 156, 66, '[9] MANTA DE AQUECIMENTO (LOW-SIDE)'),
                            (185, 60, 220, 70, '[10] CADEIA DE SEGURANÇA TÉRMICA'),
                            (185, 132, 110, 92, '[6] LÂMPADAS (LOW-SIDE)'),
                            (297, 132, 108, 46, '[2] REGULAÇÃO 12 V → 5 V')]:
        s.append(rf'\bloco{{{x}}}{{{y}}}{{{w}}}{{{h}}}{{{tex(tit)}}}')
    s += [B1, B7, B9, B10, B6, B2]
    s.append(r'\caixa{185}{17}{81}{41}{LEGENDA}{' + ICON_LEG + '}')
    alim = tabela(t['alim_h'], t['alim'], r'|p{18mm}|X|X|p{18mm}|')
    s.append(r'\caixa{27}{210}{156}{70}{' + tex(t['alim_t']) + '}{' + alim + r'\\[1.5mm]' + tex(t['fonte']) + '}')
    fl = r'\begin{enumerate}\setlength{\itemsep}{1mm}' + ''.join(r'\item ' + tex(x) for x in t['folhas']) + r'\end{enumerate}'
    s.append(r'\caixa{297}{180}{108}{42}{' + tex(t['folhas_t']) + '}{' + fl + '}')
    fios = tabela(t['fios_h'], t['fios'], r'|X|p{13mm}|')
    s.append(r'\caixa{185}{226}{81}{54}{' + tex(t['fios_t']) + '}{' + fios + '}')
    s.append(r'\end{tikzpicture}\null\newpage')
    return '\n'.join(s)


def folha2():
    s = [r'\begin{tikzpicture}[remember picture, overlay, x=1mm, y=1mm, shift={(current page.south west)}, font=\scriptsize]',
         moldura(2, 3, t['sub'][1])]
    for x, y, w, h, tit in [(27, 17, 104, 132, '[3] CONTROLADOR'), (133, 17, 165, 84, '[5] MEDIÇÃO ANALÓGICA'),
                            (300, 17, 105, 95, '[4] SENSOR DE TEMPERATURA'), (133, 103, 133, 95, '[8] DISPLAY DE TEMPERATURA')]:
        s.append(rf'\bloco{{{x}}}{{{y}}}{{{w}}}{{{h}}}{{{tex(tit)}}}')
    s += [B3, B5, B4, B8]
    ng = r'\begin{enumerate}\setlength{\itemsep}{1.2mm}' + ''.join(r'\item ' + tex(x) for x in t['ng']) + r'\end{enumerate}'
    s.append(r'\caixa{268}{114}{137}{108}{' + tex(t['notas_gerais']) + '}{\\footnotesize ' + ng + '}')
    s.append(r'\caixa{27}{151}{104}{47}{LEGENDA}{' + ICON_LEG + '}')
    s.append(r'\caixa{27}{200}{239}{80}{' + tex(t['redes_t']) + '}{' +
             tabela(t['redes_h'], REDES, r'|p{36mm}|p{58mm}|X|p{18mm}|') + '}')
    s.append(r'\end{tikzpicture}\null\newpage')
    return '\n'.join(s)


def folha3():
    s = [r'\begin{tikzpicture}[remember picture, overlay, x=1mm, y=1mm, shift={(current page.south west)}, font=\scriptsize]',
         moldura(3, 3, t['sub'][2])]
    pin = [(p, r, tp, fp, ('△' + rv) if rv == REV else rv) for p, r, tp, te, fp, fe, rv in PINOS]
    pin_t = tabela((t['pino'], t['rede'], t['tipo'], t['funcao'], t['rev']), pin, r'|p{15mm}|p{22mm}|p{17mm}|X|p{8mm}|')
    notas = r'\begin{enumerate}\setlength{\itemsep}{0.9mm}' + ''.join(
        rf'\item \textbf{{{tex(a)}}} {tex(b)}' for a, b in NOTAS['pt']) + r'\end{enumerate}'
    s.append(r'\node[anchor=north west, inner sep=0] at (27,279) {\begin{minipage}[t]{190mm}\footnotesize'
             r'{\normalsize\bfseries ' + tex(t['pin_t']) + r'}\\[-1mm]\rule{190mm}{0.4mm}\\[1mm]' + pin_t +
             r'\\[4mm]{\normalsize\bfseries ' + tex(t['notas_t']) + r'}\\[-1mm]\rule{190mm}{0.4mm}' + notas + r'\end{minipage}};')
    bom = [(i + 1, r, q, dp, ep, ('△' + rv) if rv == REV else rv) for i, (r, q, dp, de, ep, ee, rv) in enumerate(BOM)]
    bom_t = tabela((t['item'], t['ref'], t['qtd'], t['descr'], t['espec'], t['rev']), bom,
                   r'|p{6mm}|p{24mm}|p{7mm}|X|p{31mm}|p{8mm}|')
    s.append(r'\node[anchor=north west, inner sep=0] at (223,279) {\begin{minipage}[t]{180mm}\footnotesize'
             r'{\normalsize\bfseries ' + tex(t['bom_t']) + r'}\\[-1mm]\rule{180mm}{0.4mm}\\[1mm]' + bom_t +
             r'\\[1mm]' + tex(t['bom_obs']) + r'\end{minipage}};')
    s.append(r'\end{tikzpicture}\null')
    return '\n'.join(s)


doc = PRE + r'\begin{document}' + '\n' + folha1() + '\n' + folha2() + '\n' + folha3() + '\n' + r'\end{document}' + '\n'
open(sys.argv[1] if len(sys.argv) > 1 else 'esquema_eletrico.tex', 'w', encoding='utf-8').write(doc)
print('ok')
