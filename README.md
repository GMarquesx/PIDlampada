# PIDlampada — Camara Termica Compacta com Controle PWM

Camara termica de ~100x100x80 mm aquecida por tres lampadas automotivas W5W,
com controlador PI embarcado em ESP32 atuando por PWM atraves de um MOSFET
IRLZ44N. O brilho das lampadas **e** a variavel manipulada: quanto mais aceso,
mais frio esta o interior. Um cooler de exaustao joga o ar quente para fora
quando o setpoint fica abaixo da temperatura medida, e um display de 7
segmentos (TM1637) mostra a leitura na propria camara.

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
│   ├── plant_model.{h,cpp}     modelo termico de 1a ordem com ventilacao
│   ├── battery_model.{h,cpp}   pack 3S com resistencia interna e BMS
│   └── seg7.{h,cpp}            formato do display ("43.2C", "Err ", "bAt ")
├── src/
│   ├── main.cpp                maquina de estados, CSV, comandos
│   ├── sensor.{h,cpp}          LM35 | NTC do Wokwi | planta simulada
│   ├── power.{h,cpp}           tensao, corrente, fonte ATX/bateria
│   ├── net.{h,cpp}             Wi-Fi + MQTT (nunca bloqueia o controle)
│   ├── display.{h,cpp}         driver TM1637 proprio (bit-bang, sem biblioteca)
│   └── actuator.{h,cpp}        LEDC: lampadas (ch0, 500 Hz) e cooler (ch2, 25 kHz)
├── web/                        painel (three.js + mqtt.js), publicado no Pages
├── test/test_control/          testes unitarios (Unity)
├── analise/                    identificacao da planta e sintonia (Python)
├── diagram.json                circuito do Wokwi
├── wokwi.toml                  aponta para o firmware do env "wokwi"
└── docs/
    ├── hardware/               esquemas Rev. A e Rev. B, proposta (PDF/SVG/script)
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
| Potenciometro | GPIO33 | setpoint |

**Limite do Wokwi:** ele simula logica digital, nao circuito analogico — nao
tem MOSFET, diodo, capacitor nem motor DC. Por isso o cooler aparece como LED
e as protecoes (diodo de roda livre, capacitores de desacoplamento, filtro do
LM35) estao no esquema Rev. B, em [`docs/hardware/`](docs/hardware/). O
firmware e' o mesmo nos dois casos.

## Cooler e controle em faixa dividida

As lampadas so aquecem. Sem outro atuador, baixar o setpoint de 45 para 32 degC
significa esperar a camara perder calor sozinha pelas paredes. O cooler de
exaustao (40 mm, 12 V) troca o ar de dentro pelo de fora e acelera isso.

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
- **Ganho proprio do lado frio (x4):** com o Kp das lampadas, o cooler so
  reagiria a erros enormes.
- **O cooler nao esfria abaixo do ambiente.** Ele troca ar; quem gera frio
  e' o ar de fora. O painel avisa quando o alvo fica abaixo do ambiente.
- **Em falha** (T > 68 degC) as lampadas apagam e o cooler vai a 100 %.

So o split-range nao bastou. A integral, acumulada em 45 degC, mantinha as
lampadas acesas em 43 degC na descida. Tres mudancas no PI resolveram, todas
cobertas por teste unitario:

1. **Feedforward do setpoint:** `ff = (sp - T_amb) / K`, o duty que o modelo
   diz ser necessario em regime. A integral so corrige o que o modelo erra.
2. **Separacao da integral:** so integra a menos de 3 degC do alvo, ou quando
   a temperatura ja parou de mexer (evita erro permanente se o modelo errar).
3. **Nao integra enquanto ja esta chegando** ao alvo rapido o bastante.

Resultado na planta simulada (tau 640 s, K 30 degC), descida de 45 para 32 degC:

| Versao | Tempo ate o alvo |
|--------|------------------|
| PI original, sem cooler | 31 min |
| PI original + cooler | 26 min |
| PI + feedforward + separacao da integral + cooler | **7 min**, minimo de 31,9 degC |

A partida a frio continua chegando a 45 degC em cerca de 15 min, com pico de
45,08 degC, e a resposta a perturbacao de ambiente nao mudou.

## Painel web

Pagina estatica em [`web/`](web/), publicada pelo workflow `painel` no GitHub
Pages a cada push que mexe nela.

- Camara em 3D (three.js): as tres lampadas mudam de brilho **e de cor** com a
  potencia entregue — vermelho-alaranjado fraco em pouca potencia, branco
  quente no maximo, como um filamento de verdade. O fundo da pagina esquenta
  junto.
- Na cena tambem: o cooler na parede girando na rotacao do PWM, o fluxo de ar
  (quente saindo pelo cooler, frio entrando pelas fendas do outro lado) e o
  modulo TM1637 na frente da base mostrando exatamente o que o firmware mostra.
- Leituras com icones vivos: a lampada acende com o PWM, a ventoinha gira, a
  onda de PWM tem o duty real, o ponteiro marca a potencia, a bateria esvazia
  e o termometro sobe.
- Setpoint por slider, historico com temperatura e alvo, painel de atuadores
  (lampadas para cima, cooler para baixo), modo manual com lampadas e cooler
  separados, ensaio de degrau.
- Controles de simulacao: trocar ATX por bateria, "abrir a janela" (ambiente
  cai 6 degC) e recarregar a bateria. Bons para mostrar o controle reagindo.
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
| `k 0.0637 0.000105` | define Kp e Ki em tempo de execucao |
| `d 0.8` | duty manual das lampadas, malha aberta |
| `v 0.5` | cooler manual (0 a 1), malha aberta |
| `r` | ensaio de degrau (duty 100 %, cooler parado, zera o tempo) |
| `c` | volta para malha fechada |
| `a 19` | temperatura ambiente do modelo — so simulacao |
| `f bat` / `f atx` | fonte de alimentacao — so simulacao |
| `b` | recarrega a bateria — so simulacao |
| `?` | imprime o estado atual |

Saida serial em CSV, uma linha por amostra:

```
t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo,i_a,amb_c,fan
```

Telemetria MQTT em `pidlampada/<id>/telemetria`, um JSON por amostra:

```json
{"t":900,"T":45.03,"sp":45.0,"u":0.6812,"ue":0.6812,"e":-0.03,"v":12.00,
 "i":0.927,"p":11.12,"soc":1.000,"src":"ATX","cut":0,"mode":"PI",
 "kp":0.06370,"ki":0.0001050,"amb":25.0,"sim":1,"lamps":3,"fan":0.000,
 "up":15342}
```

`u` e' o duty aplicado; `ue` e' a potencia relativa a 15 W, ja corrigida pela
tensao (`u * (V/12)^2`) — e' o que define o brilho das lampadas no painel.
`fan` e' o PWM do cooler (0 a 1), ja com a compensacao de tensao `x 12/V`.

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

17 testes. Cobrem o PI (proporcional puro, saturacao, anti-windup), o ganho
estatico do modelo, a convergencia da malha fechada, a bateria (tensao em
vazio, queda pela resistencia interna, balanco de energia e desarme do BMS),
o cooler (esfria mais rapido, nunca liga junto com as lampadas, histerese,
descida de setpoint mais rapida), o feedforward, a separacao da integral sem
travar com modelo errado e o formato do display. Rodam tambem no CI a cada
push.

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

Esquema eletrico, proposta e BOM em [`docs/hardware/`](docs/hardware/).

Pinagem (esquema Rev. B):

| Pino | Rede | Funcao |
|------|------|--------|
| GPIO25 | PWM_GATE | LEDC ch0, 500 Hz -> gate do Q1 IRLZ44N (lampadas) |
| GPIO26 | FAN_GATE | LEDC ch2, 25 kHz -> gate do Q2 (cooler) |
| GPIO18 | DISP_CLK | CLK do TM1637 |
| GPIO19 | DISP_DIO | DIO do TM1637 |
| GPIO32 | TEMP | ADC1_CH4 <- LM35 |
| GPIO33 | SETPOINT | ADC1_CH5 <- potenciometro (opcional) |
| GPIO34 | V_SENSE | ADC1_CH6 <- divisor 100k/27k |
| GPIO35 | PWR_OK_S | ADC1_CH7 <- PWR_OK da ATX |
| GPIO2 | LED_ST | LED de status (o da placa) |
| GPIO27 | BTN_MODE | botao (reservado, sem funcao ainda) |

Protecoes da Rev. B, e por que cada uma existe:

| Peca | Onde | Por que |
|------|------|---------|
| D3 SS14 (Schottky) | em paralelo com o motor do cooler, catodo no +12 V | o motor e' **indutivo**: ao cortar o PWM ele gera um pico que queimaria o Q2. As lampadas sao resistivas e nao precisam disso |
| C6 100 nF | nos terminais do motor | absorve o ruido das escovas |
| C8 100 nF | no VS do LM35 | desacoplamento do sensor |
| R11 75 ohm + C9 1 uF | na saida do LM35 | filtro recomendado pela TI: o LM35 oscila com carga capacitiva direta |
| C10 100 nF | no VCC do TM1637 | desacoplamento do display |
| R9 100 ohm + R10 10 k | gate do Q2 | limita o pico de corrente do gate e garante Q2 desligado no boot |
| Cooler fora do TH1 | KSD9700 so corta as lampadas | em superaquecimento a ventoinha **tem** que continuar girando |

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
6. **Ganho do cooler estimado.** `PLANT_FAN_GAIN = 3` (ventilacao no maximo
   quadruplica a troca de calor) e' estimativa. Medir no hardware: degrau de
   cooler 100 % com lampadas apagadas a partir do regime.
7. **Cooler no Wokwi e' um LED.** O simulador nao tem motor DC nem MOSFET;
   a parte analogica (diodo de roda livre, capacitores) so existe no esquema.
8. **Planta simulada sem atraso de transporte.** O modelo do Wokwi e' de 1a
   ordem pura; o hardware real tera atraso (filamento e sensor), entao o
   simulador parece mais estavel do que a bancada vai ser.

## Licenca

MIT — ver [LICENSE](LICENSE).
