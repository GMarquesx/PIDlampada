# PIDlampada — Camara Termica Compacta com Controle PWM

Camara termica de ~100x100x80 mm aquecida por tres lampadas automotivas W5W,
com controlador PI embarcado em ESP32 atuando por PWM atraves de um MOSFET
IRLZ44N. O brilho das lampadas **e** a variavel manipulada: quanto mais aceso,
mais frio esta o interior.

Projeto Integrador — Engenharia de Computacao, UNIP Sao Jose dos Campos, 8o
semestre / 2026.

---

## Sumario

- [Arquitetura](#arquitetura)
- [Comecando](#comecando)
- [Ambientes de build](#ambientes-de-build)
- [Simulando no Wokwi](#simulando-no-wokwi)
- [Protocolo serial](#protocolo-serial)
- [Ensaio de degrau](#ensaio-de-degrau)
- [Testes](#testes)
- [Hardware](#hardware)
- [Limitacoes conhecidas](#limitacoes-conhecidas)

---

## Arquitetura

```
PIDlampada/
├── include/config.h            parametros de projeto (pinos, ganhos, limites)
├── lib/control/                C++ puro, sem Arduino — testavel no PC
│   ├── pi_controller.{h,cpp}   PI com anti-windup por clamping condicional
│   └── plant_model.{h,cpp}     modelo termico de 1a ordem
├── src/
│   ├── main.cpp                maquina de estados, CSV, comandos seriais
│   ├── sensor.{h,cpp}          LM35 | NTC do Wokwi | planta simulada
│   └── actuator.{h,cpp}        LEDC + soft-start
├── test/test_control/          testes unitarios (Unity)
├── diagram.json                circuito do Wokwi
├── wokwi.toml                  aponta para o firmware do env "wokwi"
└── docs/
    ├── hardware/               esquema eletrico e proposta (PDF/SVG/script)
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

## Protocolo serial

115200 baud. Saida em CSV, uma linha por amostra:

```
t_s,T_c,setpoint_c,duty,erro_c,vbat_v,modo
```

Comandos de entrada:

| Comando | Efeito |
|---------|--------|
| `s 45` | setpoint em 45 degC |
| `k 0.05 0.0002` | define Kp e Ki em tempo de execucao |
| `d 0.8` | duty manual, malha aberta |
| `r` | inicia ensaio de degrau (duty 100%) |
| `c` | volta para malha fechada |
| `?` | imprime o estado atual |

Poder mudar ganhos pela serial encurta muito a sintonia: nao precisa
recompilar a cada tentativa.

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

Cobrem o PI (proporcional puro, saturacao, anti-windup), o ganho estatico do
modelo e a convergencia da malha fechada. Rodam tambem no CI a cada push.

## Hardware

Esquema eletrico, proposta e BOM em [`docs/hardware/`](docs/hardware/).

Pinagem (identica ao esquema Rev. A):

| Pino | Rede | Funcao |
|------|------|--------|
| GPIO25 | PWM_GATE | LEDC -> gate do IRLZ44N |
| GPIO32 | TEMP | ADC1_CH4 <- LM35 |
| GPIO33 | SETPOINT | ADC1_CH5 <- potenciometro (opcional) |
| GPIO34 | V_SENSE | ADC1_CH6 <- divisor 100k/27k |
| GPIO35 | PWR_OK_S | ADC1_CH7 <- PWR_OK da ATX |
| GPIO16 | LED_ST | LED de status |
| GPIO27 | BTN_MODE | botao de modo |

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
4. **Interface web.** Prevista no item 9 da proposta, ainda nao implementada.

## Licenca

MIT — ver [LICENSE](LICENSE).
