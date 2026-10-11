#pragma once

/*
 * Controlador PI com anti-windup por clamping condicional.
 *
 * Puro C++: nao depende de Arduino, por isso roda nos testes unitarios
 * do ambiente "native" (pio test -e native).
 *
 *   u(t) = ff + Kp*e(t) + Ki*integral(e)      saturado em [u_min, u_max]
 *
 * O termo integral so acumula quando a saida NAO esta saturada no sentido
 * do erro - evita o windup classico em partidas longas.
 *
 * ff e' um feedforward opcional (2 graus de liberdade): a acao que o modelo
 * diz ser necessaria para segurar o setpoint. Com ele a integral so carrega
 * o erro do modelo, e uma mudanca grande de setpoint nao fica presa a
 * "memoria" do ponto de operacao antigo.
 *
 * Separacao integral (setIntegralBand): a integral so acumula quando
 * |erro| <= banda. Em mudancas grandes de setpoint o feedforward e o termo
 * proporcional fazem o trabalho, e a integral nao junta erro durante o
 * transitorio - e' esse erro acumulado que causaria passar do alvo.
 *
 * A armadilha classica da separacao integral e' travar: se o modelo esta
 * errado e a temperatura estabiliza fora da banda, a integral nunca volta e
 * o erro fica permanente. Por isso ela tambem acumula quando a medida para
 * de variar (|dT/dt| abaixo de settle_rate): parado longe do alvo nao e'
 * transitorio, e' erro de regime - exatamente o que a integral corrige.
 */
class PIController {
 public:
  PIController(float kp, float ki, float u_min = 0.0f, float u_max = 1.0f);

  void  setGains(float kp, float ki);
  void  setLimits(float u_min, float u_max);
  // band em degC (0 = desligada); taxas em degC/s.
  static constexpr float APPROACH_RATE_DEFAULT = 0.004f;   // 0,24 degC/min
  void  setIntegralBand(float band, float settle_rate = 0.0005f,
                        float approach_rate = APPROACH_RATE_DEFAULT) {
    band_ = band;
    settle_rate_ = settle_rate;
    approach_rate_ = approach_rate;
  }
  void  reset(float integral = 0.0f);

  // dt em segundos. Retorna a acao de controle ja saturada.
  float update(float setpoint, float measurement, float dt, float feedforward = 0.0f);

  float kp() const { return kp_; }
  float ki() const { return ki_; }
  float integral() const { return integral_; }
  float lastError() const { return last_error_; }
  bool  saturated() const { return saturated_; }

 private:
  float kp_, ki_;
  float u_min_, u_max_;
  float band_ = 0.0f;
  float settle_rate_ = 0.0005f;
  float approach_rate_ = APPROACH_RATE_DEFAULT;
  float last_meas_ = 0.0f;
  bool  has_last_ = false;
  unsigned char still_count_ = 0;
  float last_sp_ = 0.0f;
  bool  has_sp_ = false;
  static constexpr unsigned char kSettleSamples = 4;
  float integral_ = 0.0f;
  float last_error_ = 0.0f;
  bool  saturated_ = false;
};
