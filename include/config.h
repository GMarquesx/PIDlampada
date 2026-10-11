#pragma once
#include <stdint.h>
/*
 * config.h - parametros de projeto em um lugar so.
 * Valores vindos da proposta e do esquema eletrico (docs/hardware/).
 */

// ---------------------------------------------------------------- pinagem
// Igual ao esquema eletrico Rev. C (docs/hardware/Esquema_Eletrico_Rev_C.pdf).
constexpr int PIN_PWM_GATE = 25;  // LEDC -> gate do IRLZ44N
constexpr int PIN_TEMP     = 32;  // ADC1_CH4 <- LM35 (ou NTC no Wokwi)
constexpr int PIN_SETPOINT = 33;  // ADC1_CH5 <- potenciometro (opcional)
constexpr int PIN_V_SENSE  = 34;  // ADC1_CH6 <- divisor 100k/27k do barramento
constexpr int PIN_PWR_OK   = 35;  // ADC1_CH7 <- PWR_OK da fonte ATX
constexpr int PIN_LED_ST   = 2;   // LED de status (onboard na DevKit v1)
constexpr int PIN_BTN_MODE = 13;  // botao (reservado)
constexpr int PIN_HEAT_GATE = 27; // LEDC -> gate do MOSFET da manta (Q3)
constexpr int PIN_FAN      = 26;  // LEDC -> gate do MOSFET do cooler (Q2)
constexpr int PIN_DISP_CLK = 18;  // TM1637 CLK
constexpr int PIN_DISP_DIO = 19;  // TM1637 DIO

// ------------------------------------------------------------------- PWM
constexpr int   PWM_CHANNEL    = 0;
constexpr int   PWM_FREQ_HZ    = 500;
constexpr int   PWM_RESOLUTION = 10;            // 0..1023
constexpr int   PWM_MAX        = (1 << PWM_RESOLUTION) - 1;
constexpr float SOFT_START_S   = 2.0f;          // rampa de partida (inrush)

// Manta: canal 1, de proposito no MESMO timer das lampadas (par 0-1):
// mesma frequencia e resolucao, e as duas recebem o mesmo comando.
constexpr int   HEAT_PWM_CHANNEL = 1;

// Cooler: 25 kHz fica acima da faixa audivel (sem chiado do motor).
// Canal 2, nao 1: no LEDC do ESP32 os canais andam em pares (0-1, 2-3...)
// que dividem o mesmo timer. No canal 1 os 25 kHz do cooler mudariam
// tambem a frequencia das lampadas.
constexpr int   FAN_PWM_CHANNEL    = 2;
constexpr int   FAN_PWM_FREQ_HZ    = 25000;
constexpr int   FAN_PWM_RESOLUTION = 8;         // 0..255
constexpr int   FAN_PWM_MAX        = (1 << FAN_PWM_RESOLUTION) - 1;

// Faixa dividida: rotacao minima de partida e histerese (split_range.h).
constexpr float FAN_MIN_DUTY = 0.30f;
constexpr float FAN_ON_TH    = 0.10f;
constexpr float FAN_OFF_TH   = 0.04f;
// Ganho proprio do lado frio: com o Kp das lampadas o cooler desligaria
// ainda 4 degC acima do alvo. Com 4x, a queda de 45 para 32 degC cai de
// 13 para 7 min, sem passar do alvo (medido em lib/control nos testes).
constexpr float FAN_GAIN_SCALE = 4.0f;

// --------------------------------------------------------------- controle
constexpr float SETPOINT_DEFAULT_C = 45.0f;
constexpr float SETPOINT_MIN_C     = 25.0f;
constexpr float SETPOINT_MAX_C     = 60.0f;     // teto pratico do PMMA
constexpr float TEMP_CUTOFF_C      = 68.0f;     // corte por firmware (TH1 = 70)

constexpr float SAMPLE_PERIOD_S = 60.0f;        // periodo do PI (tau/10)

// SIMC (analise/identificacao.ipynb) sobre o ensaio de exemplo.
// PROVISORIO: refazer com o ensaio de degrau do hardware real.
// Com a manta o ganho triplica (30 -> 90 degC), mas o dissipador acrescenta
// ~300 s de atraso; em simulacao os mesmos ganhos continuam os melhores
// (25 -> 45 degC em 8 min, pico de +0,7 degC). Quem muda e' o
// feedforward, que usa o ganho total.
constexpr float PI_KP = 0.0637f;                // 1/degC
constexpr float PI_KI = 0.000105f;              // 1/(degC*s)   Ti = 606 s

// Controle de 2 graus de liberdade: feedforward pelo modelo identificado
// mais o PI no erro. Com ele, baixar o setpoint de 50 para 32 degC cai de
// 26 para 7 min, e as lampadas nao reacendem 13 degC acima do alvo.
constexpr bool  SETPOINT_FEEDFORWARD = true;
// Separacao integral: a integral so acumula com |erro| <= banda (ou com a
// temperatura parada - ver pi_controller.h).
constexpr float PI_INTEGRAL_BAND_C = 3.0f;

// O potenciometro so assume o setpoint quando e' mexido mais que isto.
// Sem essa histerese ele sobrescreveria, a cada amostra, o setpoint
// enviado pela serial ou pelo painel web.
constexpr float POT_DEADBAND_C = 0.5f;

// ------------------------------------------------- modelo termico (planta)
// Levantados no projeto; confirmar com o ensaio de degrau em malha aberta.
constexpr float PLANT_TAU_S     = 640.0f;       // C/UA = 320/0.5
constexpr float PLANT_GAIN_C    = 30.0f;        // deltaT em regime com duty=1
constexpr float PLANT_AMBIENT_C = 25.0f;
// Cooler a 100 % multiplica por (1 + G) a troca de calor com o ambiente.
constexpr float PLANT_FAN_GAIN  = 3.0f;

// Manta de silicone 12 V / 30 W colada sob um dissipador de aluminio
// aletado (100 x 100 mm), com isolante embaixo. Ver plant_model.h.
//   ganho  : 30 W / 0,5 W/K = 60 degC no ar com duty = 1
//   tau_h  : ~150 J/K do dissipador / hA ~0,5 W/K = 300 s
//   r      : hA / UA ~ 1
// Estimativas de projeto: medir com o ensaio de degrau (r com a manta).
constexpr float PLANT_HEATER_GAIN_C = 60.0f;
constexpr float PLANT_HEATER_TAU_S  = 300.0f;
constexpr float PLANT_HEATER_COUPLING = 1.0f;
// TH2 (KSD301 NF no dissipador): abre a 100 degC, fecha de novo a ~85.
constexpr float HEATER_TRIP_C  = 100.0f;
constexpr float HEATER_RESET_C = 85.0f;

// ------------------------------------------------------- carga (lampadas)
constexpr int   LAMP_COUNT   = 3;
constexpr float LAMP_POWER_W = 5.0f;            // W5W
constexpr float LAMP_V_NOM   = 12.0f;
// Resistencia equivalente a quente das tres em paralelo: 12^2 / 15 = 9,6 ohms.
constexpr float LAMP_R_EQ_OHM = (LAMP_V_NOM * LAMP_V_NOM) / (LAMP_COUNT * LAMP_POWER_W);
// ESP32 com Wi-Fi + perdas do buck, vistos do barramento de 12 V.
constexpr float BASE_POWER_W = 0.9f;
// Ventoinha 12 V 40 x 40 mm tipica: ~0,1 A na rotacao maxima.
constexpr float FAN_POWER_W  = 1.2f;

// --------------------------------------------------------- carga (manta)
constexpr bool  HEATER_ENABLED_DEFAULT = true;  // comando 'm 0' desliga
constexpr float HEATER_POWER_W = 30.0f;
constexpr float HEATER_R_OHM   = (LAMP_V_NOM * LAMP_V_NOM) / HEATER_POWER_W;   // 4,8 ohms
// Ensaio de degrau com a manta: duty 1 levaria a ~115 degC em regime e
// dispararia o corte de 68 degC antes de dar para medir a constante de
// tempo. Com 0,4 o regime fica em ~61 degC.
constexpr float STEP_TEST_DUTY_HEATER = 0.4f;

// ---------------------------------------------------------------- display
constexpr uint8_t DISPLAY_BRIGHTNESS = 4;       // 0..7

// ---------------------------------------------- bateria 3S (so simulacao)
constexpr int   BATT_CELLS       = 3;
constexpr float BATT_CAPACITY_WH = 33.3f;       // 3 x 18650 de 3000 mAh
constexpr float BATT_R_INT_OHM   = 0.15f;       // pack inteiro
constexpr float ATX_VOLTAGE_V    = 12.0f;

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

// ------------------------------------------------------------------ rede
// No Wokwi a rede Wokwi-GUEST e' aberta e no canal 6 (pular o scan
// economiza ~4 s). No hardware real, as credenciais vem de secrets.h, que
// fica fora do git - copie include/secrets.example.h para comecar.
#if defined(WOKWI)
  #define WIFI_SSID    "Wokwi-GUEST"
  #define WIFI_PASS    ""
  #define WIFI_CHANNEL 6
#elif __has_include("secrets.h")
  #include "secrets.h"
#endif

#ifndef WIFI_CHANNEL
  #define WIFI_CHANNEL 0                        // 0 = varre todos os canais
#endif

#if defined(WIFI_SSID)
  #define NET_ENABLED 1
#else
  #define NET_ENABLED 0                         // sem credenciais: so serial
#endif

// Broker publico: qualquer um que conheca o topico le e escreve. Serve para
// demonstracao; o firmware limita setpoint e duty, entao um comando
// malicioso nao consegue levar a camara a uma condicao insegura.
#ifndef MQTT_HOST
  #define MQTT_HOST "broker.hivemq.com"
#endif
#ifndef MQTT_PORT
  #define MQTT_PORT 1883
#endif
#ifndef MQTT_DEVICE_ID
  #define MQTT_DEVICE_ID "gmarques-01"          // precisa bater com o painel
#endif
#define MQTT_BASE_TOPIC "pidlampada/" MQTT_DEVICE_ID
