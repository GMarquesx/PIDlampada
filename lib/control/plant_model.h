#pragma once

/*
 * Modelo termico da camara, com ventoinha de exaustao e, opcionalmente,
 * a manta de silicone na base.
 *
 * Sem manta (primeira ordem, igual a Rev. B):
 *
 *   tau * dT/dt = K * duty - (1 + G * fan) * (T - T_amb)
 *
 * Com manta: a manta aquece o dissipador de aluminio da base, e e' ele
 * que aquece o ar. Isso cria um segundo no termico, com a sua propria
 * temperatura Th:
 *
 *   tau   * dT/dt  = K * lamps + r * (Th - T) - (1 + G * fan) * (T - T_amb)
 *   tau_h * dTh/dt = (Kh / r) * heater - (Th - T)
 *
 * K     = ganho das lampadas em degC para duty = 1, ventoinha parada
 * tau   = constante de tempo do ar e das paredes (capacidade / UA)
 * G     = quanto a ventoinha a 100 % multiplica a troca com o ambiente
 * Kh    = ganho da manta em degC no ar, em regime (30 W / 0,5 W/K = 60)
 * tau_h = constante de tempo do dissipador (capacidade / hA)
 * r     = hA / UA: quao bem o dissipador troca calor com o ar
 *
 * Em regime o dissipador fica Kh*heater/r acima do ar: e' esse atraso
 * (calor guardado no aluminio) que o controle precisa respeitar.
 *
 * TH2 (KSD301 no dissipador) tambem e' modelado: abre acima de trip_c e
 * so fecha de novo abaixo de reset_c, cortando a manta.
 *
 * A ventoinha so empurra a camara para o ambiente - nunca abaixo dele.
 * Os parametros devem ser substituidos pelos do ensaio de degrau real.
 */
class PlantModel {
 public:
  PlantModel(float tau_s, float gain_c, float ambient_c, float fan_gain = 3.0f);

  // Liga o segundo no (manta + dissipador). Sem esta chamada o modelo e'
  // exatamente o de primeira ordem.
  void setHeater(float gain_c, float tau_s, float coupling = 1.0f,
                 float trip_c = 100.0f, float reset_c = 85.0f);

  void  reset(float temperature_c);
  // duties em [0,1], dt em segundos. Retorna a nova temperatura do ar.
  float step(float lamps, float heater, float fan, float dt);
  float step(float duty, float fan, float dt) { return step(duty, 0.0f, fan, dt); }
  float step(float duty, float dt) { return step(duty, 0.0f, 0.0f, dt); }

  float temperature() const { return temp_c_; }
  float heaterTemperature() const { return sink_c_; }
  bool  hasHeater() const { return has_heater_; }
  bool  heaterTripped() const { return tripped_; }
  void  setAmbient(float ambient_c) { ambient_c_ = ambient_c; }
  float ambient() const { return ambient_c_; }

  static constexpr int kSubSteps = 6;   // integracao com a manta

 private:
  float tau_s_, gain_c_, ambient_c_, fan_gain_;
  float temp_c_;
  bool  has_heater_ = false;
  float heater_gain_ = 0.0f, heater_tau_ = 1.0f, coupling_ = 1.0f;
  float trip_c_ = 100.0f, reset_c_ = 85.0f;
  float sink_c_;
  bool  tripped_ = false;
};
