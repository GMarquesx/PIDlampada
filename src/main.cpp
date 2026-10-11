/*
 * PIDlampada - Camara Termica Compacta com Controle PWM
 * UNIP - Engenharia de Computacao - Projeto Integrador 2026
 *
 * Mesma fonte roda no hardware e no Wokwi; o que muda e' a origem da
 * temperatura (SENSOR_SOURCE) e a escala de tempo (SIM_TIME_SCALE).
 *
 * Saida serial em CSV para alimentar direto a analise em Python/Excel:
 *   t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo,i_a,amb_c,fan
 *
 * Controle: PI com feedforward pelo modelo e separacao integral, em faixa
 * dividida - a mesma saida aquece com as lampadas (u > 0) ou exaure com o
 * cooler (u < 0). Display TM1637 mostra a temperatura medida.
 *
 * Telemetria JSON via MQTT para o painel web (ver src/net.h).
 *
 * Comandos - pela serial OU pelo topico <base>/cmd, mesmo protocolo:
 *   s 45            setpoint em 45 degC (volta para malha fechada)
 *   k 0.06 0.0001   define Kp e Ki
 *   d 0.8           duty manual das lampadas (malha aberta)
 *   v 0.6           duty manual do cooler (malha aberta)
 *   r               ensaio de degrau (duty 100 %, malha aberta)
 *   c               volta para malha fechada
 *   a 19            temperatura ambiente do modelo   [so simulacao]
 *   f bat | f atx   seleciona a fonte                [so simulacao]
 *   b               recarrega a bateria              [so simulacao]
 *   ?               imprime o estado atual
 */

#include <Arduino.h>
#include <math.h>
#include <stdarg.h>
#include "config.h"
#include "pi_controller.h"
#include "split_range.h"
#include "seg7.h"
#include "display.h"
#include "sensor.h"
#include "actuator.h"
#include "power.h"
#include "net.h"

enum class Mode { CLOSED_LOOP, OPEN_LOOP, STEP_TEST, FAULT };

// Saida em [-1, 1]: o lado negativo e' o cooler (faixa dividida).
static PIController pi(PI_KP, PI_KI, -1.0f, 1.0f);
static SplitRange g_split(FAN_MIN_DUTY, FAN_ON_TH, FAN_OFF_TH, FAN_GAIN_SCALE);
static Mode  g_mode = Mode::CLOSED_LOOP;
static float g_setpoint = SETPOINT_DEFAULT_C;
static float g_manual_duty = 0.0f;
static float g_manual_fan = 0.0f;
static float g_duty = 0.0f;            // duty aplicado ao MOSFET das lampadas
static float g_fan = 0.0f;             // duty aplicado ao MOSFET do cooler
static float g_model_time_s = 0.0f;
static float g_last_pot = NAN;

// Periodo de parede entre amostras: comprimido por SIM_TIME_SCALE no Wokwi.
static const uint32_t kWallPeriodMs =
    static_cast<uint32_t>((SAMPLE_PERIOD_S * 1000.0f) / SIM_TIME_SCALE);

static const char* modeName(Mode m) {
  switch (m) {
    case Mode::CLOSED_LOOP: return "PI";
    case Mode::OPEN_LOOP:   return "MANUAL";
    case Mode::STEP_TEST:   return "DEGRAU";
    default:                return "FALHA";
  }
}

// Responde na serial e no topico de log - o painel mostra as duas coisas.
static void reply(const char* fmt, ...) {
  char buf[160];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  Serial.print(buf);
  Serial.print("\r\n");
  net::log(buf);
}

static void handleCommand(const String& raw) {
  String line = raw;
  line.trim();
  if (line.isEmpty()) return;

  const char cmd = line.charAt(0);
  String arg = line.substring(1);
  arg.trim();

  switch (cmd) {
    case 's':
      g_setpoint = constrain(arg.toFloat(), SETPOINT_MIN_C, SETPOINT_MAX_C);
      g_mode = Mode::CLOSED_LOOP;
      reply("# setpoint = %.1f C", g_setpoint);
      break;

    case 'k': {
      const int sp = arg.indexOf(' ');
      if (sp < 0) { reply("# uso: k <kp> <ki>"); break; }
      const float kp = arg.substring(0, sp).toFloat();
      const float ki = arg.substring(sp + 1).toFloat();
      if (kp < 0.0f || ki < 0.0f || kp > 5.0f || ki > 0.1f) {
        reply("# ganhos fora da faixa (0 <= kp <= 5, 0 <= ki <= 0.1)");
        break;
      }
      pi.setGains(kp, ki);
      reply("# Kp = %.5f  Ki = %.7f", kp, ki);
      break;
    }

    case 'd':
      g_manual_duty = constrain(arg.toFloat(), 0.0f, 1.0f);
      g_mode = Mode::OPEN_LOOP;
      reply("# duty manual = %.2f", g_manual_duty);
      break;

    case 'v':
      g_manual_fan = constrain(arg.toFloat(), 0.0f, 1.0f);
      g_mode = Mode::OPEN_LOOP;
      reply("# cooler manual = %.2f", g_manual_fan);
      break;

    case 'r':
      pi.reset();
      g_split.reset();
      g_mode = Mode::STEP_TEST;
      g_model_time_s = 0.0f;
      reply("# ensaio de degrau iniciado (duty = 1.00)");
      break;

    case 'c':
      pi.reset();
      g_split.reset();
      g_mode = Mode::CLOSED_LOOP;
      reply("# malha fechada");
      break;

    case 'a':
      if (!power::isSimulated()) { reply("# 'a' so existe na simulacao"); break; }
      sensor::setAmbientC(constrain(arg.toFloat(), 0.0f, 40.0f));
      reply("# ambiente = %.1f C", sensor::ambientC());
      break;

    case 'f':
      if (!power::isSimulated()) { reply("# no hardware a fonte e' escolhida pela SW1"); break; }
      if (arg.startsWith("b")) { power::selectBattery(true);  reply("# fonte = bateria 3S"); }
      else                     { power::selectBattery(false); reply("# fonte = ATX 12 V"); }
      break;

    case 'b':
      if (!power::isSimulated()) { reply("# 'b' so existe na simulacao"); break; }
      power::rechargeBattery();
      reply("# bateria recarregada");
      break;

    case '?':
      reply("# modo=%s sp=%.1f Kp=%.5f Ki=%.7f duty=%.3f cooler=%.3f V=%.2f rede=%s",
            modeName(g_mode), g_setpoint, pi.kp(), pi.ki(), g_duty, g_fan,
            power::busVoltage(), net::online() ? "online" : "offline");
      break;

    default:
      reply("# comandos: s <C> | k <kp> <ki> | d <0-1> | v <0-1> | r | c | a <C> | f bat|atx | b | ?");
  }
}

static void handleSerial() {
  if (!Serial.available()) return;
  handleCommand(Serial.readStringUntil('\n'));
}

static void publishTelemetry(float temp, float duty_eff) {
  char json[400];
  snprintf(json, sizeof(json),
           "{\"t\":%.0f,\"T\":%.2f,\"sp\":%.1f,\"u\":%.4f,\"ue\":%.4f,\"e\":%.2f,"
           "\"v\":%.2f,\"i\":%.3f,\"p\":%.2f,\"soc\":%.3f,\"src\":\"%s\",\"cut\":%d,"
           "\"mode\":\"%s\",\"kp\":%.5f,\"ki\":%.7f,\"amb\":%.1f,\"sim\":%d,"
           "\"lamps\":%d,\"fan\":%.3f,\"up\":%lu}",
           g_model_time_s, temp, g_setpoint, g_duty, duty_eff, g_setpoint - temp,
           power::busVoltage(), power::currentA(), power::powerW(),
           power::stateOfCharge(), power::onBattery() ? "BAT" : "ATX",
           power::cutoff() ? 1 : 0, modeName(g_mode), pi.kp(), pi.ki(),
           sensor::ambientC(), power::isSimulated() ? 1 : 0, LAMP_COUNT,
           g_fan, (unsigned long)millis());
  net::publishTelemetry(json);
}

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(PIN_LED_ST, OUTPUT);
  pinMode(PIN_BTN_MODE, INPUT_PULLUP);

  sensor::begin();
  power::begin();
  actuator::begin();
  display::begin();
  pi.setIntegralBand(PI_INTEGRAL_BAND_C);

  uint8_t seg[4];
  seg7::dashes(seg);
  display::show(seg);

  Serial.println();
  Serial.println("# PIDlampada - camara termica compacta");
  Serial.printf("# sensor=%d  escala de tempo=%dx  amostragem=%.0f s\r\n",
                SENSOR_SOURCE, (int)SIM_TIME_SCALE, SAMPLE_PERIOD_S);

  net::begin(handleCommand);

  Serial.println("t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo,i_a,amb_c,fan");
}

void loop() {
  static uint32_t last_ms = millis();

  handleSerial();
  net::loop();

  const uint32_t now = millis();
  if (now - last_ms < kWallPeriodMs) return;
  // Avanca em passos fixos: se a rede segurou o loop por um instante, as
  // amostras atrasadas sao processadas em seguida e o tempo de modelo nao
  // deriva. Atraso grande demais (ex.: depurador pausado) ressincroniza.
  last_ms += kWallPeriodMs;
  if (now - last_ms > 5 * kWallPeriodMs) last_ms = now;

  const float dt = SAMPLE_PERIOD_S;          // tempo de modelo, nao de parede

  // --- alimentacao do intervalo que passou ----------------------------------
  power::step(g_duty, g_fan, dt);
  const float vbus = power::busVoltage();

  // Potencia nas lampadas relativa a 15 W: carga resistiva, P ~ V^2.
  // A rotacao do cooler acompanha a tensao, aproximadamente linear.
  const float vr = vbus / VBAT_NOMINAL_V;
  const float duty_eff = g_duty * vr * vr;
  const float fan_eff = g_fan * vr;

  const float temp = sensor::readTemperatureC(duty_eff, fan_eff, dt);

  // --- setpoint pelo potenciometro, so quando ele e' mexido ----------------
  // A primeira leitura so registra a posicao: a camara liga sempre em
  // SETPOINT_DEFAULT_C, independente de onde o knob ficou.
  const float pot = sensor::readSetpointPot();
  if (!isnan(pot)) {
    if (isnan(g_last_pot)) {
      g_last_pot = pot;
    } else if (fabsf(pot - g_last_pot) > POT_DEADBAND_C) {
      g_last_pot = pot;
      if (g_mode == Mode::CLOSED_LOOP) g_setpoint = pot;
    }
  }

  // --- camada de seguranca em firmware (o KSD9700 e' a de hardware) -------
  if (temp > TEMP_CUTOFF_C || isnan(temp) || temp < -40.0f) {
    if (g_mode != Mode::FAULT) reply("# FALHA: temperatura fora da faixa (%.1f C)", temp);
    g_mode = Mode::FAULT;
    actuator::shutdown();
  }

  // --- lei de controle -----------------------------------------------------
  float lamps = 0.0f, fan = 0.0f;
  switch (g_mode) {
    case Mode::CLOSED_LOOP: {
      // Feedforward: o duty que o modelo diz segurar este setpoint.
      const float ff = SETPOINT_FEEDFORWARD
          ? constrain((g_setpoint - PLANT_AMBIENT_C) / PLANT_GAIN_C, 0.0f, 1.0f)
          : 0.0f;
      g_split.update(pi.update(g_setpoint, temp, dt, ff), lamps, fan);
      break;
    }
    case Mode::OPEN_LOOP: lamps = g_manual_duty; fan = g_manual_fan; break;
    case Mode::STEP_TEST: lamps = 1.0f; fan = 0.0f; break;
    // Falha: lampadas desligadas e cooler no maximo para tirar o calor.
    case Mode::FAULT:     lamps = 0.0f; fan = 1.0f; break;
  }

  // --- compensacao de tensao -----------------------------------------------
  // lampadas: P ~ V^2  ->  duty * (12/V)^2      cooler: rpm ~ V  ->  duty * 12/V
  if (VBAT_COMPENSATE && vbus > 6.0f) {
    const float ratio = VBAT_NOMINAL_V / vbus;
    lamps = constrain(lamps * ratio * ratio, 0.0f, 1.0f);
    fan = constrain(fan * ratio, 0.0f, 1.0f);
  }

  if (g_mode == Mode::FAULT) actuator::shutdown();
  else actuator::setDuty(lamps);
  actuator::setFan(fan);
  g_duty = (g_mode == Mode::FAULT) ? 0.0f : lamps;
  g_fan = fan;

  // --- display: leitura real da camara -------------------------------------
  uint8_t seg[4];
  if (g_mode == Mode::FAULT)  seg7::error(seg);
  else if (power::cutoff())   seg7::batteryEmpty(seg);
  else                        seg7::temperature(temp, seg);
  display::show(seg);

  digitalWrite(PIN_LED_ST, g_mode == Mode::FAULT ? HIGH : !digitalRead(PIN_LED_ST));

  Serial.printf("%.0f,%.2f,%.1f,%.4f,%.2f,%.2f,%s,%.3f,%.1f,%.3f\r\n",
                g_model_time_s, temp, g_setpoint, g_duty,
                g_setpoint - temp, vbus, modeName(g_mode),
                power::currentA(), sensor::ambientC(), g_fan);
  // Brilho que as lampadas tem AGORA: duty novo com a tensao atual.
  publishTelemetry(temp, g_duty * vr * vr);

  g_model_time_s += dt;  // avanca depois de registrar: primeira linha e' t = 0
}
