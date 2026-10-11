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
}

float PIController::update(float setpoint, float measurement, float dt) {
  if (dt <= 0.0f) return clampf(kp_ * (setpoint - measurement) + ki_ * integral_,
                                u_min_, u_max_);

  const float error = setpoint - measurement;

  // Candidato considerando a integral que teriamos ao acumular agora.
  const float integral_try = integral_ + error * dt;
  const float u_try = kp_ * error + ki_ * integral_try;
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
