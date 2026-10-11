#pragma once
#include <stdint.h>

// Camada fina de aquisicao. A implementacao muda conforme SENSOR_SOURCE,
// mas a interface vista pelo main.cpp e' sempre esta.
namespace sensor {

void  begin();

// Temperatura em degC. No modo PLANT, o duty do ciclo anterior realimenta
// o modelo - por isso ele entra como argumento.
float readTemperatureC(float last_duty, float dt_s);

// Tensao do barramento (divisor R2/R3). No modo simulado retorna o nominal.
float readBusVoltage();

// true quando a fonte ATX esta presente (PWR_OK alto).
bool  atxPresent();

// Setpoint vindo do potenciometro; retorna NAN se nao houver pot ligado.
float readSetpointPot();

}  // namespace sensor
