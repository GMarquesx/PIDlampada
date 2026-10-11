#include "plant_model.h"

PlantModel::PlantModel(float tau_s, float gain_c, float ambient_c)
    : tau_s_(tau_s), gain_c_(gain_c), ambient_c_(ambient_c), temp_c_(ambient_c) {}

void PlantModel::reset(float temperature_c) { temp_c_ = temperature_c; }

float PlantModel::step(float duty, float dt) {
  if (tau_s_ <= 0.0f) return temp_c_;
  if (duty < 0.0f) duty = 0.0f;
  if (duty > 1.0f) duty = 1.0f;

  // Euler explicito; dt << tau, entao e' estavel e suficiente aqui.
  const float target = ambient_c_ + gain_c_ * duty;
  temp_c_ += (dt / tau_s_) * (target - temp_c_);
  return temp_c_;
}
