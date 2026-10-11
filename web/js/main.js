/*
 * Painel PIDlampada - liga a interface a camara (MQTT ou demonstracao).
 *
 * Parametros de URL, uteis para mandar o link na apresentacao:
 *   ?demo=1                      abre direto no modo demonstracao
 *   ?id=gmarques-01              ID da camara (MQTT_DEVICE_ID do firmware)
 *   ?broker=wss://host:porta/mqtt
 */

import { Link } from './link.js';
import { TrendChart } from './chart.js';
import { temperatureCells, errorCells, batteryCells, cellsKey } from './seg7.js';

const DEFAULTS = {
  broker: 'wss://broker.hivemq.com:8884/mqtt',
  device: 'gmarques-01',
};
const SP_MIN = 25, SP_MAX = 70;

const $ = (id) => document.getElementById(id);
const fmt = (x, d = 1) => Number(x).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });

// ------------------------------------------------------------- preferencias
const store = {
  get(k, fallback) { try { return localStorage.getItem(`pidlampada.${k}`) ?? fallback; } catch { return fallback; } },
  set(k, v) { try { localStorage.setItem(`pidlampada.${k}`, v); } catch { /* modo privado */ } },
};

const params = new URLSearchParams(location.search);
const config = {
  broker: params.get('broker') || store.get('broker', DEFAULTS.broker),
  device: params.get('id') || store.get('device', DEFAULTS.device),
  demo: params.get('demo') === '1' || (!params.has('id') && store.get('demo', '0') === '1'),
};

// ------------------------------------------------------------------ estado
const link = new Link();
const chart = new TrendChart($('chart'));
let scene = null;
let last = null;            // ultima telemetria
let spPending = null;       // valor escolhido no slider ainda nao confirmado
let spTimer = null;
const tableRows = [];

// A cena 3D carrega em paralelo: se o CDN do three.js falhar, o resto segue.
import('./scene.js')
  .then(({ ChamberScene }) => {
    scene = new ChamberScene($('scene'));
    scene.onDoor = (open) => { setDoorUi(open); send(`p ${open ? 1 : 0}`); };
    if (params.has('debug')) window.__scene = scene;
    if (last) applyScene(last);
  })
  .catch((err) => {
    $('scene').innerHTML = '<p class="hint" style="padding:24px">Não foi possível carregar a vista 3D. As leituras abaixo continuam funcionando.</p>';
    log(`# vista 3D indisponível: ${err.message}`);
  });

// --------------------------------------------------------------- registro
function log(text) {
  const li = document.createElement('li');
  const time = document.createElement('time');
  time.textContent = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const msg = document.createElement('span');
  msg.textContent = text.replace(/^#\s*/, '');
  li.append(time, msg);
  const list = $('log');
  list.prepend(li);
  while (list.children.length > 40) list.lastChild.remove();
}

// ------------------------------------------------------------- conexao
function setConn(state, text) {
  const btn = $('conn');
  btn.dataset.state = state;
  $('conn-text').textContent = text;
}

function showNotice(text, actionLabel, action) {
  $('notice-text').textContent = text;
  const b = $('notice-action');
  b.textContent = actionLabel;
  b.onclick = action;
  $('notice').hidden = false;
}
const hideNotice = () => { $('notice').hidden = true; };

function connect() {
  chart.clear();
  last = null;
  hideNotice();
  if (config.demo) link.startDemo();
  else link.connectMqtt(config.broker, config.device);
}

link.addEventListener('state', (e) => {
  setConn(e.detail.state, e.detail.text);
  if (e.detail.state === 'live' || e.detail.state === 'demo') hideNotice();
});

link.addEventListener('stale', (e) => {
  const msg = {
    stopped: 'A câmara parou de enviar leituras. Confira se a simulação no Wokwi continua rodando.',
    'no-device': `Nenhuma câmara está publicando como "${config.device}". Inicie a simulação no Wokwi ou use o modo demonstração.`,
    'no-broker': 'Não foi possível falar com o broker MQTT. Verifique a internet ou o endereço em Conexão, ou use o modo demonstração.',
  }[e.detail.reason];
  showNotice(msg, 'Usar demonstração', () => { config.demo = true; store.set('demo', '1'); connect(); });
});

link.addEventListener('device', (e) => log(e.detail.online ? '# câmara online' : '# câmara offline'));
link.addEventListener('log', (e) => log(e.detail));
link.addEventListener('telemetry', (e) => render(e.detail));

function send(cmd) {
  if (!link.send(cmd)) {
    log('# sem conexão: comando não enviado');
    return false;
  }
  log(`> ${cmd}`);
  return true;
}

// ------------------------------------------------------------- render
// O display da cena mostra o mesmo que o TM1637 do firmware.
function displayCells(d) {
  if (d.mode === 'FALHA') return errorCells();
  if (d.cut) return batteryCells();
  return temperatureCells(d.T);
}

function applyScene(d) {
  const cells = displayCells(d);
  scene?.setState({
    ue: d.ue ?? d.u, T: d.T, amb: d.amb ?? 25, fault: d.mode === 'FALHA' || d.cut === 1,
    fan: d.fan ?? 0, display: cells, displayKey: cellsKey(cells),
    heat: (d.heat ?? 0) * (d.ue != null && d.u > 0 ? d.ue / d.u : 1), hon: d.hon ?? 0,
    sink: d.th ?? null, beat: d.t, door: d.door ?? null,
  });
}

// ------------------------------------------------------------- porta
const DOOR_GAIN = 4;            // PLANT_DOOR_GAIN: porta aberta troca ~5x mais calor
let doorOpen = false;
function setDoorUi(open) {
  doorOpen = open;
  $('door-btn').setAttribute('aria-pressed', open ? 'true' : 'false');
  $('door-text').textContent = open ? 'Fechar a porta' : 'Abrir a porta';
  if (last) renderMax(last);
}
$('door-btn').addEventListener('click', () => {
  if (scene && scene.renderer) scene.toggleDoor(!doorOpen);
  else { setDoorUi(!doorOpen); send(`p ${doorOpen ? 1 : 0}`); }
});

// Temperatura de regime com tudo a 100 %, sem as protecoes:
//   T = T_amb + (K_lampadas + K_manta) / (1 + D * porta)
function theoreticalMax(d) {
  const amb = d.amb ?? 25;
  const k = 16 + (d.hon === 1 ? 50 : 0);
  return amb + k / (1 + (doorOpen ? DOOR_GAIN : 0));
}
function renderMax(d) {
  const tmax = theoreticalMax(d);
  const where = doorOpen ? 'porta aberta' : 'porta fechada';
  $('tmax').innerHTML = `Máx. teórico: <b>${fmt(tmax, 0)} °C</b> · ${where}`;
  $('tmax').title = !doorOpen && tmax > 78
    ? 'Regime com lâmpadas e manta a 100 %. Na prática o corte do firmware (78 °C) e o TH1 (85 °C) agem antes.'
    : 'Regime com lâmpadas e manta a 100 %.';
}

// ------------------------------------------------------------- icones
const SVG_NS = 'http://www.w3.org/2000/svg';
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

// onda de PWM com o duty real: 3 periodos entre x = 3 e x = 29
function pwmPath(duty) {
  const x0 = 3, x1 = 29, hi = 8, lo = 24, n = 3;
  const per = (x1 - x0) / n;
  if (duty <= 0.01) return `M${x0} ${lo}H${x1}`;
  if (duty >= 0.99) return `M${x0} ${lo}V${hi}H${x1}V${lo}`;
  let p = `M${x0} ${lo}`;
  for (let k = 0; k < n; k++) {
    const a = x0 + k * per, b = a + per * duty;
    p += `H${a.toFixed(2)}V${hi}H${b.toFixed(2)}V${lo}`;
  }
  return `${p}H${x1}`;
}

// rotor do cooler: gira de verdade, com inercia, na velocidade do PWM
const fanIcon = { el: null, speed: 0, target: 0, angle: 0, last: 0 };
function spinFan(now) {
  const f = fanIcon;
  const dt = Math.min(0.1, (now - (f.last || now)) / 1000);
  f.last = now;
  f.speed += (f.target - f.speed) * Math.min(1, dt / 0.6);
  if (!reduceMotion.matches && f.speed > 0.002) {
    f.angle = (f.angle + f.speed * 900 * dt) % 360;
    f.el.setAttribute('transform', `rotate(${f.angle.toFixed(1)} 16 16)`);
  }
  requestAnimationFrame(spinFan);
}
fanIcon.el = document.querySelector('.icon-fan__rotor');
requestAnimationFrame(spinFan);

function renderIcons(d) {
  const lamps = d.cut ? 0 : d.u;
  const bulb = document.querySelector('.icon-bulb');
  bulb.style.setProperty('--lvl', (d.ue ?? lamps).toFixed(3));
  bulb.classList.toggle('is-on', lamps > 0.01);

  const heater = document.querySelector('.icon-heater');
  const heat = d.cut ? 0 : (d.heat ?? 0);
  heater.style.setProperty('--lvl', heat.toFixed(3));
  heater.classList.toggle('is-on', heat > 0.01);
  heater.classList.toggle('is-off', d.hon === 0 || !!d.trip);

  if (d.th != null) {
    const sinkIcon = document.querySelector('.icon-sink');
    const hot = Math.max(0, Math.min(1, (d.th - 25) / 95));
    sinkIcon.style.setProperty('--hot', hot.toFixed(3));
    sinkIcon.classList.toggle('is-warm', d.th > 30);
    sinkIcon.classList.toggle('is-trip', !!d.trip);
    const lvl = 1.6 + 12 * hot;
    $('i-sink').setAttribute('height', lvl.toFixed(2));
    $('i-sink').setAttribute('y', (30.2 - lvl).toFixed(2));
  }

  const fan = d.cut ? 0 : (d.fan ?? 0);
  fanIcon.target = fan;
  document.querySelector('.icon-fan').classList.toggle('is-on', fan > 0.01);

  const bolt = document.querySelector('.icon-bolt');
  const v = d.cut ? 0 : d.v;
  bolt.style.setProperty('--lvl', Math.min(1, v / 12.6).toFixed(3));
  bolt.classList.toggle('is-on', v > 6);
  bolt.classList.toggle('is-off', v <= 6);

  $('i-pwm').setAttribute('d', pwmPath(lamps));
  document.querySelector('.icon-pwm').classList.toggle('is-on', lamps > 0.01);

  // ponteiro: 0 W a -80 graus, 120 W a +80 graus (5 lampadas + manta de 80 W + ventoinhas)
  const ang = -80 + Math.min(1, Math.max(0, d.p / 120)) * 160;
  $('i-needle').style.transform = `rotate(${ang.toFixed(1)}deg)`;

  const src = $('i-src');
  const onBatt = d.src === 'BAT';
  src.classList.toggle('icon-src--bat', onBatt);
  src.classList.toggle('icon-src--atx', !onBatt);
  src.classList.toggle('is-low', onBatt && d.soc < 0.15);
  const h = 19 * Math.max(0, Math.min(1, d.soc));
  $('i-soc').setAttribute('height', h.toFixed(2));
  $('i-soc').setAttribute('y', (7.5 + 19 - h).toFixed(2));

  // termometro: 15 a 70 degC ocupa o tubo
  const fill = 22 * Math.max(0.04, Math.min(1, (d.T - 15) / 55));
  $('i-mercury').setAttribute('height', fill.toFixed(2));
  $('i-mercury').setAttribute('y', (30 - fill).toFixed(2));
}

const MODE_TEXT = {
  PI: 'O controlador PI aquece com as lâmpadas e a manta e, se a câmara passar do alvo, liga o cooler para jogar o ar quente para fora.',
  MANUAL: 'Você define o aquecimento (lâmpadas + manta) e o cooler diretamente. O controle automático fica desligado.',
  DEGRAU: 'Malha aberta com o cooler parado: aquecimento a 60 % com a manta (100 % só com lâmpadas). A curva de subida dá a constante de tempo da câmara.',
  FALHA: 'A temperatura passou do limite de segurança: o firmware desligou lâmpadas e manta e ligou o cooler no máximo. Escolha Automático para retomar.',
};
const MODE_BADGE = { MANUAL: 'Manual', DEGRAU: 'Ensaio de degrau', FALHA: 'Falha: lâmpadas desligadas' };

function render(d) {
  last = d;

  $('temp').textContent = fmt(d.T);
  $('target').textContent = fmt(d.sp);

  const err = d.sp - d.T;
  $('delta').textContent = d.mode !== 'PI' ? ' '
    : Math.abs(err) < 0.3 ? 'No alvo'
    : err > 0 ? `Faltam ${fmt(err)} °C`
    : (d.fan ?? 0) > 0.01 ? `${fmt(-err)} °C acima do alvo, cooler exaurindo o ar quente`
    : `${fmt(-err)} °C acima do alvo, esfriando`;

  // setpoint: so acompanha a telemetria quando nao ha mudanca pendente
  if (spPending === null || Math.abs(spPending - d.sp) < 0.05) {
    spPending = null;
    setSliderValue(d.sp);
    $('sp-value').removeAttribute('data-pending');
  }

  const amb = d.amb ?? 25;
  const hon = d.hon === 1;
  const locked = scene && scene.doorLockUntil && performance.now() < scene.doorLockUntil;
  if (d.door != null && d.door !== (doorOpen ? 1 : 0) && !locked) setDoorUi(d.door === 1);
  renderMax(d);
  const reach = theoreticalMax(d);
  $('sp-hint').textContent = doorOpen && d.sp > reach - 0.5
    ? `Com a porta aberta o ar de dentro troca com o ambiente (${fmt(amb)} °C) e o máximo teórico cai para cerca de ${fmt(reach, 0)} °C. Feche a porta para o PI chegar ao alvo.`
    : doorOpen
    ? `Porta aberta: o ar frio entra por baixo e o quente sai por cima. Máximo teórico agora: ${fmt(reach, 0)} °C.`
    : d.sp > reach - 0.5
    ? `Esse alvo está acima do que as lâmpadas alcançam sozinhas (cerca de ${fmt(reach, 0)} °C com o ambiente atual). Ligue a manta ou o erro não zera.`
    : d.sp < amb + 0.5
    ? `Esse alvo está no nível do ambiente (${fmt(amb)} °C) ou abaixo. O cooler só troca o ar de dentro pelo de fora, então a câmara não esfria abaixo do ambiente.`
    : hon
    ? 'Faixa útil: do ambiente até 70 °C (policarbonato e LM35 com folga). Acima do alvo, o cooler ajuda a esfriar.'
    : `Só lâmpadas: numa câmara deste tamanho elas chegam a cerca de ${fmt(reach, 0)} °C. A manta faz o trabalho pesado.`;

  // instrumentos
  $('g-duty').textContent = fmt(d.u * 100, 0);
  $('g-duty-bar').style.width = `${Math.round(d.u * 100)}%`;
  $('g-duty-note').textContent = d.u > 0.01 ? `${d.lamps ?? 3} × W5W acesas` : 'apagadas';
  const heat = d.heat ?? 0;
  $('g-heat').textContent = d.hon === 0 ? '–' : fmt(heat * 100, 0);
  $('g-heat-bar').style.width = `${Math.round(heat * 100)}%`;
  $('g-heat-note').textContent = d.hon === 0 ? 'desligada (só lâmpadas)'
    : d.trip ? 'cortada pelo TH2 (relé K1)'
    : heat > 0.01 ? `${fmt(80 * heat * Math.pow((d.v || 12) / 12, 2), 1)} W na base` : 'fria';
  const sink = d.th;
  $('gc-sink').hidden = sink == null;
  if (sink != null) {
    $('g-sink').textContent = fmt(sink, 0);
    const frac = Math.max(0, Math.min(1, (sink - 20) / 100));
    $('g-sink-bar').style.width = `${Math.round(frac * 100)}%`;
    $('g-sink-bar').parentElement.toggleAttribute('data-trip', !!d.trip);
    $('g-sink-note').textContent = d.trip ? 'TH2 aberto: K1 cortou o aquecimento até 100 °C' : `${fmt(120 - sink, 0)} °C até o TH2 abrir`;
  }
  const fan = d.fan ?? 0;
  $('g-fan').textContent = fmt(fan * 100, 0);
  $('g-fan-bar').style.width = `${Math.round(fan * 100)}%`;
  $('g-fan-note').textContent = d.mode === 'FALHA' ? 'máximo: proteção'
    : fan > 0.01 ? 'exaustão ligada' : 'parado';
  $('g-volt').textContent = d.cut ? '0,0' : fmt(d.v, 2);
  $('g-volt-note').textContent = d.cut ? 'cortada pelo BMS'
    : d.src === 'BAT' ? 'bateria 3S' : 'ATX, trilho 12 V';
  $('g-amp').textContent = fmt(d.i, 2);
  $('g-watt').textContent = fmt(d.p, 1);
  $('g-amp-note').textContent = d.sim ? 'média, simulada' : 'média, estimada';

  const onBatt = d.src === 'BAT';
  $('g-soc-wrap').hidden = !onBatt;
  $('g-soc-bar').style.width = `${Math.round(d.soc * 100)}%`;
  $('g-soc-wrap').toggleAttribute('data-low', d.soc < 0.15);
  $('g-src-val').textContent = onBatt ? `${fmt(d.soc * 100, 0)} %` : 'ATX';
  $('g-src').textContent = onBatt ? 'bateria 3S 18650' : 'tomada, 12 V';
  renderIcons(d);

  // alertas
  const alert = $('alert');
  if (d.cut) {
    alert.textContent = 'Bateria esgotada: o BMS desligou a carga. Recarregue ou mude a fonte para ATX.';
    alert.hidden = false;
  } else if (d.mode === 'FALHA') {
    alert.textContent = MODE_TEXT.FALHA;
    alert.hidden = false;
  } else {
    alert.hidden = true;
  }

  // modo
  const badge = $('mode-badge');
  badge.hidden = !MODE_BADGE[d.mode];
  badge.textContent = MODE_BADGE[d.mode] || '';
  badge.dataset.kind = d.mode === 'FALHA' ? 'fault' : '';
  document.querySelectorAll('.control .segmented button').forEach((b) => {
    b.setAttribute('aria-checked', String(b.dataset.mode === d.mode));
  });
  $('manual').hidden = d.mode !== 'MANUAL';
  $('mode-hint').textContent = MODE_TEXT[d.mode] || '';

  // simulacao
  $('sim').hidden = !d.sim;
  document.querySelectorAll('.sim [data-heat]').forEach((b) => {
    b.setAttribute('aria-checked', String(Number(b.dataset.heat) === (d.hon ?? 1)));
  });
  document.querySelectorAll('.sim .segmented button').forEach((b) => {
    b.setAttribute('aria-checked', String(b.dataset.src === d.src));
  });
  $('amb-out').textContent = `${fmt(d.amb, 1)} °C`;

  // ganhos: nao sobrescreve enquanto o usuario digita
  if (document.activeElement !== $('kp')) $('kp').value = d.kp;
  if (document.activeElement !== $('ki')) $('ki').value = d.ki;

  chart.push({ t: d.t, T: d.T, sp: d.sp, u: d.u, fan: d.fan ?? 0, heat: d.heat ?? 0 });
  pushTable(d);
  applyScene(d);
}

function pushTable(d) {
  tableRows.unshift(d);
  if (tableRows.length > 10) tableRows.pop();
  $('table-body').innerHTML = tableRows.map((r) =>
    `<tr><td>${fmt(r.t / 60, 0)} min</td><td>${fmt(r.T)} °C</td><td>${fmt(r.sp)} °C</td>` +
    `<td>${fmt(r.u * 100, 0)} %${r.hon === 0 ? ' (só lâmp.)' : ''}</td><td>${fmt((r.fan ?? 0) * 100, 0)} %</td><td>${fmt(r.v, 2)} V</td></tr>`).join('');
}

// ------------------------------------------------------------- setpoint
function setSliderValue(v) {
  const range = $('sp-range');
  range.value = v;
  range.style.setProperty('--fill', `${((v - SP_MIN) / (SP_MAX - SP_MIN)) * 100}%`);
  $('sp-value').textContent = `${fmt(v)} °C`;
}

function chooseSetpoint(v, { immediate = false } = {}) {
  v = Math.min(SP_MAX, Math.max(SP_MIN, Math.round(v * 2) / 2));
  spPending = v;
  setSliderValue(v);
  $('sp-value').setAttribute('data-pending', '');
  clearTimeout(spTimer);
  spTimer = setTimeout(() => send(`s ${v}`), immediate ? 0 : 350);
}

$('sp-range').addEventListener('input', (e) => chooseSetpoint(parseFloat(e.target.value)));
$('sp-minus').addEventListener('click', () => chooseSetpoint((spPending ?? last?.sp ?? 45) - 0.5));
$('sp-plus').addEventListener('click', () => chooseSetpoint((spPending ?? last?.sp ?? 45) + 0.5));

// ------------------------------------------------------------- controle
document.querySelectorAll('.control .segmented button').forEach((b) => {
  b.addEventListener('click', () => {
    const m = b.dataset.mode;
    if (m === 'PI') send('c');
    else if (m === 'MANUAL') {
      send(`d ${(parseInt($('duty-range').value, 10) / 100).toFixed(2)}`);
      send(`v ${(parseInt($('fan-range').value, 10) / 100).toFixed(2)}`);
    }
    else if (m === 'DEGRAU') { chart.clear(); send('r'); }
  });
});

const dutyRange = $('duty-range');
dutyRange.classList.add('range--power');
let dutyTimer;
dutyRange.addEventListener('input', () => {
  const v = parseInt(dutyRange.value, 10);
  $('duty-out').textContent = `${v} %`;
  dutyRange.style.setProperty('--fill', `${v}%`);
  clearTimeout(dutyTimer);
  dutyTimer = setTimeout(() => send(`d ${(v / 100).toFixed(2)}`), 250);
});

const fanRange = $('fan-range');
fanRange.classList.add('range--fan');
let fanTimer;
fanRange.addEventListener('input', () => {
  const v = parseInt(fanRange.value, 10);
  $('fan-out').textContent = `${v} %`;
  fanRange.style.setProperty('--fill', `${v}%`);
  clearTimeout(fanTimer);
  fanTimer = setTimeout(() => send(`v ${(v / 100).toFixed(2)}`), 250);
});

// ------------------------------------------------------------- simulacao
document.querySelectorAll('.sim .segmented button').forEach((b) => {
  b.addEventListener('click', () => send(b.dataset.src === 'BAT' ? 'f bat' : 'f atx'));
});
document.querySelectorAll('.sim [data-heat]').forEach((b) => {
  b.addEventListener('click', () => send(`m ${b.dataset.heat}`));
});
$('amb-cold').addEventListener('click', () => send(`a ${((last?.amb ?? 25) - 6).toFixed(1)}`));
$('amb-reset').addEventListener('click', () => send('a 25'));
$('recharge').addEventListener('click', () => send('b'));

$('gains').addEventListener('submit', (e) => {
  e.preventDefault();
  const kp = parseFloat($('kp').value), ki = parseFloat($('ki').value);
  if (!(kp >= 0 && kp <= 5 && ki >= 0 && ki <= 0.1)) {
    log('# ganhos fora da faixa: 0 a 5 para Kp, 0 a 0,1 para Ki');
    return;
  }
  send(`k ${kp} ${ki}`);
  document.activeElement?.blur();
});

// ------------------------------------------------------------- conexao
const dialog = $('settings');
$('conn').addEventListener('click', () => {
  $('broker').value = config.broker;
  $('device').value = config.device;
  if (typeof dialog.showModal === 'function') dialog.showModal();
});
dialog.addEventListener('close', () => {
  const action = dialog.returnValue;
  if (action === 'connect') {
    config.broker = $('broker').value.trim();
    config.device = $('device').value.trim();
    config.demo = false;
    store.set('broker', config.broker);
    store.set('device', config.device);
    store.set('demo', '0');
    connect();
  } else if (action === 'demo') {
    config.demo = true;
    store.set('demo', '1');
    connect();
  }
});

setSliderValue(45);
dutyRange.style.setProperty('--fill', '0%');
fanRange.style.setProperty('--fill', '0%');
connect();
