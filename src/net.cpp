#include "net.h"
#include "config.h"

#if NET_ENABLED

#include <WiFi.h>
#include <PubSubClient.h>

namespace {

WiFiClient   g_wifi_client;
PubSubClient g_mqtt(g_wifi_client);
net::CommandHandler g_handler = nullptr;

char g_client_id[32];
uint32_t g_last_attempt_ms = 0;
bool g_wifi_announced = false;

constexpr uint32_t kRetryMs = 5000;

const char* topic(const char* leaf) {
  static char buf[96];
  snprintf(buf, sizeof(buf), "%s/%s", MQTT_BASE_TOPIC, leaf);
  return buf;
}

void onMessage(char* /*topic*/, byte* payload, unsigned int length) {
  if (!g_handler || length == 0 || length > 120) return;
  char line[128];
  memcpy(line, payload, length);
  line[length] = '\0';
  g_handler(String(line));
}

void tryConnectMqtt() {
  // LWT: se o ESP32 sumir sem se despedir, o broker publica "offline".
  if (!g_mqtt.connect(g_client_id, topic("status"), 0, true, "offline")) {
    Serial.printf("# mqtt: falha (estado %d), nova tentativa em %lu s\r\n",
                  g_mqtt.state(), (unsigned long)(kRetryMs / 1000));
    return;
  }
  g_mqtt.publish(topic("status"), "online", true);
  g_mqtt.subscribe(topic("cmd"));
  Serial.printf("# mqtt: conectado a %s como %s\r\n", MQTT_HOST, g_client_id);
  Serial.printf("# mqtt: topico base %s\r\n", MQTT_BASE_TOPIC);
}

}  // namespace

namespace net {

void begin(CommandHandler handler) {
  g_handler = handler;

  WiFi.mode(WIFI_STA);              // antes de ler o MAC: sem isso pode vir zerado

  // Sufixo aleatorio: no Wokwi todo ESP32 tem o mesmo MAC, e dois clientes
  // com o mesmo ID derrubam um ao outro no broker.
  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(g_client_id, sizeof(g_client_id), "pidlampada-%02x%02x-%04lx",
           mac[4], mac[5], (unsigned long)random(0x10000));

  WiFi.begin(WIFI_SSID, WIFI_PASS, WIFI_CHANNEL);   // nao bloqueia

  g_mqtt.setServer(MQTT_HOST, MQTT_PORT);
  g_mqtt.setCallback(onMessage);
  g_mqtt.setBufferSize(512);      // padrao de 256 B e' pouco para a telemetria
  g_mqtt.setSocketTimeout(2);     // limita o tempo em que connect() pode travar
  g_mqtt.setKeepAlive(15);

  Serial.printf("# wifi: conectando a \"%s\"...\r\n", WIFI_SSID);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    g_wifi_announced = false;
    return;
  }
  if (!g_wifi_announced) {
    g_wifi_announced = true;
    Serial.printf("# wifi: conectado, IP %s\r\n", WiFi.localIP().toString().c_str());
  }

  if (!g_mqtt.connected()) {
    const uint32_t now = millis();
    if (g_last_attempt_ms == 0 || now - g_last_attempt_ms >= kRetryMs) {
      g_last_attempt_ms = now;
      tryConnectMqtt();
    }
    return;
  }
  g_mqtt.loop();
}

bool online() { return g_mqtt.connected(); }

void publishTelemetry(const char* json) {
  if (g_mqtt.connected()) g_mqtt.publish(topic("telemetria"), json);
}

void log(const char* line) {
  if (g_mqtt.connected()) g_mqtt.publish(topic("log"), line);
}

}  // namespace net

#else  // NET_ENABLED == 0: sem credenciais, so serial

namespace net {
void begin(CommandHandler) {
  Serial.println("# rede desativada (sem WIFI_SSID) - copie include/secrets.example.h");
}
void loop() {}
bool online() { return false; }
void publishTelemetry(const char*) {}
void log(const char*) {}
}  // namespace net

#endif
