/*
 * Mesmo formato do display do firmware (lib/control/seg7.cpp), para o
 * modulo TM1637 da cena 3D mostrar exatamente o que o Wokwi mostra.
 * Bits: a=0 ... g=6.
 */
const DIGITS = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F];
const MINUS = 0x40, C = 0x39, H = 0x76, I = 0x06, L = 0x38, O = 0x3F;
const cell = (bits, dp = false) => ({ bits, dp });

export function temperatureCells(c) {
  if (c === null || c === undefined || Number.isNaN(c)) return [cell(MINUS), cell(MINUS), cell(MINUS), cell(MINUS)];
  const tenths = Math.round(c * 10);
  if (tenths >= 1000) return [cell(H), cell(I), cell(0), cell(0)];
  if (tenths <= -100) return [cell(L), cell(O), cell(0), cell(0)];
  const neg = tenths < 0;
  const a = Math.abs(tenths);
  const tens = Math.floor(a / 100), units = Math.floor(a / 10) % 10, tenth = a % 10;
  const first = neg ? MINUS : tens === 0 ? 0 : DIGITS[tens];
  return [cell(first), cell(DIGITS[units], true), cell(DIGITS[tenth]), cell(C)];
}

export const errorCells = () => [cell(0x79), cell(0x50), cell(0x50), cell(0)];        // "Err "
export const batteryCells = () => [cell(0x7C), cell(0x77), cell(0x78), cell(0)];      // "bAt "

export const cellsKey = (cells) => cells.map((x) => x.bits + (x.dp ? 128 : 0)).join(',');
