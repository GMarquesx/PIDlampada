#pragma once
#include <stdint.h>

/*
 * Codificacao para display de 7 segmentos com 4 digitos e ponto decimal
 * (modulo TM1637). Bit 0 = segmento a ... bit 6 = g, bit 7 = ponto.
 *
 *        a
 *      f   b
 *        g
 *      e   c
 *        d   .
 *
 * Funcoes puras, sem Arduino: o formato do que aparece no display e'
 * testado no PC.
 */
namespace seg7 {

constexpr uint8_t DP = 0x80;

uint8_t digit(int d);          // 0..9; fora da faixa = apagado

// "43.2C"  - quatro posicoes: 4 | 3. | 2 | C
// "-5.0C", "HI", "LO" nos extremos; NAN vira "----".
void temperature(float celsius, uint8_t out[4]);

// Mensagens curtas de estado.
void error(uint8_t out[4]);        // "Err "
void batteryEmpty(uint8_t out[4]); // "bAt "
void dashes(uint8_t out[4]);       // "----"

}  // namespace seg7
