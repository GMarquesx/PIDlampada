#pragma once

/*
 * Controlador PI com anti-windup por clamping condicional.
 *
 * Puro C++: nao depende de Arduino, por isso roda nos testes unitarios
 * do ambiente "native" (pio test -e native).
 *
 *   u(t) = Kp*e(t) + Ki*integral(e)      saturado em [u_min, u_max]
 *
 * O termo integral so acumula quando a saida NAO esta saturada no sentido
 * do erro - evita o windup classico em partidas longas.
 */
class PIController {
 public:
  PIController(float kp, float ki, float u_min = 0.0f, float u_max = 1.0f);

  void  setGains(float kp, float ki);
  void  setLimits(float u_min, float u_max);
  void  reset(float integral = 0.0f);

  // dt em segundos. Retorna a acao de controle ja saturada.
  float update(float setpoint, float measurement, float dt);

  float kp() const { return kp_; }
  float ki() const { return ki_; }
  float integral() const { return integral_; }
  float lastError() const { return last_error_; }
  bool  saturated() const { return saturated_; }

 private:
  float kp_, ki_;
  float u_min_, u_max_;
  float integral_ = 0.0f;
  float last_error_ = 0.0f;
  bool  saturated_ = false;
};
