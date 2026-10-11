#pragma once

// Camada fina de aquisicao de temperatura. A implementacao muda conforme
// SENSOR_SOURCE, mas a interface vista pelo main.cpp e' sempre esta.
namespace sensor {

void begin();

// Temperatura em degC. No modo PLANT, a potencia aplicada no intervalo
// anterior realimenta o modelo - por isso os duties das lampadas, da manta
// e do cooler entram como argumento (ja corrigidos pela tensao).
float readTemperatureC(float effective_duty, float effective_heat, float effective_fan, float dt_s);

// Temperatura do dissipador da manta e estado do TH2. So existem na
// simulacao: no hardware nao ha sensor no dissipador (NAN / false).
float heaterSinkC();
bool  heaterTripped();

// Setpoint vindo do potenciometro; retorna NAN se nao houver pot ligado.
float readSetpointPot();

// Temperatura ambiente do modelo (so tem efeito no modo PLANT). Serve para
// simular uma perturbacao: alguem abriu a janela, ligou o ar-condicionado.
void  setAmbientC(float ambient_c);
float ambientC();

}  // namespace sensor
