#include "actuator.h"
#include "config.h"
#include <Arduino.h>

namespace {
float g_duty = 0.0f;
float g_fan = 0.0f;

void writeRaw(float duty) {
  if (duty < 0.0f) duty = 0.0f;
  if (duty > 1.0f) duty = 1.0f;
  ledcWrite(PWM_CHANNEL, static_cast<uint32_t>(duty * PWM_MAX));
  g_duty = duty;
}
}  // namespace

namespace actuator {

void begin() {
  // NOTA: ledcSetup() do core Arduino nao expoe a fonte de clock.
  // Para manter o PWM vivo durante o light sleep e' preciso configurar
  // o timer LEDC com REF_TICK via API do ESP-IDF (ledc_timer_config).
  // Ver issue "light sleep + REF_TICK" no README.
  ledcSetup(PWM_CHANNEL, PWM_FREQ_HZ, PWM_RESOLUTION);
  ledcAttachPin(PIN_PWM_GATE, PWM_CHANNEL);
  writeRaw(0.0f);

  ledcSetup(FAN_PWM_CHANNEL, FAN_PWM_FREQ_HZ, FAN_PWM_RESOLUTION);
  ledcAttachPin(PIN_FAN, FAN_PWM_CHANNEL);
  setFan(0.0f);
}

void setFan(float duty) {
  if (duty < 0.0f) duty = 0.0f;
  if (duty > 1.0f) duty = 1.0f;
  ledcWrite(FAN_PWM_CHANNEL, static_cast<uint32_t>(duty * FAN_PWM_MAX));
  g_fan = duty;
}

float fan() { return g_fan; }

void setDuty(float duty) { writeRaw(duty); }

float duty() { return g_duty; }

void shutdown() { writeRaw(0.0f); }

void softStart(float target_duty) {
  const int steps = 20;
  const int step_ms = static_cast<int>((SOFT_START_S * 1000.0f) / steps);
  for (int i = 1; i <= steps; ++i) {
    writeRaw(target_duty * i / steps);
    delay(step_ms);
  }
}

}  // namespace actuator
