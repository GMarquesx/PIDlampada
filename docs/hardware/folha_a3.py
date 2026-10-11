"""
Folha de desenho A3 paisagem no padrao de prancha de engenharia: moldura com
zonas (1-8 / A-F), marcas de centro, carimbo e tabela de revisoes.

Usado por esquema_eletrico.py (PIDL-ESQ-001) e desenho_mecanico.py
(PIDL-MEC-001). Tudo em mm; o HTML vira PDF pelo Chromium (playwright).
"""
import html
import os
import re

W, H = 420.0, 297.0
BX0, BY0, BX1, BY1 = 20.0, 10.0, 410.0, 287.0          # borda
FX0, FY0, FX1, FY1 = 25.0, 15.0, 405.0, 282.0          # quadro interno (zonas por fora)
NCOL, NLIN = 8, 6
TB = (268.0, 224.0, 137.0, 58.0)                        # carimbo
RT = (268.0, 15.0, 137.0)                               # tabela de revisoes (x, y, largura)

AUTOR = 'Gabriel Marques'
SIGLA = 'GM'

esc = html.escape

ROTULOS = {
    'pt': dict(nome='NOME', sigla='SIGLA', data='DATA', elab='ELABORADO', aprov='APROVADO',
               n_des='Nº DO DESENHO', rev='REV.', folha='FOLHA', escala='ESCALA', formato='FORMATO',
               projeto='PROJETO', revisoes='REVISÕES', desc='DESCRIÇÃO', resp='RESP.',
               inst='UNIP · ENGENHARIA DE COMPUTAÇÃO · PROJETO INTEGRADOR 2026', local='SÃO JOSÉ DOS CAMPOS - SP'),
    'en': dict(nome='NAME', sigla='INIT.', data='DATE', elab='DRAWN', aprov='APPROVED',
               n_des='DRAWING No.', rev='REV.', folha='SHEET', escala='SCALE', formato='SIZE',
               projeto='PROJECT', revisoes='REVISIONS', desc='DESCRIPTION', resp='BY',
               inst='UNIP · COMPUTER ENGINEERING · CAPSTONE PROJECT 2026', local='SÃO JOSÉ DOS CAMPOS - SP · BRAZIL'),
}


def borda(folha_txt, des, rev):
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
    s.append(f'<text x="{BX0}" y="{BY1 + 6}" class="foot">{esc(des)} · REV. {rev} · {esc(folha_txt)}</text>')
    s.append('</svg>')
    return ''.join(s)


def carimbo(lang, des, rev, data, folha, total, titulo, subtitulo, escala):
    r = ROTULOS[lang]
    x, y, w, h = TB
    return f'''
<div class="tb" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm">
  <table class="sign">
    <tr><th style="width:24mm"></th><th>{r['nome']}</th><th style="width:16mm">{r['sigla']}</th><th style="width:24mm">{r['data']}</th></tr>
    <tr><td class="k">{r['elab']}</td><td>{AUTOR}</td><td class="c">{SIGLA}</td><td class="c">{data}</td></tr>
    <tr><td class="k">{r['aprov']}</td><td>{AUTOR}</td><td class="c">{SIGLA}</td><td class="c">{data}</td></tr>
  </table>
  <div class="ttl">
    <div class="lbl">{r['projeto']} PIDlampada</div>
    <div class="t1">{esc(titulo)}</div>
    <div class="t2">{esc(subtitulo)}</div>
  </div>
  <div class="inst"><span>{r['inst']}</span><span>{r['local']}</span></div>
  <table class="fld">
    <tr>
      <td style="width:38mm"><div class="lbl">{r['n_des']}</div><div class="v big">{des}</div></td>
      <td style="width:14mm"><div class="lbl">{r['rev']}</div><div class="v big c">{rev}</div></td>
      <td style="width:18mm"><div class="lbl">{r['folha']}</div><div class="v c">{folha} / {total}</div></td>
      <td style="width:18mm"><div class="lbl">{r['escala']}</div><div class="v c">{escala}</div></td>
      <td style="width:16mm"><div class="lbl">{r['formato']}</div><div class="v c">A3</div></td>
      <td><div class="lbl">{r['data']}</div><div class="v c">{data}</div></td>
    </tr>
  </table>
</div>'''


def tabela_revisoes(lang, linhas):
    """linhas: [(rev, descricao, data)]"""
    r = ROTULOS[lang]
    x, y, w = RT
    corpo = ''.join(f'<tr><td class="c b">{rv}</td><td>{esc(dsc)}</td><td class="c">{dt}</td><td class="c">{SIGLA}</td></tr>'
                    for rv, dsc, dt in linhas)
    return f'''
<div class="rt" style="left:{x}mm;top:{y}mm;width:{w}mm">
  <table>
    <tr><th colspan="4" class="cap">{r['revisoes']}</th></tr>
    <tr><th style="width:10mm">{r['rev']}</th><th>{r['desc']}</th><th style="width:20mm">{r['data']}</th><th style="width:12mm">{r['resp']}</th></tr>
    {corpo}
  </table>
</div>'''


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


def svg_inline(caminho, k):
    s = open(caminho, encoding='utf-8').read()
    s = re.sub(r'<\?xml[^>]*>', '', s)
    m = re.search(r'viewBox="([-\d.e]+) ([-\d.e]+) ([-\d.e]+) ([-\d.e]+)"', s)
    vw, vh = float(m.group(3)), float(m.group(4))
    wmm, hmm = vw / 36 * k, vh / 36 * k
    s = re.sub(r'height="[^"]*pt"', f'height="{hmm:.2f}mm"', s, count=1)
    s = re.sub(r'width="[^"]*pt"', f'width="{wmm:.2f}mm"', s, count=1)
    return s, wmm, hmm



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
.notes .legline { position: absolute; left: 3mm; right: 3mm; top: 9mm; display: flex; justify-content: space-between; align-items: center; font-size: 2.4mm; }
.notes .legline .li { display: flex; align-items: center; gap: 1.2mm; }
.notes .verf2 { position: absolute; right: 3mm; top: 2mm; font-size: 2.3mm; color: #333; }
.s2.ngs ol { margin: 0; padding-left: 6mm; font-size: 2.6mm; line-height: 1.35; }
.s2 .h3 { font-size: 2.9mm; font-weight: bold; letter-spacing: 0.05em; margin: 2.5mm 0 1.2mm; }
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
.s2col { position: absolute; display: flex; flex-direction: column; gap: 5mm; }
.s2col .s2 { position: static; }
.s2 { position: absolute; }
.s2 .h2 { font-size: 3.2mm; font-weight: bold; letter-spacing: 0.06em; border-bottom: 0.5mm solid #000; padding-bottom: 0.8mm; margin-bottom: 1.5mm; }
.s2 th, .s2 td { border: 0.25mm solid #000; font-size: 2.5mm; padding: 0.7mm 1.4mm; text-align: left; vertical-align: top; }
.s2 th { font-size: 2.2mm; background: #eee; }
.s2 td.c, .s2 th.c { text-align: center; }
.s2 .mono { font-family: "DejaVu Sans Mono", Consolas, monospace; font-size: 2.3mm; }
.s2.nts ol { margin: 0; padding-left: 6mm; font-size: 2.6mm; line-height: 1.35; }
.s2.nts li { margin-bottom: 0.9mm; }
.s2 .rem { font-size: 2.4mm; margin: 1.6mm 0 0; }

'''
