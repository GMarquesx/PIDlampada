#include "plant_model.h"

namespace {
inline float clamp01(float v) { return v < 0.0f ? 0.0f : (v > 1.0f ? 1.0f : v); }
}  // namespace

PlantModel::PlantModel(float tau_s, float gain_c, float ambient_c, float fan_gain)
    : tau_s_(tau_s), gain_c_(gain_c), ambient_c_(ambient_c), fan_gain_(fan_gain),
      temp_c_(ambient_c) {}

void PlantModel::reset(float temperature_c) { temp_c_ = temperature_c; }

float PlantModel::step(float duty, float fan, float dt) {
  if (tau_s_ <= 0.0f) return temp_c_;
  duty = clamp01(duty);
  fan = clamp01(fan);

  // Euler explicito. Estavel enquanto dt*(1+G)/tau < 1: com dt = 60 s,
  // tau = 640 s e G = 3 da 0,375 - folga confortavel.
  const float loss = (1.0f + fan_gain_ * fan) * (temp_c_ - ambient_c_);
  temp_c_ += (dt / tau_s_) * (gain_c_ * duty - loss);
  return temp_c_;
}
