#include "display.h"
#include "config.h"
#include <Arduino.h>

namespace {

constexpr uint8_t kCmdData    = 0x40;   // escrita, endereco auto-incrementado
constexpr uint8_t kCmdAddress = 0xC0;   // endereco 0
constexpr uint8_t kCmdDisplay = 0x88;   // display ligado | brilho

inline void bitDelay() { delayMicroseconds(5); }

void startCondition() {
  pinMode(PIN_DISP_DIO, OUTPUT);
  digitalWrite(PIN_DISP_CLK, HIGH);
  digitalWrite(PIN_DISP_DIO, HIGH);
  bitDelay();
  digitalWrite(PIN_DISP_DIO, LOW);
  bitDelay();
}

void stopCondition() {
  digitalWrite(PIN_DISP_CLK, LOW);
  bitDelay();
  digitalWrite(PIN_DISP_DIO, LOW);
  bitDelay();
  digitalWrite(PIN_DISP_CLK, HIGH);
  bitDelay();
  digitalWrite(PIN_DISP_DIO, HIGH);
  bitDelay();
}

bool writeByte(uint8_t b) {
  for (int i = 0; i < 8; ++i) {
    digitalWrite(PIN_DISP_CLK, LOW);
    bitDelay();
    digitalWrite(PIN_DISP_DIO, (b & 0x01) ? HIGH : LOW);
    bitDelay();
    digitalWrite(PIN_DISP_CLK, HIGH);
    bitDelay();
    b >>= 1;
  }
  // 9o pulso: o TM1637 confirma puxando DIO para baixo.
  digitalWrite(PIN_DISP_CLK, LOW);
  pinMode(PIN_DISP_DIO, INPUT_PULLUP);
  bitDelay();
  digitalWrite(PIN_DISP_CLK, HIGH);
  bitDelay();
  const bool ack = digitalRead(PIN_DISP_DIO) == LOW;
  digitalWrite(PIN_DISP_CLK, LOW);
  pinMode(PIN_DISP_DIO, OUTPUT);
  bitDelay();
  return ack;
}

void command(uint8_t c) {
  startCondition();
  writeByte(c);
  stopCondition();
}

}  // namespace

namespace display {

void begin() {
  pinMode(PIN_DISP_CLK, OUTPUT);
  pinMode(PIN_DISP_DIO, OUTPUT);
  digitalWrite(PIN_DISP_CLK, HIGH);
  digitalWrite(PIN_DISP_DIO, HIGH);
}

void show(const uint8_t segments[4]) {
  command(kCmdData);

  startCondition();
  writeByte(kCmdAddress);
  for (int i = 0; i < 4; ++i) writeByte(segments[i]);
  stopCondition();

  command(static_cast<uint8_t>(kCmdDisplay | (DISPLAY_BRIGHTNESS & 0x07)));
}

}  // namespace display
