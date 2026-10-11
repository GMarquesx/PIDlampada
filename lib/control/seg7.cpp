#include "seg7.h"
#include <math.h>

namespace {
constexpr uint8_t kDigits[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F};
constexpr uint8_t kMinus = 0x40;
constexpr uint8_t kC = 0x39;
constexpr uint8_t kH = 0x76, kI = 0x06, kL = 0x38, kO = 0x3F;
constexpr uint8_t kE = 0x79, kr = 0x50, kb = 0x7C, kA = 0x77, kt = 0x78;
}  // namespace

namespace seg7 {

uint8_t digit(int d) { return (d >= 0 && d <= 9) ? kDigits[d] : 0x00; }

void dashes(uint8_t out[4]) { out[0] = out[1] = out[2] = out[3] = kMinus; }

void error(uint8_t out[4]) { out[0] = kE; out[1] = kr; out[2] = kr; out[3] = 0; }

void batteryEmpty(uint8_t out[4]) { out[0] = kb; out[1] = kA; out[2] = kt; out[3] = 0; }

void temperature(float c, uint8_t out[4]) {
  if (isnan(c)) { dashes(out); return; }

  // Arredonda para um decimal antes de decidir o formato: 99,96 vira 100,0.
  long tenths = lroundf(c * 10.0f);

  if (tenths >= 1000) { out[0] = kH; out[1] = kI; out[2] = 0; out[3] = 0; return; }
  if (tenths <= -100) { out[0] = kL; out[1] = kO; out[2] = 0; out[3] = 0; return; }

  out[3] = kC;
  const bool neg = tenths < 0;
  const long a = neg ? -tenths : tenths;   // 0..999
  const int d_tens  = static_cast<int>(a / 100);
  const int d_units = static_cast<int>((a / 10) % 10);
  const int d_tenth = static_cast<int>(a % 10);

  out[2] = digit(d_tenth);
  out[1] = static_cast<uint8_t>(digit(d_units) | DP);
  if (neg)              out[0] = kMinus;            // -5.0C (faixa -9,9..-0,1)
  else if (d_tens == 0) out[0] = 0;                 // " 8.5C" sem zero a esquerda
  else                  out[0] = digit(d_tens);
}

}  // namespace seg7
