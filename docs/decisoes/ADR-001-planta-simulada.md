# ADR-001 — Planta termica simulada em firmware para o Wokwi

**Data:** 2026-10-10
**Status:** aceito

## Contexto

O Wokwi nao possui modelo termico: nao simula lampada incandescente, MOSFET
de potencia nem troca de calor. Tambem nao tem a peca LM35 — os sensores de
temperatura disponiveis sao NTC analogico, DS18B20, DHT22 e BMP180.

Sem planta, o Wokwi so provaria que o firmware compila e escreve PWM. Nao
daria para observar sobressinal, tempo de acomodacao nem erro em regime, que
sao exatamente os resultados exigidos no item 9 da proposta.

## Decisao

Introduzir uma camada de aquisicao (`src/sensor.*`) com tres origens
selecionadas em tempo de compilacao por `SENSOR_SOURCE`:

| Valor | Ambiente | Origem da temperatura |
|-------|----------|------------------------|
| `SENSOR_LM35`  | `env:esp32dev`   | ADC1 lendo o LM35 real |
| `SENSOR_NTC`   | `env:wokwi_ntc`  | NTC do Wokwi, ajustado na tela |
| `SENSOR_PLANT` | `env:wokwi`      | Modelo de 1a ordem em `lib/control/plant_model` |

O modelo e a lei de controle ficam em `lib/control/`, em C++ puro, sem
dependencia de Arduino — o que permite rodar a malha fechada inteira nos
testes unitarios do ambiente `native`.

## Consequencias

**Positivas**
- A mesma fonte roda no simulador e no hardware; muda so o flag de build.
- Permite sintonizar o PI antes de o hardware existir.
- A malha fechada vira caso de teste automatizado no CI.

**Negativas**
- Os parametros do modelo (`tau`, ganho) sao estimativas de projeto ate o
  ensaio de degrau real. Devem ser substituidos pelos medidos.
- Validar no simulador nao substitui validar no hardware: ruido de ADC,
  nao-linearidade do filamento e perdas reais nao estao no modelo.
