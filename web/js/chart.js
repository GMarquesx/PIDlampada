/*
 * Grafico de historico em canvas, sem dependencias.
 *
 * Dois paineis com o mesmo eixo de tempo - nunca dois eixos y no mesmo
 * grafico: em cima temperatura e alvo (ambos em degC), embaixo os atuadores
 * num eixo so de -100 a +100 %: lampadas para cima (aquecer), cooler para
 * baixo (exaurir). E' o mesmo u do split-range do firmware, entao os dois
 * nunca aparecem juntos. Crosshair e tooltip ao passar o dedo ou o mouse.
 */

const COLORS = {
  temp: '#D37B0D',
  target: '#28A0C7',
  fan: '#8B7CF0',
  grid: '#24313D',
  axis: '#8C9BA8',
  ink: '#E6EDF2',
  surface: '#121A22',
};

const fmt = (x, d = 1) => x.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

export class TrendChart {
  constructor(host, { capacity = 180 } = {}) {
    this.host = host;
    this.capacity = capacity;
    this.data = [];
    this.hover = -1;

    this.canvas = document.createElement('canvas');
    this.canvas.setAttribute('aria-hidden', 'true');
    this.ctx = this.canvas.getContext('2d');
    this.tip = document.createElement('div');
    this.tip.className = 'chart__tip';
    this.tip.hidden = true;
    this.empty = document.createElement('p');
    this.empty.className = 'chart__empty';
    this.empty.textContent = 'O histórico aparece assim que a câmara enviar leituras.';
    host.append(this.canvas, this.tip, this.empty);

    new ResizeObserver(() => this.#resize()).observe(host);
    this.#resize();

    const move = (ev) => {
      const r = this.canvas.getBoundingClientRect();
      this.#setHover(ev.clientX - r.left);
    };
    this.canvas.addEventListener('pointermove', move);
    this.canvas.addEventListener('pointerdown', move);
    this.canvas.addEventListener('pointerleave', () => { this.hover = -1; this.tip.hidden = true; this.draw(); });

    if (document.fonts) document.fonts.ready.then(() => this.draw());
  }

  clear() { this.data = []; this.hover = -1; this.tip.hidden = true; this.draw(); }

  push(sample) {
    const last = this.data[this.data.length - 1];
    // o firmware zera o tempo no ensaio de degrau: comeca um historico novo
    if (last && sample.t < last.t) this.data = [];
    this.data.push(sample);
    if (this.data.length > this.capacity) this.data.shift();
    this.draw();
    if (this.hover >= 0) this.#updateTip();
  }

  #resize() {
    const r = this.host.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.w = Math.max(200, r.width);
    this.h = Math.max(160, r.height);
    this.canvas.width = Math.round(this.w * dpr);
    this.canvas.height = Math.round(this.h * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.draw();
  }

  #layout() {
    const left = 40, right = 78, top = 8, gap = 26, bottom = 22;
    const dutyH = Math.round((this.h - top - gap - bottom) * 0.36);
    const tempH = this.h - top - gap - bottom - dutyH;
    return {
      x0: left, x1: this.w - right,
      temp: { y0: top, y1: top + tempH },
      duty: { y0: top + tempH + gap, y1: top + tempH + gap + dutyH },
      axisY: this.h - 4,
    };
  }

  #xScale(L) {
    const d = this.data;
    const t0 = d[0].t, t1 = Math.max(d[d.length - 1].t, t0 + 60);
    return (t) => L.x0 + ((t - t0) / (t1 - t0)) * (L.x1 - L.x0);
  }

  #tempDomain() {
    let lo = Infinity, hi = -Infinity;
    for (const s of this.data) {
      lo = Math.min(lo, s.T, s.sp);
      hi = Math.max(hi, s.T, s.sp);
    }
    lo = Math.floor((lo - 1) / 5) * 5;
    hi = Math.ceil((hi + 1) / 5) * 5;
    if (hi - lo < 10) hi = lo + 10;
    return [lo, hi];
  }

  draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.w, this.h);
    this.empty.hidden = this.data.length > 0;
    if (this.data.length < 2) return;

    const L = this.#layout();
    const X = this.#xScale(L);
    const [lo, hi] = this.#tempDomain();
    const YT = (v) => L.temp.y1 - ((v - lo) / (hi - lo)) * (L.temp.y1 - L.temp.y0);
    // -1 (cooler 100 %) embaixo, +1 (lampadas 100 %) em cima
    const YD = (v) => L.duty.y1 - ((v + 1) / 2) * (L.duty.y1 - L.duty.y0);

    ctx.font = '500 12px "Barlow", system-ui, sans-serif';
    ctx.textBaseline = 'middle';

    // grade e rotulos de temperatura
    ctx.lineWidth = 1;
    for (let v = lo; v <= hi; v += 5) {
      const y = Math.round(YT(v)) + 0.5;
      ctx.strokeStyle = COLORS.grid;
      ctx.beginPath(); ctx.moveTo(L.x0, y); ctx.lineTo(L.x1, y); ctx.stroke();
      ctx.fillStyle = COLORS.axis;
      ctx.textAlign = 'right';
      ctx.fillText(`${v}°`, L.x0 - 6, y);
    }

    // painel dos atuadores
    for (const v of [-1, 0, 1]) {
      const y = Math.round(YD(v)) + 0.5;
      ctx.strokeStyle = v === 0 ? COLORS.axis : COLORS.grid;
      ctx.globalAlpha = v === 0 ? 0.5 : 1;
      ctx.beginPath(); ctx.moveTo(L.x0, y); ctx.lineTo(L.x1, y); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.fillStyle = COLORS.axis;
    ctx.textAlign = 'right';
    ctx.fillText('100', L.x0 - 6, YD(1));
    ctx.fillText('0', L.x0 - 6, YD(0));
    ctx.fillText('100', L.x0 - 6, YD(-1));
    ctx.textAlign = 'left';
    ctx.fillText('▲ Lâmpadas  ·  ▼ Cooler  (%)', L.x0 + 2, L.duty.y0 - 10);

    // eixo x: minutos de modelo
    const d = this.data;
    const spanMin = Math.max(1, (d[d.length - 1].t - d[0].t) / 60);
    // passo escolhido pela largura em pixels: rotulo a cada >= 64 px
    const pxPerMin = (L.x1 - L.x0) / spanMin;
    const stepMin = [1, 2, 5, 10, 15, 30, 60, 120].find((m) => m * pxPerMin >= 64) || 240;
    ctx.textAlign = 'center';
    const firstMin = Math.ceil(d[0].t / 60 / stepMin) * stepMin;
    for (let m = firstMin; m * 60 <= d[d.length - 1].t; m += stepMin) {
      ctx.fillStyle = COLORS.axis;
      ctx.fillText(`${m} min`, X(m * 60), L.axisY - 6);
    }

    // areas dos atuadores: lampadas acima do zero, cooler abaixo
    this.#area(d, X, (s) => YD(s.u), YD(0), 'rgba(211, 123, 13, 0.22)');
    this.#line(d, (s) => X(s.t), (s) => YD(s.u), COLORS.temp, []);
    if (d.some((s) => (s.fan ?? 0) > 0)) {
      this.#area(d, X, (s) => YD(-(s.fan ?? 0)), YD(0), 'rgba(139, 124, 240, 0.28)');
      this.#line(d, (s) => X(s.t), (s) => YD(-(s.fan ?? 0)), COLORS.fan, []);
    }

    // alvo (tracejado = codificacao secundaria, nao depende so da cor)
    this.#line(d, (s) => X(s.t), (s) => YT(s.sp), COLORS.target, [6, 4]);
    // temperatura
    this.#line(d, (s) => X(s.t), (s) => YT(s.T), COLORS.temp, []);

    // rotulos diretos na ponta das linhas
    const last = d[d.length - 1];
    this.#endLabel(X(last.t), YT(last.T), `${fmt(last.T)}°`, COLORS.temp, YT(last.sp));
    ctx.textAlign = 'left';
    ctx.fillStyle = COLORS.axis;
    ctx.fillText(`alvo ${fmt(last.sp)}°`, X(last.t) + 8, YT(last.sp) + (YT(last.sp) > YT(last.T) ? 12 : -12));

    // crosshair
    if (this.hover >= 0 && this.hover < d.length) {
      const s = d[this.hover];
      const x = Math.round(X(s.t)) + 0.5;
      ctx.strokeStyle = 'rgba(230, 237, 242, 0.35)';
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(x, L.temp.y0); ctx.lineTo(x, L.duty.y1); ctx.stroke();
      this.#dot(x, YT(s.T), COLORS.temp);
      this.#dot(x, YT(s.sp), COLORS.target);
      if ((s.fan ?? 0) > 0) this.#dot(x, YD(-s.fan), COLORS.fan);
      else this.#dot(x, YD(s.u), COLORS.temp);
    }
  }

  #area(d, X, fy, yBase, fill) {
    const ctx = this.ctx;
    ctx.beginPath();
    d.forEach((s, i) => (i ? ctx.lineTo(X(s.t), fy(s)) : ctx.moveTo(X(s.t), fy(s))));
    ctx.lineTo(X(d[d.length - 1].t), yBase);
    ctx.lineTo(X(d[0].t), yBase);
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
  }

  #line(d, fx, fy, color, dash) {
    const ctx = this.ctx;
    ctx.save();
    ctx.setLineDash(dash);
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.strokeStyle = color;
    ctx.beginPath();
    d.forEach((s, i) => (i ? ctx.lineTo(fx(s), fy(s)) : ctx.moveTo(fx(s), fy(s))));
    ctx.stroke();
    ctx.restore();
  }

  #dot(x, y, color) {
    const ctx = this.ctx;
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = COLORS.surface;
    ctx.stroke();
  }

  #endLabel(x, y, text, color, avoidY) {
    this.#dot(x, y, color);
    const ctx = this.ctx;
    ctx.font = '600 13px "Barlow Semi Condensed", "Barlow", system-ui, sans-serif';
    ctx.fillStyle = COLORS.ink;
    ctx.textAlign = 'left';
    const off = Math.abs(y - avoidY) < 14 ? (y <= avoidY ? -10 : 10) : 0;
    ctx.fillText(text, x + 8, y + off);
    ctx.font = '500 12px "Barlow", system-ui, sans-serif';
  }

  #setHover(px) {
    if (this.data.length < 2) return;
    const L = this.#layout();
    const X = this.#xScale(L);
    let best = 0, bestD = Infinity;
    this.data.forEach((s, i) => {
      const dd = Math.abs(X(s.t) - px);
      if (dd < bestD) { bestD = dd; best = i; }
    });
    this.hover = best;
    this.draw();
    this.#updateTip();
  }

  #updateTip() {
    const s = this.data[this.hover];
    if (!s) return;
    const L = this.#layout();
    const X = this.#xScale(L);
    this.tip.innerHTML =
      `<span>${fmt(s.t / 60, 0)} min</span><br>` +
      `<b>${fmt(s.T)} °C</b> medido<br>` +
      `${fmt(s.sp)} °C alvo<br>` +
      `${fmt(s.u * 100, 0)} % lâmpadas<br>` +
      `${fmt((s.fan ?? 0) * 100, 0)} % cooler`;
    this.tip.hidden = false;
    const x = Math.min(Math.max(X(s.t), 70), this.w - 70);
    this.tip.style.left = `${x}px`;
  }
}
