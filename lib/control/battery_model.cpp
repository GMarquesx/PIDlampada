#include "battery_model.h"

#include <math.h>

namespace {

// OCV tipica de uma celula 18650 NMC em repouso, por SoC.
constexpr int   kPts = 9;
constexpr float kSoc[kPts] = {0.00f, 0.05f, 0.10f, 0.20f, 0.40f, 0.60f, 0.80f, 0.90f, 1.00f};
constexpr float kOcv[kPts] = {3.00f, 3.30f, 3.45f, 3.58f, 3.68f, 3.78f, 3.93f, 4.05f, 4.20f};

// BMS 3S tipico desarma perto de 2,8 V por celula sob carga.
constexpr float kCutoffPerCell = 2.80f;

}  // namespace

BatteryModel::BatteryModel(int cells, float capacity_wh, float r_internal_ohm)
    : cells_(cells), capacity_j_(capacity_wh * 3600.0f), r_int_(r_internal_ohm) {
  reset(1.0f);
}

void BatteryModel::reset(float soc) {
  soc_ = soc < 0.0f ? 0.0f : (soc > 1.0f ? 1.0f : soc);
  cutoff_ = false;
  v_term_ = cells_ * ocvPerCell(soc_);
  i_total_ = 0.0f;
}

float BatteryModel::ocvPerCell(float soc) {
  if (soc <= kSoc[0]) return kOcv[0];
  if (soc >= kSoc[kPts - 1]) return kOcv[kPts - 1];
  for (int i = 1; i < kPts; ++i) {
    if (soc <= kSoc[i]) {
      const float f = (soc - kSoc[i - 1]) / (kSoc[i] - kSoc[i - 1]);
      return kOcv[i - 1] + f * (kOcv[i] - kOcv[i - 1]);
    }
  }
  return kOcv[kPts - 1];
}

float BatteryModel::step(float duty, float r_load_ohm, float base_power_w, float dt_s) {
  if (cutoff_) {
    v_term_ = 0.0f;
    i_total_ = 0.0f;
    return v_term_;
  }
  if (duty < 0.0f) duty = 0.0f;
  if (duty > 1.0f) duty = 1.0f;

  const float ocv = cells_ * ocvPerCell(soc_);

  // a*V^2 - OCV*V + R_int*P_base = 0,  com  a = 1 + R_int*duty/R_carga
  const float a = 1.0f + (r_load_ohm > 0.0f ? r_int_ * duty / r_load_ohm : 0.0f);
  const float disc = ocv * ocv - 4.0f * a * r_int_ * base_power_w;
  const float v = disc > 0.0f ? (ocv + sqrtf(disc)) / (2.0f * a) : ocv / (2.0f * a);

  const float i_load = r_load_ohm > 0.0f ? duty * v / r_load_ohm : 0.0f;
  const float i_base = v > 0.1f ? base_power_w / v : 0.0f;

  v_term_ = v;
  i_total_ = i_load + i_base;

  soc_ -= (ocv * i_total_ * dt_s) / capacity_j_;
  if (soc_ < 0.0f) soc_ = 0.0f;

  // A tabela satura em 3,0 V no SoC zero; na celula real a curva despenca
  // logo abaixo disso. Esgotar a carga, portanto, tambem desarma o BMS.
  if (soc_ <= 0.0f || v_term_ < kCutoffPerCell * cells_) {
    cutoff_ = true;
    v_term_ = 0.0f;
    i_total_ = 0.0f;
  }
  return v_term_;
}
