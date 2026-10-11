#pragma once

/*
 * Modelo simples de pack Li-ion em serie alimentando uma carga resistiva
 * chaveada por PWM.
 *
 *   V_term = OCV(SoC) - I * R_int
 *   I      = duty * V_term / R_carga + P_base / V_term
 *
 * As duas equacoes juntas dao uma quadratica em V_term, resolvida em
 * forma fechada. A energia retirada da quimica e' OCV * I * dt.
 *
 * Simplificacoes assumidas (e aceitaveis para o proposito do painel):
 *  - curva OCV x SoC tabelada e linear por trechos, sem histerese
 *  - R_int constante (na pratica sobe a frio e no fim da descarga)
 *  - corrente media do PWM; o pico real e' V/R durante o tempo ligado
 *  - resistencia do filamento constante (a frio ela e' ~1/10 da quente)
 *
 * Puro C++, sem Arduino: roda nos testes do ambiente native.
 */
class BatteryModel {
 public:
  BatteryModel(int cells, float capacity_wh, float r_internal_ohm);

  void reset(float soc = 1.0f);

  // duty em [0,1]; r_load_ohm e' a carga com duty 100 %; base_power_w e'
  // a carga fixa (ESP32). Retorna a tensao nos terminais.
  float step(float duty, float r_load_ohm, float base_power_w, float dt_s);

  float voltage() const { return v_term_; }
  float current() const { return i_total_; }
  float soc() const { return soc_; }
  bool  cutoff() const { return cutoff_; }   // BMS abriu por subtensao

  static float ocvPerCell(float soc);

 private:
  int   cells_;
  float capacity_j_;
  float r_int_;
  float soc_ = 1.0f;
  float v_term_ = 0.0f;
  float i_total_ = 0.0f;
  bool  cutoff_ = false;
};
