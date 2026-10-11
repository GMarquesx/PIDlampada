"""
Esquema eletrico - PIDlampada - desenho PIDL-ESQ-001, A3 paisagem, 3 folhas.
Revisao atual: D.

  folha 1: potencia - blocos [1] [2] [6] [7] [9] [10], redes de alimentacao,
           legenda, indice de folhas, tabela de revisoes e carimbo
  folha 2: controle e medicao - blocos [3] [4] [5] [8], notas gerais,
           interligacao das redes entre folhas
  folha 3: pinagem do U2, notas de projeto e lista de materiais

Gera as versoes em portugues e em ingles.

Uso:
    pip install schemdraw playwright
    python -m playwright install chromium
    python docs/hardware/esquema_eletrico.py

Saida (em docs/hardware/):
    Esquema_Eletrico_Rev_D.pdf          portugues
    Electrical_Schematic_Rev_D_EN.pdf   ingles
    build/                              HTML e SVG intermediarios

Sem o playwright, abra build/esquema_pt.html no navegador e imprima em PDF
(A3 paisagem, margens "nenhuma").

Nova revisao: acrescente a linha em esquema_dados.REVISOES, mude REV e DATA,
mude REV_ATUAL em esquema_blocos.py e marque o que mudou com rev(d, (x, y), 'E').
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import esquema_blocos as B           # noqa: E402
import folha_a3 as F                 # noqa: E402
from folha_a3 import esc             # noqa: E402
from esquema_dados import DES, REV, DATA, REVISOES, TXT, REDES, PINOS, NOTAS, BOM   # noqa: E402

BUILD = os.path.join(AQUI, 'build')
TOTAL = 3
TITULO_H, PAD = 7.0, 2.0

# quadro de cada bloco: (x, y, largura, altura) em mm
QUADROS_1 = {
    '1': (27, 17, 156, 53),
    '7': (27, 72, 156, 68),
    '9': (27, 142, 156, 66),
    '10': (185, 60, 220, 70),
    '6': (185, 132, 110, 92),
    '2': (297, 132, 108, 46),
}
QUADROS_2 = {
    '3': (27, 17, 104, 132),
    '5': (133, 17, 165, 84),
    '4': (300, 17, 105, 95),
    '8': (133, 103, 133, 95),
}

ICONES = [
    '<polygon points="1,8 9,8 5,1.2" fill="none" stroke="#000" stroke-width="0.35"/>'
    f'<text x="5" y="7" font-size="3.4" text-anchor="middle">{REV}</text>',
    '<polygon points="0.5,2.5 8,2.5 10,4.5 8,6.5 0.5,6.5" fill="none" stroke="#000" stroke-width="0.35"/>',
    '<line x1="5" y1="0.5" x2="5" y2="3.5" stroke="#000" stroke-width="0.35"/>'
    '<line x1="2" y1="3.5" x2="8" y2="3.5" stroke="#000" stroke-width="0.35"/>'
    '<line x1="3.2" y1="5" x2="6.8" y2="5" stroke="#000" stroke-width="0.35"/>'
    '<line x1="4.3" y1="6.5" x2="5.7" y2="6.5" stroke="#000" stroke-width="0.35"/>',
    '<line x1="0.5" y1="5" x2="9.5" y2="5" stroke="#000" stroke-width="0.35"/>'
    '<line x1="5" y1="1" x2="5" y2="5" stroke="#000" stroke-width="0.35"/><circle cx="5" cy="5" r="0.9"/>',
]


# ------------------------------------------------------------------ pecas
def caixa(x, y, w, h, titulo, corpo, cls=''):
    return (f'<div class="blk box {cls}" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">'
            f'<div class="bt">{esc(titulo)}</div><div class="boxbody">{corpo}</div></div>')


def legenda(t, vertical=False):
    itens = ''.join(f'<span class="li"><svg viewBox="0 0 10 9" width="10mm" height="9mm">{ic}</svg>{esc(txt)}</span>'
                    for ic, txt in zip(ICONES, t['leg']))
    return f'<div class="legline{" vert" if vertical else ""}">{itens}</div>'


def tabela(cab, linhas, larguras=None, cls='grid'):
    larguras = larguras or [None] * len(cab)
    th = ''.join(f'<th{f" style=\"width:{w}mm\"" if w else ""}>{esc(c)}</th>' for c, w in zip(cab, larguras))
    tr = ''.join('<tr>' + ''.join(f'<td>{esc(str(c))}</td>' for c in lin) + '</tr>' for lin in linhas)
    return f'<table class="{cls}"><tr>{th}</tr>{tr}</table>'


def marca(rv):
    return f'△{rv}' if rv == REV else rv


def escala(info, quadros):
    """A maior escala (ate a nominal) que faz todos os blocos da folha caberem nos quadros."""
    k = B.ESCALA_MM
    for n, (x, y, w, h) in quadros.items():
        _, bw, bh = info[n]
        k = min(k, (w - 2 * PAD) / (bw / B.ESCALA_MM), (h - TITULO_H - PAD) / (bh / B.ESCALA_MM))
    return k


def blocos(quadros, info, k, lang):
    out = []
    for n, (x, y, w, h) in quadros.items():
        svg, wmm, hmm = F.svg_inline(os.path.join(BUILD, lang, f'bloco_{n}.svg'), k)
        cx = x + (w - wmm) / 2
        cy = y + TITULO_H + (h - TITULO_H - hmm) / 2
        out.append(f'<div class="blk" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">'
                   f'<div class="bt">[{n}]&nbsp; {esc(info[n][0])}</div></div>')
        out.append(f'<div class="svgbox" style="left:{cx:.2f}mm;top:{cy:.2f}mm">{svg}</div>')
    return out


def folha_txt(t, n):
    return f'{t["folha"]} {n}/{TOTAL}'


def escala_txt(t, k):
    return t['escala']


# ------------------------------------------------------------------ folhas
def folha1(t, lang, info, k):
    out = [f'<section class="sheet">{F.borda(folha_txt(t, 1), DES, REV)}']
    out += blocos(QUADROS_1, info, k, lang)
    corpo = tabela(t['alim_h'], t['alim'], [24, 52, None, 24]) + f'<p class="rem">{esc(t["fonte"])}</p>'
    out.append(caixa(27, 210, 156, 70, t['alim_t'], corpo))
    out.append(caixa(185, 17, 81, 41, t['legenda'], legenda(t, vertical=True), 'leg'))
    fl = ''.join(f'<li>{esc(s)}</li>' for s in t['folhas'])
    out.append(caixa(297, 180, 108, 42, t['folhas_t'], f'<ol class="folhas">{fl}</ol>'))
    out.append(caixa(185, 226, 81, 54, t['fios_t'], tabela(t['fios_h'], t['fios'], [None, 15])))
    out.append(F.tabela_revisoes(lang, REVISOES[lang]))
    out.append(F.carimbo(lang, DES, REV, DATA, 1, TOTAL, t['titulo'], t['sub'][0], escala_txt(t, k)))
    out.append('</section>')
    return ''.join(out)


def folha2(t, lang, info, k):
    out = [f'<section class="sheet">{F.borda(folha_txt(t, 2), DES, REV)}']
    out += blocos(QUADROS_2, info, k, lang)
    ng = ''.join(f'<li>{esc(n)}</li>' for n in t['ng'])
    out.append(caixa(268, 114, 137, 108, t['notas_gerais'], f'<ol class="ng">{ng}</ol>'))
    out.append(caixa(27, 151, 104, 47, t['legenda'], legenda(t, vertical=True), 'leg'))
    out.append(caixa(27, 200, 239, 80, t['redes_t'], tabela(t['redes_h'], REDES, [40, 62, None, 22])))
    out.append(F.carimbo(lang, DES, REV, DATA, 2, TOTAL, t['titulo'], t['sub'][1], escala_txt(t, k)))
    out.append('</section>')
    return ''.join(out)


def folha3(t, lang):
    pt = lang == 'pt'
    out = [f'<section class="sheet f3">{F.borda(folha_txt(t, 3), DES, REV)}']
    lin = ''.join(
        f'<tr><td class="b">{p}</td><td class="mono">{r}</td><td>{tp if pt else te}</td>'
        f'<td>{esc(fp if pt else fe)}</td><td class="c">{marca(rv)}</td></tr>'
        for p, r, tp, te, fp, fe, rv in PINOS)
    out.append('<div class="s2col" style="left:27mm;top:18mm;width:190mm">')
    out.append(f'''<div class="s2 pin">
      <div class="h2">{t['pin_t']}</div>
      <table><tr><th style="width:17mm">{t['pino']}</th><th style="width:24mm">{t['rede']}</th>
      <th style="width:21mm">{t['tipo']}</th><th>{t['funcao']}</th><th style="width:11mm">{t['rev']}</th></tr>{lin}</table>
    </div>''')
    notas = ''.join(f'<li><b>{esc(a)}</b> {esc(b)}</li>' for a, b in NOTAS[lang])
    out.append(f'<div class="s2 nts"><div class="h2">{t["notas_t"]}</div><ol>{notas}</ol></div></div>')
    linhas = ''.join(
        f'<tr><td class="c">{i + 1}</td><td class="b">{r}</td><td class="c">{q}</td>'
        f'<td>{esc(dp if pt else de)}</td><td>{esc(ep if pt else ee)}</td><td class="c">{marca(rv)}</td></tr>'
        for i, (r, q, dp, de, ep, ee, rv) in enumerate(BOM))
    out.append(f'''<div class="s2 bom" style="left:223mm;top:18mm;width:180mm">
      <div class="h2">{t['bom_t']}</div>
      <table><tr><th style="width:8mm">{t['item']}</th><th style="width:36mm">{t['ref']}</th><th style="width:9mm">{t['qtd']}</th>
      <th>{t['descr']}</th><th style="width:36mm">{t['espec']}</th><th style="width:10mm">{t['rev']}</th></tr>{linhas}</table>
      <p class="rem">{esc(t['bom_obs'])}</p>
    </div>''')
    out.append(F.carimbo(lang, DES, REV, DATA, 3, TOTAL, t['titulo'], t['sub'][2], t['escala']))
    out.append('</section>')
    return ''.join(out)


CSS_EXTRA = '''
.box .boxbody { position: absolute; top: 8.5mm; left: 3mm; right: 3mm; bottom: 2mm; overflow: hidden; }
table.grid th, table.grid td { border: 0.25mm solid #000; font-size: 2.35mm; padding: 0.7mm 1.2mm;
  text-align: left; vertical-align: top; }
table.grid th { font-size: 2.1mm; background: #eee; }
.box .rem { font-size: 2.35mm; margin: 1.6mm 0 0; }
ol.ng, ol.folhas { margin: 0; padding-left: 5mm; font-size: 2.55mm; line-height: 1.35; }
ol.ng li { margin-bottom: 1mm; }
ol.folhas li { margin-bottom: 1.6mm; }
.legline { display: flex; justify-content: space-between; align-items: center; font-size: 2.4mm; }
.legline .li { display: flex; align-items: center; gap: 1.2mm; }
.legline.vert { flex-direction: column; align-items: flex-start; gap: 0; }
.legline.vert svg { height: 6.6mm; }
.legline.vert { font-size: 2.3mm; }
.rt th, .rt td { font-size: 2.2mm; padding: 0.55mm 1.1mm; }
.s2 th, .s2 td { font-size: 2.4mm; padding: 0.6mm 1.3mm; }
.s2.nts ol { font-size: 2.5mm; line-height: 1.32; }
.f3 .s2 th, .f3 .s2 td { font-size: 2.75mm; padding: 0.75mm 1.4mm; }
.f3 .s2 th { font-size: 2.4mm; }
.f3 .s2 .mono { font-size: 2.55mm; }
.f3 .s2.nts ol { font-size: 2.85mm; line-height: 1.34; }
.f3 .s2 .h2 { font-size: 3.5mm; }
.f3 .s2 .rem { font-size: 2.6mm; }
ol.ng { font-size: 2.85mm; }
ol.ng li { margin-bottom: 1.6mm; }
'''


def gerar_html(lang):
    t = TXT[lang]
    info = B.gerar(os.path.join(BUILD, lang), lang=lang)
    k1, k2 = escala(info, QUADROS_1), escala(info, QUADROS_2)
    corpo = folha1(t, lang, info, k1) + folha2(t, lang, info, k2) + folha3(t, lang)
    doc = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{DES} rev {REV}</title>'
           f'<style>{F.CSS}{CSS_EXTRA}</style></head><body>{corpo}</body></html>')
    caminho = os.path.join(BUILD, f'esquema_{lang}.html')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(doc)
    print(f'{lang}: escala {k1:.2f} / {k2:.2f} mm/unidade -> {caminho}')
    return caminho, t['arquivo']


if __name__ == '__main__':
    os.makedirs(BUILD, exist_ok=True)
    for lang in ('pt', 'en'):
        h, nome = gerar_html(lang)
        F.pdf(h, os.path.join(AQUI, nome))
