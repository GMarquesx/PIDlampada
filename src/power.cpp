#include "power.h"
#include "config.h"
#include <Arduino.h>

#if SENSOR_SOURCE == SENSOR_PLANT
#include "battery_model.h"
static BatteryModel g_batt(BATT_CELLS, BATT_CAPACITY_WH, BATT_R_INT_OHM);
static bool g_on_battery = false;   // simulacao comeca na bancada (ATX)
#endif

static float g_v = VBAT_NOMINAL_V;
static float g_i = 0.0f;

namespace {

[[maybe_unused]] float readMillivolts(int pin) {
  long acc = 0;
  for (int i = 0; i < ADC_SAMPLES; ++i) {
    acc += analogRead(pin);
    delayMicroseconds(200);
  }
  return (static_cast<float>(acc) / ADC_SAMPLES / ADC_MAX) * ADC_VREF_MV;
}

float estimatedCurrent(float duty, float heat, float fan, float v) {
  if (v < 0.5f) return 0.0f;
  return duty * v / LAMP_R_EQ_OHM + heat * v / HEATER_R_OHM + (BASE_POWER_W + fan * FAN_POWER_W) / v;
}

}  // namespace

namespace power {

void begin() {
#if SENSOR_SOURCE != SENSOR_PLANT
  analogSetPinAttenuation(PIN_V_SENSE, ADC_11db);
  analogSetPinAttenuation(PIN_PWR_OK, ADC_11db);
#else
  g_batt.reset(1.0f);
#endif
}

void step(float duty, float heat, float fan, float dt_s) {
#if SENSOR_SOURCE == SENSOR_PLANT
  if (g_on_battery) {
    // Lampadas e manta sao resistivas e chaveadas juntas: para a bateria
    // equivalem a uma carga de condutancia duty/R_l + heat/R_h.
    const float g = duty / LAMP_R_EQ_OHM + heat / HEATER_R_OHM;
    const float base = BASE_POWER_W + fan * FAN_POWER_W;
    g_v = g > 0.0f ? g_batt.step(1.0f, 1.0f / g, base, dt_s)
                   : g_batt.step(0.0f, LAMP_R_EQ_OHM, base, dt_s);
    g_i = g_batt.current();
  } else {
    g_v = ATX_VOLTAGE_V;
    g_i = estimatedCurrent(duty, heat, fan, g_v);
  }
#else
  (void)dt_s;
  g_v = (readMillivolts(PIN_V_SENSE) / 1000.0f) * VBAT_DIVIDER;
  g_i = estimatedCurrent(duty, heat, fan, g_v);
#endif
}

float busVoltage() { return g_v; }
float currentA() { return g_i; }
float powerW() { return g_v * g_i; }

float stateOfCharge() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_on_battery ? g_batt.soc() : 1.0f;
#else
  // Estimativa grosseira pela tensao em carga: 3,0 V/celula = 0 %, 4,2 = 100 %.
  const float per_cell = g_v / BATT_CELLS;
  const float soc = (per_cell - 3.0f) / 1.2f;
  return soc < 0.0f ? 0.0f : (soc > 1.0f ? 1.0f : soc);
#endif
}

bool onBattery() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_on_battery;
#else
  return readMillivolts(PIN_PWR_OK) < 1500.0f;   // sem PWR_OK = sem ATX
#endif
}

bool cutoff() {
#if SENSOR_SOURCE == SENSOR_PLANT
  return g_on_battery && g_batt.cutoff();
#else
  return false;
#endif
}

void selectBattery(bool battery) {
#if SENSOR_SOURCE == SENSOR_PLANT
  g_on_battery = battery;
#else
  (void)battery;
#endif
}

void rechargeBattery() {
#if SENSOR_SOURCE == SENSOR_PLANT
  g_batt.reset(1.0f);
#endif
}

bool isSimulated() { return SENSOR_SOURCE == SENSOR_PLANT; }

}  // namespace power
