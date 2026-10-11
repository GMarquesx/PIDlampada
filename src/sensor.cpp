#include "sensor.h"
#include "config.h"
#include <Arduino.h>
#include <math.h>

#if SENSOR_SOURCE == SENSOR_PLANT
#include "plant_model.h"
static PlantModel g_plant(PLANT_TAU_S, PLANT_GAIN_C, PLANT_AMBIENT_C);
#endif

namespace {

// Media de N leituras cruas do ADC.
int readAdcAveraged(int pin) {
  long acc = 0;
  for (int i = 0; i < ADC_SAMPLES; ++i) {
    acc += analogRead(pin);
    delayMicroseconds(200);
  }
  return static_cast<int>(acc / ADC_SAMPLES);
}

float adcToMillivolts(int raw) {
  return (static_cast<float>(raw) / ADC_MAX) * ADC_VREF_MV;
}

}  // namespace

namespace sensor {

void begin() {
  analogReadResolution(12);
  // 11 dB cobre ate ~3,1 V. Para o LM35 (0,25-0,60 V) 6 dB da melhor
  // linearidade; ver nota no README sobre calibracao do ADC.
  analogSetPinAttenuation(PIN_TEMP, ADC_11db);
  analogSetPinAttenuation(PIN_V_SENSE, ADC_11db);
  analogSetPinAttenuation(PIN_SETPOINT, ADC_11db);
  pinMode(PIN_PWR_OK, INPUT);
#if SENSOR_SOURCE == SENSOR_PLANT
  g_plant.reset(PLANT_AMBIENT_C);
#endif
}

float readTemperatureC(float last_duty, float dt_s) {
#if SENSOR_SOURCE == SENSOR_LM35
  (void)last_duty; (void)dt_s;
  const float mv = adcToMillivolts(readAdcAveraged(PIN_TEMP));
  return mv / LM35_MV_PER_C;

#elif SENSOR_SOURCE == SENSOR_NTC
  (void)last_duty; (void)dt_s;
  // Modulo NTC do Wokwi: 10k NTC em serie com 10k, beta = 3950.
  const int raw = readAdcAveraged(PIN_TEMP);
  const float ratio = static_cast<float>(ADC_MAX) / (raw > 0 ? raw : 1) - 1.0f;
  const float beta = 3950.0f;
  return 1.0f / (logf(1.0f / ratio) / beta + 1.0f / 298.15f) - 273.15f;

#else  // SENSOR_PLANT
  return g_plant.step(last_duty, dt_s);
#endif
}

float readBusVoltage() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return VBAT_NOMINAL_V;
#else
  const float mv = adcToMillivolts(readAdcAveraged(PIN_V_SENSE));
  return (mv / 1000.0f) * VBAT_DIVIDER;
#endif
}

bool atxPresent() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return true;
#else
  return adcToMillivolts(readAdcAveraged(PIN_PWR_OK)) > 1500.0f;
#endif
}

float readSetpointPot() {
  const int raw = readAdcAveraged(PIN_SETPOINT);
  if (raw < 10) return NAN;  // pot ausente / pino flutuando no zero
  const float frac = static_cast<float>(raw) / ADC_MAX;
  return SETPOINT_MIN_C + frac * (SETPOINT_MAX_C - SETPOINT_MIN_C);
}

}  // namespace sensor
