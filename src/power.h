#pragma once

/*
 * Alimentacao: tensao do barramento, corrente, potencia e estado da fonte.
 *
 * Hardware real: tensao medida pelo divisor R2/R3; presenca da ATX pelo
 * PWR_OK. A CORRENTE E' ESTIMADA (duty * V / R_lampadas + manta + cooler + base) -
 * o circuito nao tem sensor de corrente. Para medir de verdade, acrescente
 * um INA219 no barramento.
 *
 * Simulacao (SENSOR_PLANT): fonte ATX ideal de 12 V ou pack 3S modelado em
 * lib/control/battery_model, selecionavel em tempo de execucao.
 */
namespace power {

void begin();

// Avanca um intervalo com os duties aplicados (lampadas, manta e cooler).
// Na simulacao descarrega a bateria; no hardware apenas le o ADC.
void step(float duty, float heat, float fan, float dt_s);

float busVoltage();     // V
float currentA();       // A medios (estimado no hardware)
float powerW();         // W entregues ao barramento
float stateOfCharge();  // 0..1 (estimado pela OCV no hardware)
bool  onBattery();
bool  cutoff();         // BMS desarmou por subtensao

// So tem efeito na simulacao - no hardware quem decide e' a chave SW1.
void selectBattery(bool battery);
void rechargeBattery();

bool isSimulated();

}  // namespace power
