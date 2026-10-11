#include <unity.h>
#include "pi_controller.h"
#include "plant_model.h"
#include "battery_model.h"
#include "split_range.h"
#include "seg7.h"
#include <string.h>

void setUp() {}
void tearDown() {}

// Erro zero com integral zerada -> saida zero.
void test_zero_error_gives_zero_output() {
  PIController pi(0.05f, 0.001f);
  TEST_ASSERT_FLOAT_WITHIN(1e-6, 0.0f, pi.update(40.0f, 40.0f, 1.0f));
}

// Acao proporcional pura (Ki = 0).
void test_proportional_only() {
  PIController pi(0.02f, 0.0f);
  // erro = 10 -> u = 0.2
  TEST_ASSERT_FLOAT_WITHIN(1e-4, 0.2f, pi.update(45.0f, 35.0f, 1.0f));
}

// Saida saturada no limite superior.
void test_output_is_clamped() {
  PIController pi(1.0f, 0.0f);
  TEST_ASSERT_FLOAT_WITHIN(1e-6, 1.0f, pi.update(60.0f, 20.0f, 1.0f));
  TEST_ASSERT_TRUE(pi.saturated());
}

// Anti-windup: com erro grande e saida saturada, a integral nao deve crescer.
void test_antiwindup_blocks_integral_growth() {
  PIController pi(1.0f, 0.5f);
  for (int i = 0; i < 100; ++i) pi.update(60.0f, 20.0f, 1.0f);
  TEST_ASSERT_TRUE(pi.integral() < 1.0f);
}

// Malha fechada contra o modelo: deve convergir para o setpoint.
void test_closed_loop_converges() {
  PIController pi(0.04f, 0.0005f);
  PlantModel plant(640.0f, 30.0f, 25.0f);
  const float dt = 60.0f, sp = 45.0f;
  float duty = 0.0f;
  for (int i = 0; i < 400; ++i) {  // ~6,6 h de modelo
    const float t = plant.step(duty, dt);
    duty = pi.update(sp, t, dt);
  }
  TEST_ASSERT_FLOAT_WITHIN(0.5f, sp, plant.temperature());
}

// Ganho estatico do modelo: duty = 1 -> T_amb + K.
void test_plant_static_gain() {
  PlantModel plant(640.0f, 30.0f, 25.0f);
  for (int i = 0; i < 2000; ++i) plant.step(1.0f, 60.0f);
  TEST_ASSERT_FLOAT_WITHIN(0.1f, 55.0f, plant.temperature());
}


// ---------------------------------------------------------------- bateria
// Pack cheio, sem carga: tensao = 3 x 4,20 V.
void test_battery_full_open_circuit() {
  BatteryModel b(3, 33.3f, 0.15f);
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 12.6f, b.step(0.0f, 9.6f, 0.0f, 1.0f));
}

// Sob carga a tensao cai pela resistencia interna (I*R).
void test_battery_sags_under_load() {
  BatteryModel b(3, 33.3f, 0.15f);
  const float v = b.step(1.0f, 9.6f, 0.0f, 1.0f);
  // V = 12,6 / (1 + 0,15/9,6) = 12,406 V
  TEST_ASSERT_FLOAT_WITHIN(0.01f, 12.406f, v);
}

// Energia: 15 W por 1 h tira ~15 Wh de um pack de 33,3 Wh.
void test_battery_energy_balance() {
  BatteryModel b(3, 33.3f, 0.15f);
  for (int i = 0; i < 60; ++i) b.step(1.0f, 9.6f, 0.0f, 60.0f);
  // potencia cai junto com a tensao, entao fica um pouco abaixo de 15 Wh
  const float usado_wh = (1.0f - b.soc()) * 33.3f;
  TEST_ASSERT_TRUE(usado_wh > 12.0f && usado_wh < 16.5f);
}

// Descarga ate o fim: o BMS abre e a tensao vai a zero.
void test_battery_cutoff() {
  BatteryModel b(3, 33.3f, 0.15f);
  for (int i = 0; i < 500 && !b.cutoff(); ++i) b.step(1.0f, 9.6f, 0.9f, 60.0f);
  TEST_ASSERT_TRUE(b.cutoff());
  TEST_ASSERT_FLOAT_WITHIN(1e-6, 0.0f, b.voltage());
}

// ---------------------------------------------------------------- cooler
// Com a ventoinha a 100 % (G = 3), a perda para o ambiente fica 4x maior.
void test_fan_cools_faster() {
  PlantModel sem(640.0f, 30.0f, 25.0f), com(640.0f, 30.0f, 25.0f);
  sem.reset(55.0f); com.reset(55.0f);
  for (int i = 0; i < 10; ++i) { sem.step(0.0f, 0.0f, 60.0f); com.step(0.0f, 1.0f, 60.0f); }
  TEST_ASSERT_TRUE(com.temperature() < sem.temperature() - 5.0f);
  TEST_ASSERT_TRUE(com.temperature() > 25.0f);   // nunca abaixo do ambiente
}

// Faixa dividida: lampadas e cooler nunca ligados juntos.
void test_split_range_exclusive() {
  SplitRange sr;
  for (int i = -100; i <= 100; ++i) {
    float lamps, fan;
    sr.update(i / 100.0f, lamps, fan);
    TEST_ASSERT_FALSE(lamps > 0.0f && fan > 0.0f);
  }
}

// Rotacao minima e histerese: liga acima de 10 %, desliga abaixo de 4 %.
void test_split_range_hysteresis() {
  SplitRange sr(0.30f, 0.10f, 0.04f);
  float lamps, fan;
  sr.update(-0.08f, lamps, fan); TEST_ASSERT_FLOAT_WITHIN(1e-6, 0.0f, fan);   // abaixo do limiar
  sr.update(-0.12f, lamps, fan); TEST_ASSERT_TRUE(fan >= 0.30f);              // liga ja na minima
  sr.update(-0.06f, lamps, fan); TEST_ASSERT_TRUE(fan >= 0.30f);              // segue ligado
  sr.update(-0.02f, lamps, fan); TEST_ASSERT_FLOAT_WITHIN(1e-6, 0.0f, fan);   // agora desliga
}

// Mesma configuracao do firmware: feedforward pelo modelo + separacao integral.
static float ff_of(float sp) { return (sp - 25.0f) / 30.0f; }

// Baixar o setpoint de 50 para 32 degC: o cooler acelera bastante a descida.
static int minutes_to_reach(bool use_fan, float* lowest) {
  PIController pi(0.0637f, 0.000105f, use_fan ? -1.0f : 0.0f, 1.0f);
  pi.setIntegralBand(3.0f);
  PlantModel plant(640.0f, 30.0f, 25.0f);
  SplitRange sr(0.30f, 0.10f, 0.04f, 4.0f);  // mesmos parametros do config.h
  float lamps = 0, fan = 0;
  for (int i = 0; i < 300; ++i) {            // aquece e estabiliza em 50
    const float t = plant.step(lamps, fan, 60.0f);
    sr.update(pi.update(50.0f, t, 60.0f, ff_of(50.0f)), lamps, fan);
  }
  int reached = 999;
  *lowest = 99.0f;
  for (int i = 0; i < 300; ++i) {
    const float t = plant.step(lamps, fan, 60.0f);
    if (t < *lowest) *lowest = t;
    if (reached == 999 && t <= 32.5f) reached = i;
    sr.update(pi.update(32.0f, t, 60.0f, ff_of(32.0f)), lamps, fan);
  }
  return reached;
}

void test_fan_speeds_up_setpoint_drop() {
  float low_sem, low_com;
  const int sem = minutes_to_reach(false, &low_sem), com = minutes_to_reach(true, &low_com);
  TEST_ASSERT_TRUE(com * 3 <= sem * 2);       // pelo menos 1,5x mais rapido
  TEST_ASSERT_TRUE(low_com > 31.5f);          // e sem afundar abaixo do alvo
}

// Feedforward: sem ele, as lampadas voltam a acender muito acima do alvo.
void test_feedforward_avoids_early_relight() {
  PIController pi(0.0637f, 0.000105f, 0.0f, 1.0f);
  PlantModel plant(640.0f, 30.0f, 25.0f);
  float u = 0;
  for (int i = 0; i < 300; ++i) u = pi.update(50.0f, plant.step(u, 60.0f), 60.0f);
  float relit = -1;
  for (int i = 0; i < 120 && relit < 0; ++i) {
    const float t = plant.step(u, 60.0f);
    u = pi.update(32.0f, t, 60.0f);
    if (i > 0 && u > 0.0f) relit = t;
  }
  TEST_ASSERT_TRUE(relit > 40.0f);   // PI puro reacende a ~43 degC: o defeito que o ff corrige
}

// Separacao integral nao pode travar: modelo errado e alvo perto do limite.
void test_integral_band_does_not_lock() {
  PIController pi(0.0637f, 0.000105f, -1.0f, 1.0f);
  pi.setIntegralBand(3.0f);
  PlantModel plant(640.0f, 24.0f, 21.0f);    // planta real mais fraca e ambiente mais frio
  SplitRange sr;
  float lamps = 0, fan = 0;
  for (int i = 0; i < 600; ++i) {
    const float t = plant.step(lamps, fan, 60.0f);
    sr.update(pi.update(42.0f, t, 60.0f, ff_of(42.0f)), lamps, fan);
  }
  TEST_ASSERT_FLOAT_WITHIN(0.2f, 42.0f, plant.temperature());
}

// ------------------------------------------------------------- 7 segmentos
void test_seg7_temperature_format() {
  uint8_t o[4];
  seg7::temperature(43.24f, o);  // "43.2C"
  TEST_ASSERT_EQUAL_HEX8(seg7::digit(4), o[0]);
  TEST_ASSERT_EQUAL_HEX8(seg7::digit(3) | seg7::DP, o[1]);
  TEST_ASSERT_EQUAL_HEX8(seg7::digit(2), o[2]);
  TEST_ASSERT_EQUAL_HEX8(0x39, o[3]);
  seg7::temperature(8.46f, o);   // " 8.5C": sem zero a esquerda
  TEST_ASSERT_EQUAL_HEX8(0x00, o[0]);
  TEST_ASSERT_EQUAL_HEX8(seg7::digit(5), o[2]);
  seg7::temperature(99.96f, o);  // arredonda para 100,0 -> "HI"
  TEST_ASSERT_EQUAL_HEX8(0x76, o[0]);
  seg7::temperature(-5.0f, o);   // "-5.0C"
  TEST_ASSERT_EQUAL_HEX8(0x40, o[0]);
}

// ---------------------------------------------------------------- manta
static PlantModel plant_com_manta() {
  PlantModel p(640.0f, 30.0f, 25.0f, 3.0f);
  p.setHeater(60.0f, 300.0f, 1.0f, 100.0f, 85.0f);
  p.reset(25.0f);
  return p;
}

// Ganho de regime: lampadas + manta somam (30 + 60 degC com duty 1).
void test_heater_static_gain() {
  PlantModel p = plant_com_manta();
  for (int i = 0; i < 2000; ++i) p.step(0.3f, 0.3f, 0.0f, 60.0f);
  TEST_ASSERT_FLOAT_WITHIN(0.2f, 25.0f + 0.3f * 90.0f, p.temperature());
  // dissipador acima do ar em Kh*duty/r = 18 degC
  TEST_ASSERT_FLOAT_WITHIN(0.2f, 18.0f, p.heaterTemperature() - p.temperature());
}

// O calor da manta chega atrasado: no primeiro minuto rende menos que as
// lampadas, apesar de ser o dobro da potencia.
void test_heater_is_delayed() {
  PlantModel a(640.0f, 30.0f, 25.0f, 3.0f), b = plant_com_manta();
  a.step(1.0f, 0.0f, 0.0f, 60.0f);
  b.step(0.0f, 1.0f, 0.0f, 60.0f);
  TEST_ASSERT_TRUE(b.temperature() - 25.0f < a.temperature() - 25.0f);
  TEST_ASSERT_TRUE(b.heaterTemperature() > b.temperature());
}

// TH2: dissipador acima de 100 degC abre a manta; so fecha abaixo de 85.
void test_heater_thermostat_trips() {
  PlantModel p = plant_com_manta();
  bool abriu = false;
  for (int i = 0; i < 200 && !abriu; ++i) {
    p.step(0.0f, 1.0f, 0.0f, 60.0f);
    abriu = p.heaterTripped();
  }
  TEST_ASSERT_TRUE(abriu);
  TEST_ASSERT_TRUE(p.heaterTemperature() > 90.0f);   // ja esfriando sem a manta
  bool fechou = false;
  float menor = p.heaterTemperature();
  for (int i = 0; i < 200 && !fechou; ++i) {
    p.step(0.0f, 1.0f, 0.0f, 60.0f);
    fechou = !p.heaterTripped();
    if (!fechou && p.heaterTemperature() < menor) menor = p.heaterTemperature();
  }
  TEST_ASSERT_TRUE(fechou);
  TEST_ASSERT_TRUE(menor < 85.0f);                    // so religou abaixo de 85
}

// Malha fechada 25 -> 45 degC: com a manta chega pelo menos 1,5x mais rapido
// que a Rev. B (so lampadas, sem dissipador),
// sem passar de 1 degC do alvo, e alcanca 60 degC (so lampadas: ~55).
static int minutos_ate(PlantModel& p, bool manta, float sp, float* pico) {
  PIController pi(0.0637f, 0.000105f, -1.0f, 1.0f);
  pi.setIntegralBand(3.0f);
  SplitRange sr(0.30f, 0.10f, 0.04f, 4.0f);
  const float k = manta ? 90.0f : 30.0f;
  float lamps = 0, fan = 0, t = p.temperature();
  int chegou = -1;
  *pico = t;
  for (int min = 0; min < 120; ++min) {
    t = p.step(lamps, manta ? lamps : 0.0f, fan, 60.0f);
    if (t > *pico) *pico = t;
    if (chegou < 0 && t >= sp - 0.5f) chegou = min;
    const float ff = (sp - 25.0f) / k;
    sr.update(pi.update(sp, t, 60.0f, ff > 1.0f ? 1.0f : ff), lamps, fan);
  }
  return chegou;
}

void test_heater_speeds_up_warmup() {
  PlantModel com = plant_com_manta(), sem(640.0f, 30.0f, 25.0f, 3.0f);
  float pico_com, pico_sem;
  const int t_com = minutos_ate(com, true, 45.0f, &pico_com);
  const int t_sem = minutos_ate(sem, false, 45.0f, &pico_sem);
  TEST_ASSERT_TRUE(t_com > 0 && t_sem > 0);
  TEST_ASSERT_TRUE(t_com * 3 <= t_sem * 2);
  TEST_ASSERT_TRUE(pico_com < 46.0f);
  TEST_ASSERT_FALSE(com.heaterTripped());
}

void test_heater_reaches_60() {
  PlantModel com = plant_com_manta(), sem(640.0f, 30.0f, 25.0f, 3.0f);
  float pico_com, pico_sem;
  TEST_ASSERT_TRUE(minutos_ate(com, true, 60.0f, &pico_com) > 0);
  TEST_ASSERT_TRUE(minutos_ate(sem, false, 60.0f, &pico_sem) < 0);   // so lampadas nao chega
  TEST_ASSERT_TRUE(pico_com < 61.0f);
  TEST_ASSERT_TRUE(com.heaterTemperature() < 100.0f);                // TH2 nao abre
}

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_zero_error_gives_zero_output);
  RUN_TEST(test_proportional_only);
  RUN_TEST(test_output_is_clamped);
  RUN_TEST(test_antiwindup_blocks_integral_growth);
  RUN_TEST(test_closed_loop_converges);
  RUN_TEST(test_plant_static_gain);
  RUN_TEST(test_battery_full_open_circuit);
  RUN_TEST(test_battery_sags_under_load);
  RUN_TEST(test_battery_energy_balance);
  RUN_TEST(test_battery_cutoff);
  RUN_TEST(test_fan_cools_faster);
  RUN_TEST(test_split_range_exclusive);
  RUN_TEST(test_split_range_hysteresis);
  RUN_TEST(test_fan_speeds_up_setpoint_drop);
  RUN_TEST(test_feedforward_avoids_early_relight);
  RUN_TEST(test_integral_band_does_not_lock);
  RUN_TEST(test_seg7_temperature_format);
  RUN_TEST(test_heater_static_gain);
  RUN_TEST(test_heater_is_delayed);
  RUN_TEST(test_heater_thermostat_trips);
  RUN_TEST(test_heater_speeds_up_warmup);
  RUN_TEST(test_heater_reaches_60);
  return UNITY_END();
}
