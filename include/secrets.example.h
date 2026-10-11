#pragma once
/*
 * Credenciais do hardware real.
 *
 * Copie este arquivo para include/secrets.h e preencha. O secrets.h esta
 * no .gitignore - senha de Wi-Fi nunca vai para o repositorio.
 *
 *   Copy-Item include\secrets.example.h include\secrets.h
 *
 * No Wokwi nada disso e' usado: o ambiente "wokwi" conecta sozinho na
 * rede aberta Wokwi-GUEST.
 */

#define WIFI_SSID "nome-da-rede"
#define WIFI_PASS "senha-da-rede"

// Opcional - os padroes estao em config.h.
// #define MQTT_DEVICE_ID "gmarques-01"
// #define MQTT_HOST      "broker.hivemq.com"
