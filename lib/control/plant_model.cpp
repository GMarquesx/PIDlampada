#include "plant_model.h"

namespace {
inline float clamp01(float v) { return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v); }
}  // namespace

PlantModel::PlantModel(float tau_s, float gain_c, float ambient_c, float fan_gain)
    : tau_s_(tau_s), gain_c_(gain_c), ambient_c_(ambient_c), fan_gain_(fan_gain),
      temp_c_(ambient_c), sink_c_(ambient_c) {}

void PlantModel::setHeater(float gain_c, float tau_s, float coupling, float trip_c, float reset_c,
                           bool trip_cuts_all) {
  trip_all_ = trip_cuts_all;
  has_heater_ = gain_c > 0.0f && tau_s > 0.0f && coupling > 0.0f;
  heater_gain_ = gain_c;
  heater_tau_ = tau_s;
  coupling_ = coupling;
  trip_c_ = trip_c;
  reset_c_ = reset_c;
}

void PlantModel::reset(float temperature_c) {
  temp_c_ = temperature_c;
  sink_c_ = temperature_c;
  tripped_ = false;
}

float PlantModel::step(float lamps, float heater, float fan, float dt) {
  if (tau_s_ <= 0.0f) return temp_c_;
  lamps = clamp01(lamps);
  heater = clamp01(heater);
  fan = clamp01(fan);

  if (!has_heater_) {
    // Euler explicito. Estavel enquanto dt*(1+G)/tau < 1: com dt = 60 s,
    // tau = 640 s e G = 3 da 0,375 - folga confortavel.
    const float loss = (1.0f + fan_gain_ * fan + (door_open_ ? door_gain_ : 0.0f)) * (temp_c_ - ambient_c_);
    temp_c_ += (dt / tau_s_) * (gain_c_ * lamps - loss);
    return temp_c_;
  }

  // TH2: bimetal no dissipador, com histerese.
  if (sink_c_ > trip_c_) tripped_ = true;
  else if (sink_c_ < reset_c_) tripped_ = false;
  if (tripped_) {
    heater = 0.0f;
    if (trip_all_) lamps = 0.0f;
  }

  // Dois nos acoplados: passos menores para a troca ar <-> dissipador.
  const float h = dt / kSubSteps;
  for (int i = 0; i < kSubSteps; ++i) {
    const float q = coupling_ * (sink_c_ - temp_c_);
    const float loss = (1.0f + fan_gain_ * fan + (door_open_ ? door_gain_ : 0.0f)) * (temp_c_ - ambient_c_);
    const float d_air = (gain_c_ * lamps + q - loss) / tau_s_;
    const float d_sink = ((heater_gain_ / coupling_) * heater - (sink_c_ - temp_c_)) / heater_tau_;
    temp_c_ += h * d_air;
    sink_c_ += h * d_sink;
  }
  return temp_c_;
}
