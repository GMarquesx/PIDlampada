#pragma once

// Acionamento das lampadas via LEDC/MOSFET, com rampa de partida.
namespace actuator {

void begin();

// duty em [0,1] - ja com a compensacao de tensao aplicada pelo chamador.
void setDuty(float duty);

float duty();

// Corta a saida imediatamente (falha de sensor, sobretemperatura).
void shutdown();

// Rampa de 0 ate o duty alvo, para limitar o inrush do filamento frio.
void softStart(float target_duty);

}  // namespace actuator
