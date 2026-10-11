/*
 * Ligacao com a camara: MQTT (dispositivo real ou Wokwi) ou demonstracao.
 *
 * Eventos emitidos:
 *   state      { state: 'wait'|'live'|'demo'|'error', text }
 *   telemetry  objeto JSON publicado pelo firmware
 *   log        linha de texto (resposta a comando, aviso)
 *   device     { online: boolean }  - LWT do topico status
 *
 * Os comandos sao texto puro, o mesmo protocolo da serial ("s 45", "r").
 */

import { DemoDevice } from './sim.js';

// Carregado sob demanda: se o CDN falhar, o modo demonstracao continua.
let mqttLib = null;
const loadMqtt = async () => (mqttLib ??= (await import('mqtt')).default);

const NO_DATA_MS = 12000;

export class Link extends EventTarget {
  constructor() {
    super();
    this.client = null;
    this.demo = null;
    this.base = '';
    this.mode = 'none';
    this.lastData = 0;
    this.watchdog = null;
  }

  #emit(type, detail) { this.dispatchEvent(new CustomEvent(type, { detail })); }
  #state(state, text) { this.#emit('state', { state, text }); }

  disconnect() {
    clearInterval(this.watchdog);
    this.watchdog = null;
    if (this.client) { this.client.end(true); this.client = null; }
    if (this.demo) { this.demo.stop(); this.demo = null; }
    this.mode = 'none';
  }

  async connectMqtt(brokerUrl, deviceId) {
    this.disconnect();
    this.mode = 'mqtt';
    this.base = `pidlampada/${deviceId}`;
    this.lastData = 0;
    this.brokerUp = false;
    this.#state('wait', 'Conectando ao broker');
    // O vigia comeca ja: se o broker nunca responder, a pessoa precisa de uma
    // saida (modo demonstracao) em vez de ficar olhando para "conectando".
    this.#startWatchdog();

    let mqtt;
    try {
      mqtt = await loadMqtt();
    } catch (err) {
      this.#state('error', 'Biblioteca MQTT não carregou');
      this.#emit('log', `# erro ao carregar o cliente MQTT: ${err.message}`);
      this.#emit('stale', { reason: 'no-broker' });
      return;
    }
    if (this.mode !== 'mqtt') return;   // usuario trocou de modo enquanto carregava

    let client;
    try {
      client = mqtt.connect(brokerUrl, {
        clientId: `painel-${Math.random().toString(16).slice(2, 10)}`,
        clean: true,
        connectTimeout: 8000,
        reconnectPeriod: 4000,
        keepalive: 30,
      });
    } catch (err) {
      this.#state('error', 'Endereço do broker inválido');
      this.#emit('log', `# erro: ${err.message}`);
      return;
    }
    this.client = client;

    client.on('connect', () => {
      this.brokerUp = true;
      client.subscribe([`${this.base}/telemetria`, `${this.base}/status`, `${this.base}/log`]);
      if (!this.lastData) this.#state('wait', 'Aguardando a câmara');
      this.#emit('log', `# conectado ao broker, ouvindo ${this.base}`);
    });

    client.on('reconnect', () => this.#state('wait', 'Reconectando ao broker'));
    client.on('offline', () => this.#state('error', 'Sem conexão com o broker'));
    client.on('error', (err) => this.#emit('log', `# erro do broker: ${err.message}`));

    client.on('message', (topic, payload) => {
      const text = payload.toString();
      if (topic.endsWith('/telemetria')) {
        let data;
        try { data = JSON.parse(text); } catch { return; }
        this.lastData = Date.now();
        this.#state('live', 'Ao vivo');
        this.#emit('telemetry', data);
      } else if (topic.endsWith('/status')) {
        const online = text === 'online';
        this.#emit('device', { online });
        if (!online) this.#state('error', 'Câmara offline');
      } else if (topic.endsWith('/log')) {
        this.#emit('log', text);
      }
    });
  }

  #startWatchdog() {
    clearInterval(this.watchdog);
    const since = Date.now();
    this.watchdog = setInterval(() => {
      const ref = this.lastData || since;
      if (Date.now() - ref > NO_DATA_MS) {
        const reason = this.lastData ? 'stopped' : this.brokerUp ? 'no-device' : 'no-broker';
        const text = { stopped: 'A câmara parou de responder', 'no-device': 'Nenhuma câmara respondendo', 'no-broker': 'Sem conexão com o broker' }[reason];
        this.#state('error', text);
        this.#emit('stale', { reason });
      }
    }, 2000);
  }

  startDemo() {
    this.disconnect();
    this.mode = 'demo';
    const dev = new DemoDevice();
    dev.addEventListener('telemetry', (e) => this.#emit('telemetry', e.detail));
    dev.addEventListener('log', (e) => this.#emit('log', e.detail));
    this.demo = dev;
    this.#state('demo', 'Demonstração');
    this.#emit('log', '# modo demonstração: física e controle simulados no navegador');
    dev.start();
  }

  send(command) {
    if (this.mode === 'demo' && this.demo) { this.demo.command(command); return true; }
    if (this.mode === 'mqtt' && this.client && this.client.connected) {
      this.client.publish(`${this.base}/cmd`, command);
      return true;
    }
    return false;
  }
}
