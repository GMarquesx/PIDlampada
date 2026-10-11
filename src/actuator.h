#pragma once

// Acionamento das lampadas e do cooler via LEDC/MOSFET.
namespace actuator {

void begin();

// Lampadas: duty em [0,1] - ja com a compensacao de tensao aplicada.
void setDuty(float duty);
float duty();

// Cooler: duty em [0,1]. A rotacao minima e a histerese ficam no
// SplitRange; aqui e' so o PWM.
void setFan(float duty);
float fan();

// Corta as lampadas imediatamente (falha de sensor, sobretemperatura).
void shutdown();

// Rampa de 0 ate o duty alvo, para limitar o inrush do filamento frio.
void softStart(float target_duty);

}  // namespace actuator
