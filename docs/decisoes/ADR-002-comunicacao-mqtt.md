# ADR-002 — Painel web via MQTT em broker público

**Data:** 2026-10-11
**Status:** aceito

## Contexto

O professor quer ver o controle funcionando antes de o hardware existir, e
o painel precisa abrir no celular. O ESP32 roda no Wokwi, dentro do VS Code,
no computador do aluno. Três caminhos possíveis:

| Opção | Como | Problema |
|---|---|---|
| Servidor web no ESP32 | `[[net.forward]]` no `wokwi.toml` expõe a porta 80 em `localhost` | só abre no próprio PC; celular não alcança |
| Gateway privado do Wokwi | tráfego direto para a rede local | recurso pago; ainda preso à rede local |
| **MQTT em broker público** | ESP32 publica, navegador assina | dados passam por terceiro; tópico é público |

## Decisão

MQTT, com o broker público da HiveMQ:

- ESP32: TCP em `broker.hivemq.com:1883`, biblioteca PubSubClient.
- Navegador: WebSocket seguro em `wss://broker.hivemq.com:8884/mqtt`, mqtt.js.
- Painel estático no GitHub Pages, sem servidor próprio.

Tópicos sob `pidlampada/<MQTT_DEVICE_ID>/`:

| Tópico | Sentido | Conteúdo |
|---|---|---|
| `telemetria` | ESP32 → painel | JSON a cada amostra do controle |
| `status` | ESP32 → painel | `online` / `offline`, retido, com LWT |
| `cmd` | painel → ESP32 | texto, **o mesmo protocolo da serial** |
| `log` | ESP32 → painel | respostas aos comandos |

Reaproveitar o protocolo da serial no tópico `cmd` foi deliberado: um só
parser no firmware, e tudo o que se testa pelo monitor serial vale igual
pelo painel.

## Consequências

**Positivas**
- O mesmo painel funciona com o Wokwi hoje e com o hardware amanhã; muda só
  a origem dos dados.
- Abre em qualquer lugar com internet, inclusive no celular do professor.
- Sem servidor para manter: o painel é HTML estático.

**Negativas e mitigação**
- **Qualquer pessoa que conheça o tópico lê e envia comandos.** O firmware
  limita setpoint (25–60 °C), duty (0–1) e ganhos; no hardware, o KSD9700 corta
  a 70 °C independente do software. Para uso além da demonstração, trocar por
  broker com usuário e senha (HiveMQ Cloud tem plano gratuito) e TLS no ESP32.
- **Dependência de terceiro.** Se o broker público cair, o painel oferece o
  modo demonstração, que roda a mesma física e o mesmo controle no navegador.
- **Princípio mantido:** o controle nunca espera pela rede. Wi-Fi e MQTT
  reconectam em segundo plano; a malha continua fechada sem eles.
