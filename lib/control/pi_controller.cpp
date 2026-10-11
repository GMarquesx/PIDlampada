#include "pi_controller.h"

namespace {
inline float clampf(float v, float lo, float hi) {
  return v < lo ? lo : (v > hi ? hi : v);
}
}  // namespace

PIController::PIController(float kp, float ki, float u_min, float u_max)
    : kp_(kp), ki_(ki), u_min_(u_min), u_max_(u_max) {}

void PIController::setGains(float kp, float ki) {
  kp_ = kp;
  ki_ = ki;
}

void PIController::setLimits(float u_min, float u_max) {
  u_min_ = u_min;
  u_max_ = u_max;
}

void PIController::reset(float integral) {
  integral_ = integral;
  last_error_ = 0.0f;
  saturated_ = false;
  has_last_ = false;
  has_sp_ = false;
  still_count_ = 0;
}

float PIController::update(float setpoint, float measurement, float dt, float ff) {
  if (dt <= 0.0f) return clampf(ff + kp_ * (setpoint - measurement) + ki_ * integral_,
                                u_min_, u_max_);

  const float error = setpoint - measurement;

  // Separacao integral: longe do alvo e ainda em movimento, a integral
  // fica parada. Estabilizou longe do alvo? Entao e' erro de regime.
  const float rate = has_last_ ? (measurement - last_meas_) / dt : 1e9f;
  last_meas_ = measurement;
  has_last_ = true;
  // "Parado" precisa durar algumas amostras: logo depois de uma mudanca de
  // setpoint a temperatura ainda nao reagiu e tambem parece parada.
  const bool still = (rate <= settle_rate_ && rate >= -settle_rate_);
  const bool sp_changed = has_sp_ && (setpoint - last_sp_ > 0.05f || last_sp_ - setpoint > 0.05f);
  last_sp_ = setpoint;
  has_sp_ = true;
  if (sp_changed || !still) still_count_ = 0;
  else if (still_count_ < 255) ++still_count_;
  const bool settled = still_count_ >= kSettleSamples;
  // Correndo para o alvo: o erro esta diminuindo rapido sozinho. Integrar
  // agora so acumularia um erro que vai sumir - e que depois sobra como
  // sobressinal. (erro > 0 e T subindo, ou erro < 0 e T descendo.)
  const bool approaching = (error > 0.0f && rate > approach_rate_) ||
                           (error < 0.0f && rate < -approach_rate_);
  const bool near = (error <= band_ && error >= -band_) && !approaching;
  const bool in_band = (band_ <= 0.0f) || near || settled;

  // Candidato considerando a integral que teriamos ao acumular agora.
  const float integral_try = in_band ? integral_ + error * dt : integral_;
  const float u_try = ff + kp_ * error + ki_ * integral_try;
  const float u = clampf(u_try, u_min_, u_max_);

  // Anti-windup: so acumula se nao esta empurrando contra a saturacao.
  const bool pushing_up   = (u_try > u_max_) && (error > 0.0f);
  const bool pushing_down = (u_try < u_min_) && (error < 0.0f);
  if (!pushing_up && !pushing_down) {
    integral_ = integral_try;
  }

  saturated_ = (u_try != u);
  last_error_ = error;
  return u;
}
