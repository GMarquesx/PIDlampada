#pragma once
/*
 * config.h - parametros de projeto em um lugar so.
 * Valores vindos da proposta e do esquema eletrico (docs/hardware/).
 */

// ---------------------------------------------------------------- pinagem
// Mantida identica ao esquema eletrico Rev. A.
constexpr int PIN_PWM_GATE = 25;  // LEDC -> gate do IRLZ44N
constexpr int PIN_TEMP     = 32;  // ADC1_CH4 <- LM35 (ou NTC no Wokwi)
constexpr int PIN_SETPOINT = 33;  // ADC1_CH5 <- potenciometro (opcional)
constexpr int PIN_V_SENSE  = 34;  // ADC1_CH6 <- divisor 100k/27k do barramento
constexpr int PIN_PWR_OK   = 35;  // ADC1_CH7 <- PWR_OK da fonte ATX
constexpr int PIN_LED_ST   = 2;   // LED de status (onboard na DevKit v1)
constexpr int PIN_BTN_MODE = 27;  // botao: alterna bancada / embarcado

// ------------------------------------------------------------------- PWM
constexpr int   PWM_CHANNEL    = 0;
constexpr int   PWM_FREQ_HZ    = 500;
constexpr int   PWM_RESOLUTION = 10;            // 0..1023
constexpr int   PWM_MAX        = (1 << PWM_RESOLUTION) - 1;
constexpr float SOFT_START_S   = 2.0f;          // rampa de partida (inrush)

// --------------------------------------------------------------- controle
constexpr float SETPOINT_DEFAULT_C = 45.0f;
constexpr float SETPOINT_MIN_C     = 25.0f;
constexpr float SETPOINT_MAX_C     = 60.0f;     // teto pratico do PMMA
constexpr float TEMP_CUTOFF_C      = 68.0f;     // corte por firmware (TH1 = 70)

constexpr float SAMPLE_PERIOD_S = 60.0f;        // periodo do PI (tau/10)

// SIMC (analise/identificacao.ipynb) sobre o ensaio de exemplo.
// PROVISORIO: refazer com o ensaio de degrau do hardware real.
constexpr float PI_KP = 0.0637f;                // 1/degC
constexpr float PI_KI = 0.000105f;              // 1/(degC*s)   Ti = 606 s

// ------------------------------------------------- modelo termico (planta)
// Levantados no projeto; confirmar com o ensaio de degrau em malha aberta.
constexpr float PLANT_TAU_S     = 640.0f;       // C/UA = 320/0.5
constexpr float PLANT_GAIN_C    = 30.0f;        // deltaT em regime com duty=1
constexpr float PLANT_AMBIENT_C = 25.0f;

// ------------------------------------------------------------- aquisicao
constexpr int   ADC_SAMPLES   = 16;             // media por leitura
constexpr float ADC_VREF_MV   = 3300.0f;
constexpr int   ADC_MAX       = 4095;
constexpr float LM35_MV_PER_C = 10.0f;

// --------------------------------------------- compensacao de alimentacao
constexpr float VBAT_NOMINAL_V  = 12.0f;
constexpr float VBAT_DIVIDER    = (100.0f + 27.0f) / 27.0f;  // R2/R3
constexpr bool  VBAT_COMPENSATE = true;

// ------------------------------------------------- selecao do sensor
#define SENSOR_LM35  1
#define SENSOR_NTC   2
#define SENSOR_PLANT 3

#ifndef SENSOR_SOURCE
#define SENSOR_SOURCE SENSOR_LM35
#endif

#ifndef SIM_TIME_SCALE
#define SIM_TIME_SCALE 1
#endif