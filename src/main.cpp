/*
 * PIDlampada - Camara Termica Compacta com Controle PWM
 * UNIP - Engenharia de Computacao - Projeto Integrador 2026
 *
 * Mesma fonte roda no hardware e no Wokwi; o que muda e' a origem da
 * temperatura (SENSOR_SOURCE) e a escala de tempo (SIM_TIME_SCALE).
 *
 * Saida serial em CSV para alimentar direto a analise em Python/Excel:
 *   t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo
 *
 * Comandos pela serial (uma linha, Enter no fim):
 *   s 45       define setpoint em 45 degC
 *   k 0.05 0.0002   define Kp e Ki
 *   d 0.8      duty manual (malha aberta)
 *   r          inicia ensaio de degrau (duty 100%, malha aberta)
 *   c          volta para malha fechada
 *   ?          imprime o estado atual
 */

#include <Arduino.h>
#include "config.h"
#include "pi_controller.h"
#include "sensor.h"
#include "actuator.h"

enum class Mode { CLOSED_LOOP, OPEN_LOOP, STEP_TEST, FAULT };

static PIController pi(PI_KP, PI_KI, 0.0f, 1.0f);
static Mode  g_mode = Mode::CLOSED_LOOP;
static float g_setpoint = SETPOINT_DEFAULT_C;
static float g_manual_duty = 0.0f;
static float g_duty = 0.0f;
static float g_model_time_s = 0.0f;

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

static void handleSerial() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.isEmpty()) return;

  const char cmd = line.charAt(0);
  const String arg = line.substring(1);

  switch (cmd) {
    case 's':
      g_setpoint = constrain(arg.toFloat(), SETPOINT_MIN_C, SETPOINT_MAX_C);
      g_mode = Mode::CLOSED_LOOP;
      Serial.printf("# setpoint = %.1f C\n", g_setpoint);
      break;
    case 'k': {
      const int sp = arg.indexOf(' ', 1);
      const float kp = arg.substring(0, sp).toFloat();
      const float ki = arg.substring(sp + 1).toFloat();
      pi.setGains(kp, ki);
      Serial.printf("# Kp = %.5f  Ki = %.6f\n", kp, ki);
      break;
    }
    case 'd':
      g_manual_duty = constrain(arg.toFloat(), 0.0f, 1.0f);
      g_mode = Mode::OPEN_LOOP;
      Serial.printf("# duty manual = %.2f\n", g_manual_duty);
      break;
    case 'r':
      pi.reset();
      g_mode = Mode::STEP_TEST;
      g_model_time_s = 0.0f;
      Serial.println("# ensaio de degrau iniciado (duty = 1.00)");
      break;
    case 'c':
      pi.reset();
      g_mode = Mode::CLOSED_LOOP;
      Serial.println("# malha fechada");
      break;
    case '?':
      Serial.printf("# modo=%s sp=%.1f Kp=%.5f Ki=%.6f duty=%.3f\n",
                    modeName(g_mode), g_setpoint, pi.kp(), pi.ki(), g_duty);
      break;
    default:
      Serial.println("# comandos: s <C> | k <kp> <ki> | d <0-1> | r | c | ?");
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  pinMode(PIN_LED_ST, OUTPUT);
  pinMode(PIN_BTN_MODE, INPUT_PULLUP);

  sensor::begin();
  actuator::begin();

  Serial.println();
  Serial.println("# PIDlampada - camara termica compacta");
  Serial.printf("# sensor=%d  escala de tempo=%dx  amostragem=%.0f s\n",
                SENSOR_SOURCE, (int)SIM_TIME_SCALE, SAMPLE_PERIOD_S);
  Serial.println("t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo");
}

void loop() {
  static uint32_t last_ms = 0;
  handleSerial();

  const uint32_t now = millis();
  if (now - last_ms < kWallPeriodMs) return;
  last_ms = now;

  const float dt = SAMPLE_PERIOD_S;          // tempo de modelo, nao de parede
  g_model_time_s += dt;

  const float temp = sensor::readTemperatureC(g_duty, dt);
  const float vbat = sensor::readBusVoltage();

  // Setpoint pelo potenciometro quando ele existe.
  const float pot = sensor::readSetpointPot();
  if (!isnan(pot) && g_mode == Mode::CLOSED_LOOP) g_setpoint = pot;

  // --- camada de seguranca em firmware (o KSD9700 e' a de hardware) -------
  if (temp > TEMP_CUTOFF_C || isnan(temp) || temp < -40.0f) {
    g_mode = Mode::FAULT;
    actuator::shutdown();
    g_duty = 0.0f;
  }

  // --- lei de controle -----------------------------------------------------
  float u = 0.0f;
  switch (g_mode) {
    case Mode::CLOSED_LOOP: u = pi.update(g_setpoint, temp, dt); break;
    case Mode::OPEN_LOOP:   u = g_manual_duty; break;
    case Mode::STEP_TEST:   u = 1.0f; break;
    case Mode::FAULT:       u = 0.0f; break;
  }

  // --- compensacao de tensao: duty_corr = duty * (12 / V_bat)^2 ------------
  float u_out = u;
  if (VBAT_COMPENSATE && vbat > 6.0f) {
    const float ratio = VBAT_NOMINAL_V / vbat;
    u_out = constrain(u * ratio * ratio, 0.0f, 1.0f);
  }

  if (g_mode != Mode::FAULT) actuator::setDuty(u_out);
  g_duty = u_out;

  digitalWrite(PIN_LED_ST, g_mode == Mode::FAULT ? HIGH : !digitalRead(PIN_LED_ST));

  Serial.printf("%.0f,%.2f,%.1f,%.4f,%.2f,%.2f,%s\n",
                g_model_time_s, temp, g_setpoint, g_duty,
                g_setpoint - temp, vbat, modeName(g_mode));
}
