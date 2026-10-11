#pragma once

/*
 * Modelo termico de primeira ordem da camara.
 *
 *   tau * dT/dt = -(T - T_amb) + K * duty
 *
 * K  = ganho estatico em degC para duty = 1 (potencia total / UA)
 * tau = constante de tempo em segundos (capacidade termica / UA)
 *
 * Usado para rodar a malha fechada no Wokwi sem hardware. Os parametros
 * devem ser substituidos pelos extraidos do ensaio de degrau real.
 */
class PlantModel {
 public:
  PlantModel(float tau_s, float gain_c, float ambient_c);

  void  reset(float temperature_c);
  // duty em [0,1], dt em segundos. Retorna a nova temperatura.
  float step(float duty, float dt);

  float temperature() const { return temp_c_; }
  void  setAmbient(float ambient_c) { ambient_c_ = ambient_c; }

 private:
  float tau_s_, gain_c_, ambient_c_;
  float temp_c_;
};
