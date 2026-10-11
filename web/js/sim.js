/*
 * Modo demonstracao: a mesma fisica e o mesmo controle do firmware,
 * rodando no navegador.
 *
 * Porta direta de lib/control (pi_controller, split_range, plant_model com a manta,
 * battery_model) e do loop de src/main.cpp - mesma ordem de operacoes,
 * mesmas constantes. Serve para apresentar o painel sem o Wokwi aberto.
 * Os dados ficam claramente marcados como simulados na interface.
 */

const C = {
  SAMPLE_PERIOD_S: 60,
  TIME_SCALE: 60,                 // 1 s de parede = 60 s de modelo
  SP_MIN: 25, SP_MAX: 70, SP_DEFAULT: 45,
  CUTOFF_C: 78,
  KP: 0.080, KI: 0.000100,
  INTEGRAL_BAND_C: 3,
  FEEDFORWARD: true,
  TAU_S: 1000, GAIN_C: 16, AMBIENT_C: 25, FAN_GAIN: 5,
  HEATER_GAIN_C: 50, HEATER_TAU_S: 140, HEATER_COUPLING: 2, HEATER_TRIP_C: 120, HEATER_RESET_C: 100,
  HEATER_TRIP_CUTS_ALL: true,     // TH2 na cadeia do rele K1
  HEATER_R: (12 * 12) / 80,       // manta 12 V / 80 W = 1,8 ohms
  STEP_DUTY_HEATER: 0.6,
  LAMPS: 5,
  R_EQ: (12 * 12) / (5 * 5),      // 5,76 ohms
  BASE_W: 2.7,                    // ESP32 + buck + ventoinha de circulacao M2
  FAN_W: 1.8,
  FAN_MIN: 0.30, FAN_ON: 0.10, FAN_OFF: 0.04, FAN_SCALE: 6,
  V_NOM: 12,
  BATT_CELLS: 3, BATT_WH: 66.6, BATT_RINT: 0.08,   // 3S2P
};

const clamp = (x, lo, hi) => (x < lo ? lo : x > hi ? hi : x);

// lib/control/pi_controller.cpp
class PIController {
  constructor(kp, ki, umin = 0, umax = 1) {
    Object.assign(this, { kp, ki, umin, umax });
    this.band = 0; this.settleRate = 0.0005; this.approachRate = 0.004;
    this.reset();
  }
  setIntegralBand(band) { this.band = band; }
  reset() {
    this.integral = 0; this.lastMeas = null; this.lastSp = null; this.stillCount = 0;
  }
  update(sp, y, dt, ff = 0) {
    const e = sp - y;
    const rate = this.lastMeas === null ? 1e9 : (y - this.lastMeas) / dt;
    this.lastMeas = y;
    const still = Math.abs(rate) <= this.settleRate;
    const spChanged = this.lastSp !== null && Math.abs(sp - this.lastSp) > 0.05;
    this.lastSp = sp;
    this.stillCount = spChanged || !still ? 0 : Math.min(255, this.stillCount + 1);
    const settled = this.stillCount >= 4;
    const approaching = (e > 0 && rate > this.approachRate) || (e < 0 && rate < -this.approachRate);
    const near = Math.abs(e) <= this.band && !approaching;
    const inBand = this.band <= 0 || near || settled;

    const integralTry = inBand ? this.integral + e * dt : this.integral;
    const uTry = ff + this.kp * e + this.ki * integralTry;
    const u = clamp(uTry, this.umin, this.umax);
    const up = uTry > this.umax && e > 0;
    const down = uTry < this.umin && e < 0;
    if (!up && !down) this.integral = integralTry;
    return u;
  }
}

// lib/control/split_range.cpp
class SplitRange {
  constructor() { this.fanOn = false; }
  reset() { this.fanOn = false; }
  update(u) {
    u = clamp(u, -1, 1);
    const lamps = u > 0 ? u : 0;
    const demand = u < 0 ? Math.min(1, -u * C.FAN_SCALE) : 0;
    if (!this.fanOn && demand > C.FAN_ON) this.fanOn = true;
    else if (this.fanOn && demand < C.FAN_OFF) this.fanOn = false;
    const fan = this.fanOn ? Math.min(1, C.FAN_MIN + (1 - C.FAN_MIN) * demand) : 0;
    return { lamps, fan };
  }
}

// lib/control/plant_model.cpp - ar + dissipador da manta (dois nos)
class PlantModel {
  constructor(tau, gain, amb, fanGain) {
    Object.assign(this, { tau, gain, amb, fanGain, T: amb, Th: amb, hasHeater: false, tripped: false });
  }
  setHeater(gain, tau, coupling, trip, reset, cutsAll = false) {
    Object.assign(this, { hGain: gain, hTau: tau, r: coupling, trip, resetC: reset, cutsAll, hasHeater: true });
  }
  step(lamps, heater, fan, dt) {
    lamps = clamp(lamps, 0, 1); heater = clamp(heater, 0, 1); fan = clamp(fan, 0, 1);
    if (!this.hasHeater) {
      const loss = (1 + this.fanGain * fan) * (this.T - this.amb);
      this.T += (dt / this.tau) * (this.gain * lamps - loss);
      return this.T;
    }
    if (this.Th > this.trip) this.tripped = true;
    else if (this.Th < this.resetC) this.tripped = false;
    if (this.tripped) { heater = 0; if (this.cutsAll) lamps = 0; }
    const h = dt / 6;
    for (let i = 0; i < 6; i++) {
      const q = this.r * (this.Th - this.T);
      const loss = (1 + this.fanGain * fan) * (this.T - this.amb);
      const dAir = (this.gain * lamps + q - loss) / this.tau;
      const dSink = ((this.hGain / this.r) * heater - (this.Th - this.T)) / this.hTau;
      this.T += h * dAir;
      this.Th += h * dSink;
    }
    return this.T;
  }
}

const OCV_SOC = [0.00, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80, 0.90, 1.00];
const OCV_V   = [3.00, 3.30, 3.45, 3.58, 3.68, 3.78, 3.93, 4.05, 4.20];

// lib/control/battery_model.cpp
class BatteryModel {
  constructor(cells, wh, rint) {
    Object.assign(this, { cells, capJ: wh * 3600, rint });
    this.reset();
  }
  reset() { this.soc = 1; this.cutoff = false; this.v = this.cells * this.ocv(1); this.i = 0; }
  ocv(soc) {
    if (soc <= 0) return OCV_V[0];
    if (soc >= 1) return OCV_V[OCV_V.length - 1];
    for (let k = 1; k < OCV_SOC.length; k++) {
      if (soc <= OCV_SOC[k]) {
        const f = (soc - OCV_SOC[k - 1]) / (OCV_SOC[k] - OCV_SOC[k - 1]);
        return OCV_V[k - 1] + f * (OCV_V[k] - OCV_V[k - 1]);
      }
    }
    return OCV_V[OCV_V.length - 1];
  }
  step(duty, rLoad, baseW, dt) {
    if (this.cutoff) { this.v = 0; this.i = 0; return 0; }
    duty = clamp(duty, 0, 1);
    const ocv = this.cells * this.ocv(this.soc);
    const a = 1 + this.rint * duty / rLoad;
    const disc = ocv * ocv - 4 * a * this.rint * baseW;
    const v = disc > 0 ? (ocv + Math.sqrt(disc)) / (2 * a) : ocv / (2 * a);
    this.v = v;
    this.i = duty * v / rLoad + (v > 0.1 ? baseW / v : 0);
    this.soc = Math.max(0, this.soc - (ocv * this.i * dt) / this.capJ);
    if (this.soc <= 0 || this.v < 2.8 * this.cells) { this.cutoff = true; this.v = 0; this.i = 0; }
    return this.v;
  }
}

export class DemoDevice extends EventTarget {
  constructor() {
    super();
    this.pi = new PIController(C.KP, C.KI, -1, 1);
    this.pi.setIntegralBand(C.INTEGRAL_BAND_C);
    this.split = new SplitRange();
    this.plant = new PlantModel(C.TAU_S, C.GAIN_C, C.AMBIENT_C, C.FAN_GAIN);
    this.plant.setHeater(C.HEATER_GAIN_C, C.HEATER_TAU_S, C.HEATER_COUPLING, C.HEATER_TRIP_C, C.HEATER_RESET_C, C.HEATER_TRIP_CUTS_ALL);
    this.heaterOn = true;
    this.heat = 0;
    this.batt = new BatteryModel(C.BATT_CELLS, C.BATT_WH, C.BATT_RINT);
    this.mode = 'PI';
    this.sp = C.SP_DEFAULT;
    this.manual = 0;
    this.manualFan = 0;
    this.duty = 0;
    this.fan = 0;
    this.t = 0;
    this.onBattery = false;
    this.v = C.V_NOM;
    this.i = 0;
    this.timer = null;
    this.start0 = performance.now();
  }

  start() {
    if (this.timer) return;
    this.tick();
    this.timer = setInterval(() => this.tick(), (C.SAMPLE_PERIOD_S * 1000) / C.TIME_SCALE);
  }

  stop() { clearInterval(this.timer); this.timer = null; }

  #reply(text) { this.dispatchEvent(new CustomEvent('log', { detail: text })); }

  command(raw) {
    const line = raw.trim();
    if (!line) return;
    const cmd = line[0];
    const arg = line.slice(1).trim();
    const num = parseFloat(arg);
    switch (cmd) {
      case 's':
        this.sp = clamp(isNaN(num) ? this.sp : num, C.SP_MIN, C.SP_MAX);
        this.mode = 'PI';
        this.#reply(`# setpoint = ${this.sp.toFixed(1)} C`);
        break;
      case 'k': {
        const [kp, ki] = arg.split(/\s+/).map(Number);
        if (!(kp >= 0 && kp <= 5 && ki >= 0 && ki <= 0.1)) { this.#reply('# ganhos fora da faixa'); break; }
        this.pi.kp = kp; this.pi.ki = ki;
        this.#reply(`# Kp = ${kp.toFixed(5)}  Ki = ${ki.toFixed(7)}`);
        break;
      }
      case 'd':
        this.manual = clamp(isNaN(num) ? 0 : num, 0, 1);
        this.mode = 'MANUAL';
        this.#reply(`# duty manual = ${this.manual.toFixed(2)}`);
        break;
      case 'v':
        this.manualFan = clamp(isNaN(num) ? 0 : num, 0, 1);
        this.mode = 'MANUAL';
        this.#reply(`# cooler manual = ${this.manualFan.toFixed(2)}`);
        break;
      case 'm':
        this.heaterOn = (isNaN(num) ? 0 : num) > 0.5;
        this.#reply(this.heaterOn ? '# manta ligada' : '# manta desligada (so lampadas)');
        break;
      case 'r':
        this.pi.reset(); this.split.reset(); this.mode = 'DEGRAU'; this.t = 0;
        this.#reply(`# ensaio de degrau iniciado (duty = ${this.#stepDuty().toFixed(2)})`);
        break;
      case 'c':
        this.pi.reset(); this.split.reset(); this.mode = 'PI';
        this.#reply('# malha fechada');
        break;
      case 'a':
        this.plant.amb = clamp(isNaN(num) ? C.AMBIENT_C : num, 0, 40);
        this.#reply(`# ambiente = ${this.plant.amb.toFixed(1)} C`);
        break;
      case 'f':
        this.onBattery = arg.startsWith('b');
        this.#reply(this.onBattery ? '# fonte = bateria 3S' : '# fonte = ATX 12 V');
        break;
      case 'b':
        this.batt.reset();
        this.#reply('# bateria recarregada');
        break;
      default:
        this.#reply('# comando desconhecido');
    }
  }

  #gain() { return C.GAIN_C + (this.heaterOn ? C.HEATER_GAIN_C : 0); }
  #stepDuty() { return this.heaterOn ? C.STEP_DUTY_HEATER : 1; }

  // Mesma ordem do loop() em src/main.cpp.
  tick() {
    const dt = C.SAMPLE_PERIOD_S;

    // alimentacao do intervalo que passou
    const base = C.BASE_W + this.fan * C.FAN_W;
    if (this.onBattery) {
      const g = this.duty / C.R_EQ + this.heat / C.HEATER_R;
      this.v = g > 0 ? this.batt.step(1, 1 / g, base, dt) : this.batt.step(0, C.R_EQ, base, dt);
      this.i = this.batt.i;
    } else {
      this.v = C.V_NOM;
      this.i = this.duty * this.v / C.R_EQ + this.heat * this.v / C.HEATER_R + base / this.v;
    }
    const vr = this.v / C.V_NOM;
    const T = this.plant.step(this.duty * vr * vr, this.heat * vr * vr, this.fan * vr, dt);

    if (T > C.CUTOFF_C && this.mode !== 'FALHA') {
      this.mode = 'FALHA';
      this.#reply(`# FALHA: temperatura fora da faixa (${T.toFixed(1)} C)`);
    }

    let lamps = 0, fan = 0;
    if (this.mode === 'PI') {
      const ff = C.FEEDFORWARD ? clamp((this.sp - C.AMBIENT_C) / this.#gain(), 0, 1) : 0;
      ({ lamps, fan } = this.split.update(this.pi.update(this.sp, T, dt, ff)));
    } else if (this.mode === 'MANUAL') { lamps = this.manual; fan = this.manualFan; }
    else if (this.mode === 'DEGRAU') { lamps = this.#stepDuty(); fan = 0; }
    else { lamps = 0; fan = 1; }        // FALHA: lampadas desligadas, cooler no maximo

    if (this.v > 6) {
      const ratio = C.V_NOM / this.v;
      lamps = clamp(lamps * ratio * ratio, 0, 1);
      fan = clamp(fan * ratio, 0, 1);
    }
    this.duty = this.mode === 'FALHA' ? 0 : lamps;
    this.heat = this.mode === 'FALHA' || !this.heaterOn ? 0 : lamps;
    this.fan = fan;

    const cut = this.onBattery && this.batt.cutoff;
    this.dispatchEvent(new CustomEvent('telemetry', {
      detail: {
        t: this.t, T, sp: this.sp, u: this.duty, ue: this.duty * vr * vr,
        e: this.sp - T, v: this.v, i: this.i, p: this.v * this.i,
        soc: this.onBattery ? this.batt.soc : 1, src: this.onBattery ? 'BAT' : 'ATX',
        cut: cut ? 1 : 0, mode: this.mode, kp: this.pi.kp, ki: this.pi.ki,
        amb: this.plant.amb, sim: 1, lamps: C.LAMPS, fan: this.fan,
        heat: this.heat, hon: this.heaterOn ? 1 : 0, th: this.plant.Th, trip: this.plant.tripped ? 1 : 0,
        up: Math.round(performance.now() - this.start0),
      },
    }));
    this.t += dt;
  }
}
