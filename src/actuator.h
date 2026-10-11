#pragma once

// Acionamento das lampadas, da manta e do cooler via LEDC/MOSFET.
namespace actuator {

void begin();

// Lampadas: duty em [0,1] - ja com a compensacao de tensao aplicada.
void setDuty(float duty);
float duty();

// Manta de silicone: duty em [0,1], ja compensado. Canal 1, mesmo timer
// das lampadas.
void setHeater(float duty);
float heater();

// Cooler: duty em [0,1]. A rotacao minima e a histerese ficam no
// SplitRange; aqui e' so o PWM.
void setFan(float duty);
float fan();

// Corta lampadas e manta imediatamente (falha de sensor, sobretemperatura).
void shutdown();

// Rampa de 0 ate o duty alvo, para limitar o inrush do filamento frio.
void softStart(float target_duty);

}  // namespace actuator
