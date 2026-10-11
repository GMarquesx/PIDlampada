#pragma once
#include <stdint.h>

/*
 * Display TM1637 de 4 digitos com ponto decimal.
 *
 * Driver proprio, sem biblioteca: o protocolo e' curto (parecido com I2C,
 * sem endereco, bits LSB primeiro) e assim fica claro o que vai no fio.
 *
 *   start   DIO desce com CLK alto
 *   byte    8 bits, LSB primeiro, amostrados na subida de CLK
 *   ack     o TM1637 puxa DIO para baixo no 9o pulso
 *   stop    DIO sobe com CLK alto
 *
 * Sequencia de uma atualizacao:
 *   0x40           dados, endereco auto-incrementado
 *   0xC0 d0..d3    a partir do endereco 0 (digito mais a esquerda)
 *   0x88 | brilho  liga o display, brilho 0..7
 *
 * No hardware real alimente o modulo com 3,3 V: os pull-ups do modulo vao
 * no VCC, e o ESP32 nao tolera 5 V no DIO.
 */
namespace display {

void begin();
void show(const uint8_t segments[4]);   // codificados por lib/control/seg7

}  // namespace display
