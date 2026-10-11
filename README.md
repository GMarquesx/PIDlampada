# PIDlampada — Camara Termica com Controle PWM

Camara termica de policarbonato de 250 x 250 x 250 mm (13,8 L por dentro)
aquecida por cinco lampadas automotivas W5W no teto e por uma manta de
silicone de 80 W no piso, sob dois dissipadores aletados e uma prateleira de
aluminio perfurado. O controlador PI roda num ESP32 e atua por PWM atraves de
MOSFETs. Lampadas e manta recebem o mesmo comando, entao o brilho das lampadas
**e** o sinal de controle: quanto mais aceso, mais frio esta o interior. Um
cooler de exaustao de 80 mm joga o ar quente para fora quando o setpoint fica
abaixo da temperatura medida, e um display de 7 segmentos (TM1637) mostra a
leitura na propria camara.

Componentes baratos e faceis de achar, mas com controle de estufa de verdade:
feedforward, faixa dividida aquecer/esfriar, cadeia de seguranca com dois
termostatos e rele, e corte por firmware. Setpoint de ate 70 degC.

**Painel ao vivo:** https://gmarquesx.github.io/PIDlampada/ — abre no celular,
mostra a camara em 3D com as lampadas no brilho real do PWM e permite mudar o
setpoint. Sem a simulacao rodando, use `?demo=1` no fim do endereco.

Projeto Integrador — Engenharia de Computacao, UNIP Sao Jose dos Campos, 8o
semestre / 2026.

---

## Sumario

- [Arquitetura](#arquitetura)
- [Comecando](#comecando)
- [Ambientes de build](#ambientes-de-build)
- [Simulando no Wokwi](#simulando-no-wokwi)
- [Cooler e controle em faixa dividida](#cooler-e-controle-em-faixa-dividida)
- [Camara de policarbonato (Rev. D)](#camara-de-policarbonato-rev-d)
- [Painel web](#painel-web)
- [Protocolo serial e MQTT](#protocolo-serial-e-mqtt)
- [Ensaio de degrau](#ensaio-de-degrau)
- [Testes](#testes)
- [Analise e sintonia](#analise-e-sintonia)
- [Hardware](#hardware)
- [Limitacoes conhecidas](#limitacoes-conhecidas)

---

## Arquitetura

```
PIDlampada/
├── include/config.h            parametros de projeto (pinos, ganhos, limites)
├── lib/control/                C++ puro, sem Arduino — testavel no PC
│   ├── pi_controller.{h,cpp}   PI com feedforward, separacao de integral e anti-windup
│   ├── split_range.{h,cpp}     um PI, dois atuadores: lampadas (u>0) e cooler (u<0)
│   ├── plant_model.{h,cpp}     modelo termico de dois nos (ar e dissipador) com ventilacao
│   ├── battery_model.{h,cpp}   pack 3S2P com resistencia interna e BMS
│   └── seg7.{h,cpp}            formato do display ("43.2C", "Err ", "bAt ")
├── src/
│   ├── main.cpp                maquina de estados, CSV, comandos
│   ├── sensor.{h,cpp}          LM35 | NTC do Wokwi | planta simulada
│   ├── power.{h,cpp}           tensao, corrente, fonte ATX/bateria
│   ├── net.{h,cpp}             Wi-Fi + MQTT (nunca bloqueia o controle)
│   ├── display.{h,cpp}         driver TM1637 proprio (bit-bang, sem biblioteca)
│   └── actuator.{h,cpp}        LEDC: lampadas (ch0) e manta (ch1) a 500 Hz, cooler (ch2, 25 kHz)
├── web/                        painel (three.js + mqtt.js), publicado no Pages
├── test/test_control/          testes unitarios (Unity)
├── analise/                    identificacao da planta e sintonia (Python)
├── diagram.json                circuito do Wokwi
├── wokwi.toml                  aponta para o firmware do env "wokwi"
└── docs/
    ├── hardware/               esquema eletrico Rev. D, desenho mecanico, proposta, scripts
    ├── ensaios/                CSVs capturados da serial
    └── decisoes/               ADRs
```

A lei de controle e o modelo da planta nao dependem do Arduino. Isso e' de
proposito: permite rodar a malha fechada inteira como teste unitario no PC,
sem hardware e sem simulador.

## Comecando

Pre-requisitos: Git, Python 3.11+, VS Code, [gh CLI](https://cli.github.com/).

```powershell
git clone https://github.com/<usuario>/PIDlampada.git
cd PIDlampada
pip install --upgrade platformio
code .
```

O VS Code vai sugerir as extensoes recomendadas (PlatformIO e Wokwi). Aceite.

Depois, ative a licenca do Wokwi uma unica vez: `F1` -> **Wokwi: Request a New
License**. A licenca e' gratuita e vale 30 dias; renove com o mesmo comando.

## Ambientes de build

| Env | Sensor | Escala de tempo | Para que serve |
|-----|--------|-----------------|----------------|
| `esp32dev` | LM35 no ADC1 | 1x (real) | Hardware |
| `wokwi` | planta simulada | 60x | Validar a malha fechada sem hardware |
| `wokwi_ntc` | NTC do Wokwi | 10x | Testar o caminho de aquisicao |
| `native` | — | — | Testes unitarios no PC |

```powershell
pio run -e wokwi          # compila para o simulador
pio run -e esp32dev       # compila para a placa
pio run -e esp32dev -t upload
pio test -e native        # testes unitarios
```

## Simulando no Wokwi

```powershell
pio run -e wokwi
```

Depois `F1` -> **Wokwi: Start Simulator**. A cada rebuild o Wokwi recarrega o
firmware sozinho.

O `wokwi.toml` aponta para `firmware.merged.bin` — a imagem completa da flash
(bootloader + tabela de particoes + aplicacao), gerada automaticamente por
`scripts/merge_bin.py`. Apontar para `firmware.bin` puro causa boot loop.

Com `SIM_TIME_SCALE=60`, um ensaio de uma hora de modelo roda em um minuto de
parede.

O circuito do Wokwi tem:

| Peca | Pino | O que mostra |
|------|------|--------------|
| Display TM1637 4 digitos | CLK GPIO18, DIO GPIO19, VCC 3V3 | a temperatura lida, `43.2C`; `Err` em falha, `bAt` com bateria esgotada |
| LED "LAMPADAS" | GPIO25 | brilho = PWM das lampadas |
| LED azul "COOLER" | GPIO26 | brilho = PWM do cooler |
| LED vermelho "MANTA" | GPIO27 | brilho = PWM da manta (o mesmo das lampadas) |
| Potenciometro | GPIO33 | setpoint |

**Limite do Wokwi:** ele simula logica digital, nao circuito analogico — nao
tem MOSFET, diodo, capacitor nem motor DC. Por isso o cooler aparece como LED
e as protecoes (diodo de roda livre, capacitores de desacoplamento, filtro do
LM35, termostatos, rele) estao no esquema Rev. D, em [`docs/hardware/`](docs/hardware/). O
firmware e' o mesmo nos dois casos.

## Cooler e controle em faixa dividida

As lampadas so aquecem. Sem outro atuador, baixar o setpoint de 45 para 32 degC
significa esperar a camara perder calor sozinha pelas paredes. O cooler de
exaustao (80 mm, 12 V) troca o ar de dentro pelo de fora e acelera isso.

Um unico PI comanda os dois (`lib/control/split_range.cpp`):

```
u em [-1, 1]
  u > 0  -> lampadas = u              cooler parado
  u < 0  -> lampadas = 0              cooler = 30 % + 70 % * min(1, 4|u|)
```

- **Nunca os dois juntos:** ventilar com as lampadas acesas so joga energia fora.
- **Rotacao minima de 30 %:** abaixo disso uma ventoinha de 12 V nem parte.
- **Histerese:** liga com demanda > 0,10, desliga < 0,04 — sem isso o cooler
  ficaria ligando e desligando perto do alvo.
- **Ganho proprio do lado frio (x6, `FAN_GAIN_SCALE`):** com o Kp das
  lampadas, o cooler so reagiria a erros enormes.
- **O cooler nao esfria abaixo do ambiente.** Ele troca ar; quem gera frio
  e' o ar de fora. O painel avisa quando o alvo fica abaixo do ambiente.
- **Em falha** (T > 78 degC) lampadas e manta apagam e o cooler vai a 100 %.

So o split-range nao bastou. A integral, acumulada em 45 degC, mantinha as
lampadas acesas em 43 degC na descida. Tres mudancas no PI resolveram, todas
cobertas por teste unitario:

1. **Feedforward do setpoint:** `ff = (sp - T_amb) / K`, o duty que o modelo
   diz ser necessario em regime. A integral so corrige o que o modelo erra.
2. **Separacao da integral:** so integra a menos de 3 degC do alvo, ou quando
   a temperatura ja parou de mexer (evita erro permanente se o modelo errar).
3. **Nao integra enquanto ja esta chegando** ao alvo rapido o bastante.

Resultado na planta da Rev. B (camara de acrilico, tau 640 s, K 30 degC),
descida de 45 para 32 degC, quando estas mudancas entraram:

| Versao | Tempo ate o alvo |
|--------|------------------|
| PI original, sem cooler | 31 min |
| PI original + cooler | 26 min |
| PI + feedforward + separacao da integral + cooler | **7 min**, minimo de 31,9 degC |

A partida a frio continua chegando a 45 degC em cerca de 15 min, com pico de
45,08 degC, e a resposta a perturbacao de ambiente nao mudou. Na camara de
policarbonato da Rev. D, a descida de 70 para 35 degC leva 8 min.

## Camara de policarbonato (Rev. D)

A camara compacta de acrilico (Rev. A a C) tinha pouca area util e o acrilico
limitava o setpoint a 60 degC. A Rev. D troca tudo por uma caixa de
**policarbonato compacto cristal de 6 mm**, cortada de uma chapa de
1000 x 1000 mm (o plano de corte esta no desenho PIDL-MEC-001):

```
      tampa de PC  ->  refletor + 5 lampadas W5W
            ar     ->  LM35 a ~75 mm da prateleira, TH1 sob a tampa
  prateleira de aluminio perfurado a 70 mm do piso (amostras em cima)
  M2 60 mm no fundo  ->  2 dissipadores aletados 200 x 100 (TH2 na ponta)
      manta H1 200 x 200, 80 W  ->  isolante de fibra ceramica
                      base de MDF 300 x 300 x 15
```

- **Por que PC:** aguenta uso continuo ate ~115 degC (acrilico amolece perto de
  80) e nao estilhaca. Cantoneiras de aluminio por fora nas 8 arestas fixas,
  parafusos M4 inox com furos de 5 mm (folga para a dilatacao do PC) e nada de
  cola de solvente, que trinca o PC.
- **Prateleira sobre os dissipadores:** o piso fica livre para as amostras.
  A ventoinha de circulacao M2, sempre ligada, sopra ao longo das aletas e o ar
  quente sobe pelos furos da prateleira.
- **Fluxo de ar do cooler:** entra pelas 18 frestas de 8 mm na lateral esquerda,
  embaixo, e sai pelo cooler M1 de 80 mm na lateral direita, em cima.
- **Potencia:** a caixa grande perde ~1,6 W/K (contra ~0,5 da compacta) e tem
  constante de tempo de ~1000 s. As cinco lampadas (25 W) sozinhas so levam a
  camara a ambiente + 16 degC; quem faz o trabalho pesado e' a manta de 80 W.
  Cinco lampadas e' um bom limite: cada uma a mais acrescenta so ~3 degC e
  mais corrente no Q1.
- **Mesmo comando nas duas** (GPIO27, LEDC canal 1, que divide o timer com o
  canal 0). O feedforward usa o ganho somado, 16 + 50 = 66 degC. O comando
  `m 0` desliga a manta para comparar.
- **Cadeia de seguranca:** TH1 (KSD301 85 degC, no ar) e TH2 (KSD301 120 degC,
  no dissipador) em serie com a bobina do rele automotivo K1. Qualquer um que
  abra corta lampadas e manta (rede `+12V_TH`); as ventoinhas continuam. O
  firmware ainda corta tudo acima de 78 degC.
- **Entrada:** com ate ~9 A, o diodo de protecao vira um P-MOSFET (Q4
  IRF4905, 20 mohm), F1 passa a 15 A e a bateria a 3S2P.

Resultado na planta simulada (`lib/control/plant_model.h`, dois nos: ar e
dissipador), Kp 0,080 e Ki 0,000100, ambiente 25 degC:

| Ensaio (tempo ate 0,5 degC do alvo) | Rev. D |
|--------|--------|
| 25 -> 45 degC | **12 min** |
| 45 -> 70 degC | **20 min**, pico < 0,3 degC acima |
| 70 -> 35 degC (cooler) | **8 min** |
| Partida a frio com ambiente a 19 degC, ate 45 | 23 min |
| Dissipador no pior caso (alvo 70) | 89 degC (TH2 abre a 120) |
| So lampadas, 100 % | para em ambiente + 16 degC |

O ganho e o atraso da manta sao estimativas: `PLANT_HEATER_GAIN_C`,
`PLANT_HEATER_TAU_S` e `PLANT_HEATER_COUPLING` em `include/config.h` devem
sair do ensaio de degrau no hardware. Com a manta o ensaio usa duty 0,6 (com
1,0 a camara iria acima de 85 degC e o corte de 78 degC dispararia antes).

## Painel web

Pagina estatica em [`web/`](web/), publicada pelo workflow `painel` no GitHub
Pages a cada push que mexe nela.

- Camara de policarbonato em 3D (three.js), com as cotas do PIDL-MEC-001: as
  cinco lampadas mudam de brilho **e de cor** com a
  potencia entregue — vermelho-alaranjado fraco em pouca potencia, branco
  quente no maximo, como um filamento de verdade. O fundo da pagina esquenta
  junto.
- Na cena tambem: o cooler na parede girando na proporcao do PWM, com a
  etiqueta de % e rpm estimado; o caminho do ar (entra frio pelos furos da
  lateral, passa pelos dissipadores, sobe pela prateleira perfurada e sai pelo
  cooler); a ventoinha de circulacao M2 sob a prateleira; a manta com os
  dissipadores aletados, que mudam de cor com a temperatura; amostras na
  prateleira; o modulo TM1637 mostrando exatamente o que o firmware mostra; e a
  ESP32 DevKit v1 numa protoboard na mesa, com os jumpers e o LED azul
  (GPIO2) piscando a cada amostra.
- Leituras com icones vivos: a lampada acende com o PWM, a resistencia da
  manta brilha, a ventoinha gira, o dissipador esquenta, a onda de PWM tem o
  duty real, o ponteiro marca a potencia, a bateria esvazia e o termometro sobe.
- Setpoint por slider, historico com temperatura e alvo, painel de atuadores
  (lampadas para cima, cooler para baixo), modo manual com lampadas e cooler
  separados, ensaio de degrau.
- **Porta clicavel:** clique na porta de policarbonato (ou no botao "Abrir a
  porta") e ela abre. O ar frio entra rente ao piso e o quente sai pela metade
  de cima; o modelo soma `PLANT_DOOR_GAIN = 4` a troca com o ambiente, entao o
  maximo teorico a 100 % cai de 91 para ~38 degC com 25 degC de ambiente
  (`T_amb + 66 / (1 + 4)`). O painel mostra esse maximo teorico ao vivo.
- Pas do cooler visiveis girando na proporcao do PWM (com rastro, sem efeito
  estroboscopico), e o ar - frio entrando e quente saindo - indo para a saida.
- Controles de simulacao: trocar ATX por bateria, ligar/desligar a manta,
  "abrir a janela" (ambiente cai 6 degC) e recarregar a bateria. Bons para
  mostrar o controle reagindo.
- Modo demonstracao (`?demo=1`): a mesma fisica e o mesmo PI rodando no
  navegador, para apresentar sem o Wokwi aberto. Fica marcado como tal.

Para testar localmente (modulos ES nao abrem via `file://`):

```powershell
python -m http.server 8080 -d web
# http://localhost:8080/?demo=1
```

Parametros de URL: `?demo=1`, `?id=<MQTT_DEVICE_ID>`, `?broker=wss://...`.

A decisao de usar MQTT em broker publico, e os cuidados que vem com ela,
estao em [`docs/decisoes/ADR-002-comunicacao-mqtt.md`](docs/decisoes/ADR-002-comunicacao-mqtt.md).

## Protocolo serial e MQTT

Os comandos sao os mesmos pela serial (115200 baud) e pelo topico
`pidlampada/<id>/cmd`:

| Comando | Efeito |
|---------|--------|
| `s 45` | setpoint em 45 degC (volta para malha fechada) |
| `k 0.08 0.0001` | define Kp e Ki em tempo de execucao |
| `d 0.8` | duty manual de aquecimento (lampadas + manta), malha aberta |
| `m 1` / `m 0` | liga / desliga a manta |
| `p 1` / `p 0` | abre / fecha a porta da camara — so simulacao |
| `v 0.5` | cooler manual (0 a 1), malha aberta |
| `r` | ensaio de degrau (cooler parado, zera o tempo; duty 100 %, ou 60 % com a manta) |
| `c` | volta para malha fechada |
| `a 19` | temperatura ambiente do modelo — so simulacao |
| `f bat` / `f atx` | fonte de alimentacao — so simulacao |
| `b` | recarrega a bateria — so simulacao |
| `?` | imprime o estado atual |

Saida serial em CSV, uma linha por amostra:

```
t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo,i_a,amb_c,fan,heat
```

Telemetria MQTT em `pidlampada/<id>/telemetria`, um JSON por amostra:

```json
{"t":900,"T":45.02,"sp":45.0,"u":0.3051,"ue":0.3051,"e":-0.02,"v":12.00,
 "i":2.89,"p":34.7,"soc":1.000,"src":"ATX","cut":0,"mode":"PI",
 "kp":0.08000,"ki":0.0001000,"amb":25.0,"sim":1,"lamps":5,"fan":0.000,
 "heat":0.3051,"hon":1,"th":52.6,"trip":0,"door":0,
 "up":15342}
```

`u` e' o duty aplicado; `ue` e' a potencia relativa a nominal, ja corrigida pela
tensao (`u * (V/12)^2`) — e' o que define o brilho das lampadas no painel.
`fan` e' o PWM do cooler (0 a 1), ja com a compensacao de tensao `x 12/V`.
`heat` e' o PWM da manta, `hon` diz se ela esta ligada; `th` (temperatura do
dissipador) e `trip` (cadeia de seguranca aberta) so existem na simulacao - no
hardware `th` vem `null`, porque nao ha sensor no dissipador.

O potenciometro so assume o setpoint quando e' mexido mais de 0,5 degC. Sem
essa histerese ele sobrescreveria, a cada amostra, o valor vindo do painel.

## Ensaio de degrau

```powershell
pio device monitor -e wokwi | Tee-Object -FilePath docs\ensaios\degrau_sim.csv
# na serial: r
```

Com o CSV em maos, extraia a constante de tempo pelo metodo dos 63,2 %:

```python
import pandas as pd
d = pd.read_csv("docs/ensaios/degrau_sim.csv", comment="#")
T0, Tf = d.T_c.iloc[0], d.T_c.iloc[-1]
tau = d.loc[d.T_c >= T0 + 0.632 * (Tf - T0), "t_s"].iloc[0]
print(f"K = {Tf - T0:.1f} C/duty   tau = {tau:.0f} s")
```

Depois atualize `PLANT_TAU_S` e `PLANT_GAIN_C` em `include/config.h` com os
valores **medidos no hardware** e ressintonize.

## Testes

```powershell
pio test -e native
```

25 testes. Cobrem o PI (proporcional puro, saturacao, anti-windup), o ganho
estatico do modelo, a convergencia da malha fechada, a bateria (tensao em
vazio, queda pela resistencia interna, balanco de energia e desarme do BMS),
o cooler (esfria mais rapido, nunca liga junto com as lampadas, histerese,
descida de setpoint mais rapida), o feedforward, a separacao da integral sem
travar com modelo errado, o formato do display e a manta (ganho somado,
atraso do dissipador, TH2 abrindo e fechando com histerese, o rele cortando
lampadas e manta juntas, aquecimento mais rapido, alcance de 60 e de 70 degC
e o regime com a porta aberta).
Rodam tambem no CI a cada push.

## Analise e sintonia

A pasta [`analise/`](analise/) traz o notebook que fecha o ciclo entre o
ensaio e o firmware: le o CSV da serial, identifica o modelo FOPDT, compara
quatro regras de sintonia em tres cenarios e gera os ganhos prontos para
colar em `include/config.h`.

```powershell
cd analise
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
jupyter lab
```

Tres resultados que valem para o relatorio:

- **O metodo dos 63,2 % infla tau** quando ha atraso de transporte. Sundaresan
  & Krishnaswamy (dois pontos, 35,3 % e 85,3 %) separa tau de theta e cai de
  1,1 para 0,19 degC de RMSE nos dados de exemplo.
- **O ZOH acrescenta Ts/2 de atraso efetivo.** Amostrar a cada 60 s equivale
  a 30 s de atraso extra; ignorar isso superestima a margem de fase.
- **A partida a frio nao diferencia sintonias** nesta planta: o duty satura
  em 1,0 durante quase toda a subida e o sistema roda em malha aberta. Para
  comparar regras e' preciso um degrau pequeno de setpoint ou uma
  perturbacao de ambiente.

`simular_malha_fechada()` reproduz o algoritmo de `pi_controller.cpp` —
mesma amostragem, mesma saturacao, mesmo anti-windup.

## Hardware

Esquema eletrico (PIDL-ESQ-001 Rev. D, 3 folhas), desenho mecanico
(PIDL-MEC-001: corte, plano de corte da chapa, furacao e lista de materiais)
e proposta em [`docs/hardware/`](docs/hardware/), em portugues e ingles.

Pinagem (esquema Rev. D):

| Pino | Rede | Funcao |
|------|------|--------|
| GPIO25 | PWM_GATE | LEDC ch0, 500 Hz -> gate do Q1 IRLZ44N (5 lampadas) |
| GPIO27 | HEAT_GATE | LEDC ch1 (timer das lampadas) -> gate do Q3 IRLB8721 (manta 80 W) |
| GPIO26 | FAN_GATE | LEDC ch2, 25 kHz -> gate do Q2 (cooler 80 mm) |
| GPIO18 | DISP_CLK | CLK do TM1637 |
| GPIO19 | DISP_DIO | DIO do TM1637 |
| GPIO32 | TEMP | ADC1_CH4 <- LM35 |
| GPIO33 | SETPOINT | ADC1_CH5 <- potenciometro (opcional) |
| GPIO34 | V_SENSE | ADC1_CH6 <- divisor 100k/27k |
| GPIO35 | PWR_OK_S | ADC1_CH7 <- PWR_OK da ATX |
| GPIO2 | LED_ST | LED de status (o da placa) |
| GPIO13 | BTN_MODE | botao (reservado, sem funcao ainda; era GPIO27) |

Protecoes (Rev. B a D), e por que cada uma existe:

| Peca | Onde | Por que |
|------|------|---------|
| D3 SS14 (Schottky) | em paralelo com o motor do cooler, catodo no +12 V | o motor e' **indutivo**: ao cortar o PWM ele gera um pico que queimaria o Q2. As lampadas sao resistivas e nao precisam disso |
| C6 100 nF | nos terminais do motor | absorve o ruido das escovas |
| C8 100 nF | no VS do LM35 | desacoplamento do sensor |
| R11 75 ohm + C9 1 uF | na saida do LM35 | filtro recomendado pela TI: o LM35 oscila com carga capacitiva direta |
| C10 100 nF | no VCC do TM1637 | desacoplamento do display |
| R9 100 ohm + R10 10 k | gate do Q2 | limita o pico de corrente do gate e garante Q2 desligado no boot |
| Ventoinhas fora da cadeia | K1 so corta lampadas e manta | em superaquecimento a ventoinha **tem** que continuar girando |
| TH1 85 degC + TH2 120 degC na bobina do K1 | TH1 no ar, TH2 no dissipador | com 8,8 A de carga, termostato barato nao aguenta a corrente; na bobina eles so passam ~80 mA e o rele automotivo (30 A) corta a carga |
| D5 1N4007 | em paralelo com a bobina do K1 | a bobina e' indutiva: sem o diodo, o pico ao abrir queima o contato do termostato |
| Q4 IRF4905 + R14 + D4 | entrada | protecao contra inversao com 20 mohm: um Schottky dissiparia ~5 W a 9 A |
| F1 15 A, SW1 15 A, C1 2200 uF | entrada | corrente maxima subiu para ~9 A |
| R12 150 ohm + R13 10 k | gate do Q3 | mesmo papel de R6/R7 no Q1 |

O TM1637 vai no **3V3**, nao no 5 V: os pinos do ESP32 nao toleram 5 V.

No hardware real, o Wi-Fi so liga se existir `include/secrets.h`:

```powershell
Copy-Item include\secrets.example.h include\secrets.h
# edite SSID e senha; o arquivo esta no .gitignore
```

## Limitacoes conhecidas

1. **PWM em light sleep.** `ledcSetup()` do core Arduino nao expoe a fonte de
   clock. Para o PWM sobreviver ao light sleep e' preciso configurar o timer
   LEDC com `REF_TICK` via `ledc_timer_config()` do ESP-IDF. Ainda nao feito.
2. **Calibracao do ADC.** A faixa util do LM35 (250 a 600 mV) cai no quinto
   inferior da escala, onde a nao-linearidade do ADC do ESP32 e' pior. Media de
   16 amostras reduz ruido aleatorio, nao erro sistematico. Pendente: atenuacao
   de 6 dB + `esp_adc_cal`, ou calibracao de dois pontos.
3. **Parametros da planta.** `PLANT_TAU_S` e `PLANT_GAIN_C` sao estimativas de
   projeto ate o ensaio de degrau no hardware real.
4. **Corrente estimada.** O circuito nao tem sensor de corrente: no hardware o
   valor e' calculado por `duty * V / R_lampadas + carga base`. Para medir de
   verdade, acrescentar um INA219 no barramento.
5. **Broker publico.** Qualquer pessoa que conheca o topico le a telemetria e
   envia comandos. O firmware limita setpoint, duty e ganhos; para alem da
   demonstracao, usar broker com autenticacao (ver ADR-002).
6. **Ganho do cooler estimado.** `PLANT_FAN_GAIN = 5` (ventilacao no maximo
   sextuplica a troca de calor) e' estimativa. Medir no hardware: degrau de
   cooler 100 % com lampadas apagadas a partir do regime.
7. **Manta estimada.** Ganho (50 degC), atraso do dissipador (140 s) e
   acoplamento com o ar (2,0, com a M2 ligada) sao estimativas de projeto. O
   dissipador escolhido muda muito o atraso: medir com degrau de 0,6 e
   ajustar `config.h`.
8. **Cooler e manta no Wokwi sao LEDs.** O simulador nao tem motor DC nem MOSFET;
   a parte analogica (diodo de roda livre, capacitores) so existe no esquema.
9. **Planta simulada sem atraso de transporte.** O modelo do Wokwi e' de 1a
   ordem pura; o hardware real tera atraso (filamento e sensor), entao o
   simulador parece mais estavel do que a bancada vai ser.

## Licenca

MIT — ver [LICENSE](LICENSE).
