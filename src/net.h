#pragma once
#include <Arduino.h>

/*
 * Wi-Fi + MQTT.
 *
 * Topicos (MQTT_BASE_TOPIC = "pidlampada/<id>"):
 *   <base>/telemetria   JSON publicado a cada amostra do controle
 *   <base>/status       "online" / "offline" (retido, com LWT)
 *   <base>/cmd          comandos de texto - o MESMO protocolo da serial
 *   <base>/log          respostas aos comandos
 *
 * Principio de projeto: o controle nunca espera pela rede. Se o Wi-Fi ou o
 * broker caem, a malha continua fechada e a reconexao e' tentada em segundo
 * plano a cada poucos segundos.
 */
namespace net {

using CommandHandler = void (*)(const String& line);

void begin(CommandHandler handler);
void loop();                       // chamar em todo loop(); nao bloqueia
bool online();                     // MQTT conectado
void publishTelemetry(const char* json);
void log(const char* line);

}  // namespace net
