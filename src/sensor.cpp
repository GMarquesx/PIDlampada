#include "sensor.h"
#include "config.h"
#include <Arduino.h>
#include <math.h>

#if SENSOR_SOURCE == SENSOR_PLANT
#include "plant_model.h"
static PlantModel g_plant(PLANT_TAU_S, PLANT_GAIN_C, PLANT_AMBIENT_C, PLANT_FAN_GAIN);
#endif

static float g_ambient_c = PLANT_AMBIENT_C;

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

[[maybe_unused]] float adcToMillivolts(int raw) {
  return (static_cast<float>(raw) / ADC_MAX) * ADC_VREF_MV;
}

}  // namespace

namespace sensor {

void begin() {
  analogReadResolution(12);
  // 11 dB cobre ate ~3,1 V. Para o LM35 (0,25-0,60 V) 6 dB da melhor
  // linearidade; ver nota no README sobre calibracao do ADC.
  analogSetPinAttenuation(PIN_TEMP, ADC_11db);
  analogSetPinAttenuation(PIN_SETPOINT, ADC_11db);
#if SENSOR_SOURCE == SENSOR_PLANT
  g_plant.setHeater(PLANT_HEATER_GAIN_C, PLANT_HEATER_TAU_S, PLANT_HEATER_COUPLING,
                    HEATER_TRIP_C, HEATER_RESET_C, HEATER_TRIP_CUTS_ALL);
  g_plant.setDoorGain(PLANT_DOOR_GAIN);
  g_plant.reset(PLANT_AMBIENT_C);
#endif
}

float readTemperatureC(float effective_duty, float effective_heat, float effective_fan, float dt_s) {
#if SENSOR_SOURCE == SENSOR_LM35
  (void)effective_duty; (void)effective_heat; (void)effective_fan; (void)dt_s;
  const float mv = adcToMillivolts(readAdcAveraged(PIN_TEMP));
  return mv / LM35_MV_PER_C;

#elif SENSOR_SOURCE == SENSOR_NTC
  (void)effective_duty; (void)effective_heat; (void)effective_fan; (void)dt_s;
  // Modulo NTC do Wokwi: 10k NTC em serie com 10k, beta = 3950.
  const int raw = readAdcAveraged(PIN_TEMP);
  const float ratio = static_cast<float>(ADC_MAX) / (raw > 0 ? raw : 1) - 1.0f;
  const float beta = 3950.0f;
  return 1.0f / (logf(1.0f / ratio) / beta + 1.0f / 298.15f) - 273.15f;

#else  // SENSOR_PLANT
  return g_plant.step(effective_duty, effective_heat, effective_fan, dt_s);
#endif
}

float readSetpointPot() {
  const int raw = readAdcAveraged(PIN_SETPOINT);
  if (raw < 10) return NAN;  // pot ausente / pino flutuando no zero
  const float frac = static_cast<float>(raw) / ADC_MAX;
  return SETPOINT_MIN_C + frac * (SETPOINT_MAX_C - SETPOINT_MIN_C);
}

void setAmbientC(float ambient_c) {
  g_ambient_c = ambient_c;
#if SENSOR_SOURCE == SENSOR_PLANT
  g_plant.setAmbient(ambient_c);
#endif
}

float ambientC() { return g_ambient_c; }

void setDoorOpen(bool open) {
#if SENSOR_SOURCE == SENSOR_PLANT
  g_plant.setDoorOpen(open);
#else
  (void)open;
#endif
}

bool doorOpen() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_plant.doorOpen();
#else
  return false;
#endif
}

float heaterSinkC() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_plant.heaterTemperature();
#else
  return NAN;
#endif
}

bool heaterTripped() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_plant.heaterTripped();
#else
  return false;
#endif
}

}  // namespace sensor
