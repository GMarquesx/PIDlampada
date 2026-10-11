#pragma once

/*
 * Controle em faixa dividida (split-range).
 *
 * Um unico PI, com saida u em [-1, 1], comanda dois atuadores opostos:
 *
 *   u > 0  ->  lampadas = u            (aquecer)
 *   u < 0  ->  cooler   = |u|          (exaurir o ar quente)
 *
 * Os dois nunca ligam juntos: aquecer e ventilar ao mesmo tempo so
 * desperdica energia, porque a ventoinha joga fora o calor das lampadas.
 *
 * Do lado do cooler ha dois cuidados de hardware:
 *  - rotacao minima: abaixo de ~30 % de PWM uma ventoinha de 12 V para ou
 *    nem parte. O comando e' remapeado para [min, 1].
 *  - histerese: liga acima de on_threshold e desliga abaixo de
 *    off_threshold. Sem isso, perto de u = 0 o cooler ficaria ligando e
 *    desligando a cada amostra.
 *
 * Ganho proprio do lado frio (fan_scale): lampadas e cooler sao atuadores
 * fisicamente diferentes, e com o Kp sintonizado para as lampadas o cooler
 * so reagiria a erros grandes. A demanda do cooler e' |u| * fan_scale.
 *
 * Puro C++, sem Arduino: testado no ambiente native.
 */
class SplitRange {
 public:
  SplitRange(float fan_min = 0.30f, float on_threshold = 0.10f, float off_threshold = 0.04f,
             float fan_scale = 1.0f);

  // u em [-1, 1]. Escreve lamps e fan em [0, 1].
  void update(float u, float& lamps, float& fan);

  void reset() { fan_on_ = false; }
  bool fanOn() const { return fan_on_; }

 private:
  float fan_min_, on_th_, off_th_, fan_scale_;
  bool  fan_on_ = false;
};
