#include <unity.h>
#include "pi_controller.h"
#include "plant_model.h"

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

int main(int, char**) {
  UNITY_BEGIN();
  RUN_TEST(test_zero_error_gives_zero_output);
  RUN_TEST(test_proportional_only);
  RUN_TEST(test_output_is_clamped);
  RUN_TEST(test_antiwindup_blocks_integral_growth);
  RUN_TEST(test_closed_loop_converges);
  RUN_TEST(test_plant_static_gain);
  return UNITY_END();
}
