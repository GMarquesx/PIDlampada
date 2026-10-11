#pragma once

/*
 * Modelo termico de primeira ordem da camara, com ventoinha de exaustao.
 *
 *   tau * dT/dt = K * duty - (1 + G * fan) * (T - T_amb)
 *
 * K   = ganho estatico em degC para duty = 1, ventoinha parada
 * tau = constante de tempo em segundos (capacidade termica / UA)
 * G   = quanto a ventoinha a 100 % multiplica a troca de calor. Com G = 3,
 *       a perda para o ambiente fica 4x maior: a camara esfria 4x mais
 *       rapido e, se as lampadas ficassem ligadas junto, o ganho de
 *       aquecimento cairia para K/4. Por isso o controle nunca liga os dois
 *       ao mesmo tempo (ver split_range.h).
 *
 * A ventoinha so empurra a camara para o ambiente - nunca abaixo dele.
 *
 * Usado para rodar a malha fechada no Wokwi sem hardware. Os parametros
 * devem ser substituidos pelos extraidos do ensaio de degrau real.
 */
class PlantModel {
 public:
  PlantModel(float tau_s, float gain_c, float ambient_c, float fan_gain = 3.0f);

  void  reset(float temperature_c);
  // duty e fan em [0,1], dt em segundos. Retorna a nova temperatura.
  float step(float duty, float fan, float dt);
  float step(float duty, float dt) { return step(duty, 0.0f, dt); }

  float temperature() const { return temp_c_; }
  void  setAmbient(float ambient_c) { ambient_c_ = ambient_c; }
  float ambient() const { return ambient_c_; }

 private:
  float tau_s_, gain_c_, ambient_c_, fan_gain_;
  float temp_c_;
};
