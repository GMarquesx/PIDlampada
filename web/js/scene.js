/*
 * A camara em 3D.
 *
 * Unidade = 1 cm. Caixa de 10 x 8 x 10 cm sobre uma base de acrilico preto,
 * chapa de aluminio presa no teto e tres W5W penduradas nela, como na
 * proposta. O brilho e a cor de cada lampada seguem a potencia real
 * entregue (duty corrigido pela tensao), com a inercia de um filamento.
 *
 * Cooler de 40 mm na parede direita, perto do teto (onde o ar quente
 * fica), com frestas de entrada embaixo na parede oposta. Gira na
 * proporcao do PWM e mostra o caminho do ar: entra frio pelas frestas,
 * atravessa a camara esquentando e sai pelo cooler.
 *
 * No piso, a manta de silicone sob um dissipador aletado: o dissipador
 * esquenta de cor com a temperatura dele e solta ar quente para cima.
 *
 * Na mesa, a ESP32 DevKit v1 numa protoboard, com os jumpers ate a
 * camara e ate o modulo TM1637 (que mostra a leitura do Wokwi). O LED
 * azul da placa (GPIO2) pisca a cada amostra, como no firmware.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const BOX = { w: 10, h: 8, d: 10, base: 0.6 };
const LAMP_X = [-2.7, 0, 2.7];

// Cor do filamento por potencia: vermelho-alaranjado fraco ate branco quente.
const COLD = new THREE.Color('#ff4a12');
const HOT = new THREE.Color('#ffd7a3');
const ACRYLIC_EDGE = new THREE.Color('#9fd8ea');
const TUNGSTEN = new THREE.Color('#ffb25b');
const FAN_Y = BOX.base + BOX.h - 2.3;
const SINK = { w: 8.6, base: 0.28, fin: 1.25, fins: 9, y: BOX.base + 0.32 };   // dissipador no piso
const ESP_POS = new THREE.Vector3(8.4, 0, 8.2);    // protoboard na mesa
const ESP_ROT = -0.42;
// Particulas de ar: exaustao (fora), entrada (fora), caminho interno e conveccao
const AIR = { out: 90, intake: 50, path: 120, conv: 110 };
const AIR_N = AIR.out + AIR.intake + AIR.path + AIR.conv;
const FAN_RPM_MAX = 6000;                          // ventoinha 40 mm a 12 V
const FAN_VISUAL_MAX = 10;                         // rad/s na tela (sem efeito estroboscopico)

export class ChamberScene {
  constructor(host) {
    this.host = host;
    this.target = { ue: 0, T: 25, amb: 25, fault: false, fan: 0, display: null, displayKey: '',
      heat: 0, hon: 1, sink: null, beat: null };
    this.shown = { b: 0, heat: 0, fan: 0, pad: 0, sink: 25 };
    this.ledOn = false;
    this.lastBeat = null;
    this.fanLabelKey = '';
    this.fanAngle = 0;
    this.drawnDisplay = undefined;
    this.visible = true;
    this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    } catch (err) {
      host.innerHTML = '<p class="hint" style="padding:24px">Este navegador não conseguiu iniciar o WebGL, então a vista 3D ficou desligada. As leituras abaixo continuam funcionando.</p>';
      this.renderer = null;
      return;
    }

    const r = this.renderer;
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.outputColorSpace = THREE.SRGBColorSpace;
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 0.9;
    r.setClearColor(0x000000, 0);
    host.appendChild(r.domElement);

    this.scene = new THREE.Scene();
    // Fundo e neblina na cor da pagina; aquecem junto com as lampadas.
    this.bgCold = new THREE.Color('#10171e');
    this.bgWarm = new THREE.Color('#2b1c10');
    this.scene.background = this.bgCold.clone();
    this.scene.fog = new THREE.Fog(this.bgCold.clone(), 38, 95);
    const pmrem = new THREE.PMREMGenerator(r);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(r), 0.04).texture;

    this.camera = new THREE.PerspectiveCamera(30, 1, 0.5, 200);
    this.camera.position.set(17, 12, 21);

    this.controls = new OrbitControls(this.camera, r.domElement);
    this.controls.target.set(0, BOX.base + BOX.h * 0.5, 0);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.minDistance = 16;
    this.controls.maxDistance = 48;
    this.controls.minPolarAngle = 0.35;
    this.controls.maxPolarAngle = 1.48;
    this.controls.autoRotate = !this.reduceMotion;
    this.controls.autoRotateSpeed = 0.55;
    let idle;
    this.controls.addEventListener('start', () => { this.controls.autoRotate = false; clearTimeout(idle); });
    this.controls.addEventListener('end', () => {
      clearTimeout(idle);
      if (!this.reduceMotion) idle = setTimeout(() => { this.controls.autoRotate = true; }, 9000);
    });

    this.#build();

    this.composer = new EffectComposer(r);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.85, 0.55, 0.82);
    this.composer.addPass(this.bloom);
    this.composer.addPass(new OutputPass());

    new ResizeObserver(() => this.#resize()).observe(host);
    this.#resize();

    // Nao gasta bateria do celular renderizando o que ninguem ve.
    new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; }).observe(host);
    document.addEventListener('visibilitychange', () => { this.hidden = document.hidden; });

    this.clock = new THREE.Clock();
    r.setAnimationLoop(() => this.#frame());
  }

  setState(next) { Object.assign(this.target, next); }

  #build() {
    const s = this.scene;

    s.add(new THREE.HemisphereLight(0x9fb6cc, 0x0b0f13, 0.35));

    // bancada
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(60, 64),
      new THREE.MeshStandardMaterial({ color: 0x1b242d, roughness: 0.92, metalness: 0, envMapIntensity: 0.2 }),
    );
    ground.rotation.x = -Math.PI / 2;
    s.add(ground);

    // sombra de contato falsa sob a base
    const shadowTex = radialTexture('rgba(0,0,0,0.75)', 'rgba(0,0,0,0)');
    const shadow = new THREE.Mesh(
      new THREE.PlaneGeometry(BOX.w * 1.9, BOX.d * 1.9),
      new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }),
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = 0.01;
    s.add(shadow);

    // base de acrilico preto
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(BOX.w + 1.2, BOX.base, BOX.d + 1.2),
      new THREE.MeshPhysicalMaterial({ color: 0x0c0f12, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 0.6 }),
    );
    base.position.y = BOX.base / 2;
    s.add(base);

    const top = BOX.base + BOX.h;

    // calor: volume interno que esquenta de cor com a temperatura
    this.heatMat = new THREE.MeshBasicMaterial({
      color: 0xff8a3d, transparent: true, opacity: 0, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.BackSide,
    });
    const heat = new THREE.Mesh(new THREE.BoxGeometry(BOX.w - 0.3, BOX.h - 0.3, BOX.d - 0.3), this.heatMat);
    heat.position.y = BOX.base + BOX.h / 2;
    s.add(heat);

    // chapa de aluminio no teto
    const plate = new THREE.Mesh(
      new THREE.BoxGeometry(8.2, 0.2, 5.2),
      new THREE.MeshStandardMaterial({ color: 0xc9d0d6, metalness: 1, roughness: 0.32, envMapIntensity: 0.9 }),
    );
    plate.position.y = top - 0.55;
    s.add(plate);

    // lampadas
    this.lamps = LAMP_X.map((x) => this.#lamp(x, top - 0.65));

    // sensor LM35 (TO-92) pendurado a meia altura, fora do eixo das lampadas
    this.#sensor(3.1, BOX.base + 3.6, 2.6, top);

    // acrilico: faces quase invisiveis + arestas que conduzem a luz
    this.acrylic = new THREE.MeshPhysicalMaterial({
      color: 0xdaf1f8, transparent: true, opacity: 0.06, roughness: 0.05,
      metalness: 0, clearcoat: 0.35, clearcoatRoughness: 0.05, envMapIntensity: 0.15,
      side: THREE.DoubleSide, depthWrite: false,
    });
    const boxGeo = new THREE.BoxGeometry(BOX.w, BOX.h, BOX.d);
    const box = new THREE.Mesh(boxGeo, this.acrylic);
    box.position.y = BOX.base + BOX.h / 2 + 0.03;   // acima da base: sem z-fighting
    box.renderOrder = 2;
    s.add(box);

    this.edgeMat = new THREE.LineBasicMaterial({ color: ACRYLIC_EDGE.clone(), transparent: true, opacity: 0.6 });
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(boxGeo), this.edgeMat);
    edges.position.copy(box.position);
    edges.renderOrder = 3;
    s.add(edges);

    this.#fan();
    this.#vents();
    this.#heater();
    this.#air();
    this.#displayModule();
    this.#espBoard();
    this.#wires();
  }

  // Cooler 40 x 40 mm na parede +x: moldura com furo, cubo e 7 pas.
  #fan() {
    const g = new THREE.Group();
    g.position.set(BOX.w / 2 + 0.02, FAN_Y, 0);
    this.scene.add(g);

    const frameShape = new THREE.Shape();
    frameShape.moveTo(-2, -2); frameShape.lineTo(2, -2); frameShape.lineTo(2, 2); frameShape.lineTo(-2, 2); frameShape.lineTo(-2, -2);
    const hole = new THREE.Path();
    hole.absarc(0, 0, 1.78, 0, Math.PI * 2, true);
    frameShape.holes.push(hole);
    const frameGeo = new THREE.ExtrudeGeometry(frameShape, { depth: 1.0, bevelEnabled: false, curveSegments: 40 });
    frameGeo.translate(0, 0, -0.5);
    const plastic = new THREE.MeshStandardMaterial({ color: 0x16191d, roughness: 0.55, envMapIntensity: 0.5 });
    const frame = new THREE.Mesh(frameGeo, plastic);
    frame.rotation.y = Math.PI / 2;           // furo voltado para o eixo x
    g.add(frame);

    this.fanRotor = new THREE.Group();
    g.add(this.fanRotor);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 0.7, 28), plastic);
    hub.rotation.z = Math.PI / 2;
    this.fanRotor.add(hub);
    const sticker = new THREE.Mesh(new THREE.CircleGeometry(0.5, 28),
      new THREE.MeshStandardMaterial({ color: 0x9aa3ab, metalness: 0.6, roughness: 0.35 }));
    sticker.rotation.y = Math.PI / 2;
    sticker.position.x = 0.36;
    this.fanRotor.add(sticker);

    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x23282e, roughness: 0.5, envMapIntensity: 0.5, side: THREE.DoubleSide });
    for (let i = 0; i < 7; i++) {
      const arm = new THREE.Group();
      arm.rotation.x = (i / 7) * Math.PI * 2;
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.08, 0.62), bladeMat);
      blade.position.y = 1.15;
      blade.rotation.y = 0.5;                  // passo da pa
      arm.add(blade);
      this.fanRotor.add(arm);
    }

    // borrao de movimento: disco translucido que aparece com a rotacao
    this.fanBlurMat = new THREE.MeshBasicMaterial({ color: 0x2a3038, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
    const blur = new THREE.Mesh(new THREE.RingGeometry(0.62, 1.74, 40), this.fanBlurMat);
    blur.rotation.y = Math.PI / 2;
    g.add(blur);
    // aneis de velocidade: mais visiveis quanto mais rapido
    this.fanStreakMat = new THREE.MeshBasicMaterial({ color: 0x9aa6c8, transparent: true, opacity: 0, depthWrite: false,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
    for (const r of [1.05, 1.4]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(r, r + 0.035, 48), this.fanStreakMat);
      ring.rotation.y = Math.PI / 2;
      ring.position.x = 0.38;
      g.add(ring);
    }

    // etiqueta flutuante: PWM e rotacao estimada
    this.fanLabelCanvas = document.createElement('canvas');
    this.fanLabelCanvas.width = 720; this.fanLabelCanvas.height = 128;
    this.fanLabelTex = new THREE.CanvasTexture(this.fanLabelCanvas);
    this.fanLabelTex.colorSpace = THREE.SRGBColorSpace;
    this.fanLabelMat = new THREE.SpriteMaterial({ map: this.fanLabelTex, transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
    this.fanLabel = new THREE.Sprite(this.fanLabelMat);
    this.fanLabel.scale.set(5.6, 1.0, 1);
    this.fanLabel.position.set(BOX.w / 2 + 2.6, FAN_Y + 3.1, 0);
    this.scene.add(this.fanLabel);
  }

  #drawFanLabel(f) {
    const c = this.fanLabelCanvas.getContext('2d');
    const W = this.fanLabelCanvas.width, H = this.fanLabelCanvas.height;
    c.clearRect(0, 0, W, H);
    c.fillStyle = 'rgba(16, 23, 30, 0.82)';
    roundRect(c, 4, 10, W - 8, H - 20, 26);
    c.fill();
    c.strokeStyle = 'rgba(139, 124, 240, 0.9)';
    c.lineWidth = 4;
    c.stroke();
    c.fillStyle = '#e6edf2';
    c.font = '600 50px "Barlow Semi Condensed", "Barlow", sans-serif';
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    const rpm = Math.round((f * FAN_RPM_MAX) / 50) * 50;
    c.fillText(`cooler ${Math.round(f * 100)} %  ·  ~${rpm.toLocaleString('pt-BR')} rpm`, W / 2, H / 2 + 2);
    this.fanLabelTex.needsUpdate = true;
  }

  // Manta de silicone sob um dissipador aletado, sobre isolante, no piso.
  #heater() {
    const g = new THREE.Group();
    this.scene.add(g);
    const y0 = BOX.base;
    // isolante (fibra ceramica): protege a base de acrilico
    const insul = new THREE.Mesh(new THREE.BoxGeometry(9.3, 0.14, 9.3),
      new THREE.MeshStandardMaterial({ color: 0xd9d4c7, roughness: 0.95, envMapIntensity: 0.3 }));
    insul.position.y = y0 + 0.07;
    g.add(insul);
    // manta de silicone: a borda laranja aparece por baixo do dissipador
    this.padMat = new THREE.MeshStandardMaterial({ color: 0xc2441c, roughness: 0.7, emissive: new THREE.Color(0xff4a12), emissiveIntensity: 0 });
    const pad = new THREE.Mesh(new THREE.BoxGeometry(8.95, 0.09, 8.95), this.padMat);
    pad.position.y = y0 + 0.185;
    g.add(pad);
    // fios da manta saindo para tras
    const wireMat = new THREE.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5 });
    [-0.5, 0.5].forEach((dz) => {
      const w = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.2, 8), wireMat);
      w.rotation.x = Math.PI / 2;
      w.position.set(3.6 + dz * 0.4, y0 + 0.2, -4.9);
      g.add(w);
    });

    // dissipador de aluminio aletado
    this.sinkMat = new THREE.MeshStandardMaterial({ color: 0xb9c1c8, metalness: 0.9, roughness: 0.38, envMapIntensity: 0.9,
      emissive: new THREE.Color(0xff5a1f), emissiveIntensity: 0 });
    const sbase = new THREE.Mesh(new THREE.BoxGeometry(SINK.w, SINK.base, SINK.w), this.sinkMat);
    sbase.position.y = SINK.y + SINK.base / 2;
    g.add(sbase);
    const pitch = SINK.w / SINK.fins;
    for (let i = 0; i < SINK.fins; i++) {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.14, SINK.fin, SINK.w), this.sinkMat);
      fin.position.set(-SINK.w / 2 + pitch * (i + 0.5), SINK.y + SINK.base + SINK.fin / 2, 0);
      g.add(fin);
    }
    // TH2 (KSD301) preso na lateral do dissipador
    const th2 = new THREE.Group();
    th2.position.set(SINK.w / 2 + 0.25, SINK.y + 0.55, 2.6);
    const can = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.42, 0.3, 24),
      new THREE.MeshStandardMaterial({ color: 0xcfd5da, metalness: 1, roughness: 0.25 }));
    can.rotation.z = Math.PI / 2;
    th2.add(can);
    const tab = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.3, 1.3),
      new THREE.MeshStandardMaterial({ color: 0xcfd5da, metalness: 1, roughness: 0.3 }));
    tab.position.x = -0.12;
    th2.add(tab);
    g.add(th2);
  }

  // ESP32 DevKit v1 numa meia protoboard, na mesa.
  #espBoard() {
    const g = new THREE.Group();
    g.position.copy(ESP_POS);
    g.rotation.y = ESP_ROT;
    this.scene.add(g);
    this.espGroup = g;

    // protoboard 8,2 x 5,5 cm
    const bbTex = new THREE.CanvasTexture(breadboardCanvas());
    bbTex.colorSpace = THREE.SRGBColorSpace;
    bbTex.anisotropy = 4;
    const bbTop = new THREE.MeshStandardMaterial({ map: bbTex, roughness: 0.75, envMapIntensity: 0.4 });
    const bbSide = new THREE.MeshStandardMaterial({ color: 0xe9e6dc, roughness: 0.8, envMapIntensity: 0.4 });
    const bb = new THREE.Mesh(new THREE.BoxGeometry(8.2, 0.85, 5.5), [bbSide, bbSide, bbTop, bbSide, bbSide, bbSide]);
    bb.position.y = 0.425;
    g.add(bb);

    const top = 0.85;
    // barras de pinos (2 x 15) apoiadas na protoboard
    const header = new THREE.MeshStandardMaterial({ color: 0x15171a, roughness: 0.6 });
    [-1.27, 1.27].forEach((z) => {
      const strip = new THREE.Mesh(new THREE.BoxGeometry(3.85, 0.25, 0.25), header);
      strip.position.set(0, top + 0.125, z);
      g.add(strip);
    });

    // placa: 5,2 x 2,8 cm
    const pcbTex = new THREE.CanvasTexture(devkitCanvas());
    pcbTex.colorSpace = THREE.SRGBColorSpace;
    pcbTex.anisotropy = 4;
    const pcbTop = new THREE.MeshStandardMaterial({ map: pcbTex, roughness: 0.5, envMapIntensity: 0.5 });
    const pcbSide = new THREE.MeshStandardMaterial({ color: 0x14171d, roughness: 0.5 });
    const py = top + 0.25 + 0.08;
    const pcb = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.16, 2.8), [pcbSide, pcbSide, pcbTop, pcbSide, pcbSide, pcbSide]);
    pcb.position.y = py;
    g.add(pcb);
    const sy = py + 0.08;

    // ESP-WROOM-32: antena (PCB) + blindagem metalica
    const shieldTex = new THREE.CanvasTexture(shieldCanvas());
    shieldTex.colorSpace = THREE.SRGBColorSpace;
    const shieldTop = new THREE.MeshStandardMaterial({ map: shieldTex, metalness: 0.85, roughness: 0.35, envMapIntensity: 1.0 });
    const shieldSide = new THREE.MeshStandardMaterial({ color: 0xc8cdd2, metalness: 0.9, roughness: 0.3 });
    const modPcb = new THREE.Mesh(new THREE.BoxGeometry(2.55, 0.08, 1.8),
      new THREE.MeshStandardMaterial({ color: 0x1c2026, roughness: 0.5 }));
    modPcb.position.set(-1.2, sy + 0.04, 0);
    g.add(modPcb);
    const shield = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.3, 1.6), [shieldSide, shieldSide, shieldTop, shieldSide, shieldSide, shieldSide]);
    shield.position.set(-0.85, sy + 0.08 + 0.15, 0);
    g.add(shield);
    const ant = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 1.6),
      new THREE.MeshStandardMaterial({ map: antennaTexture(), roughness: 0.4, metalness: 0.4 }));
    ant.rotation.x = -Math.PI / 2;
    ant.position.set(-2.2, sy + 0.085, 0);
    g.add(ant);

    // micro-USB, regulador, botoes
    const metal = new THREE.MeshStandardMaterial({ color: 0xd2d6da, metalness: 1, roughness: 0.25 });
    const usb = new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.28, 0.78), metal);
    usb.position.set(2.42, sy + 0.14, 0);
    g.add(usb);
    const black = new THREE.MeshStandardMaterial({ color: 0x111316, roughness: 0.45 });
    const reg = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.16, 0.35), black);
    reg.position.set(1.35, sy + 0.08, 0.75);
    g.add(reg);
    [[1.85, -0.95], [1.85, 0.95]].forEach(([x, z]) => {
      const base = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.14, 0.45), metal);
      base.position.set(x, sy + 0.07, z);
      g.add(base);
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.1, 16), black);
      cap.position.set(x, sy + 0.19, z);
      g.add(cap);
    });

    // LEDs: vermelho (alimentacao) sempre aceso, azul = GPIO2
    this.ledPwr = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.0, 0.18, 0.12).multiplyScalar(2.2), toneMapped: false });
    const lp = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.08, 0.1), this.ledPwr);
    lp.position.set(1.25, sy + 0.04, -0.5);
    g.add(lp);
    this.ledBlueMat = new THREE.MeshBasicMaterial({ color: 0x0c1830, toneMapped: false });
    const lb = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.08, 0.1), this.ledBlueMat);
    lb.position.set(1.25, sy + 0.04, -0.2);
    g.add(lb);
    this.ledGlowMat = new THREE.SpriteMaterial({ map: radialTexture('rgba(90,150,255,1)', 'rgba(90,150,255,0)'), transparent: true,
      opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending });
    const glow = new THREE.Sprite(this.ledGlowMat);
    glow.scale.set(0.9, 0.9, 1);
    glow.position.set(1.25, sy + 0.12, -0.2);
    g.add(glow);

    // etiqueta da placa na mesa
    const lbl = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 0.7),
      new THREE.MeshBasicMaterial({ map: textTexture('ESP32 DevKit v1 · protoboard', 34), transparent: true, depthWrite: false }));
    lbl.rotation.x = -Math.PI / 2;
    lbl.position.set(0, 0.012, 3.3);
    g.add(lbl);
  }

  // Jumpers: da protoboard ate a camara (gates e sensor) e ate o display.
  #wires() {
    const local = (x, z) => new THREE.Vector3(x, 0.9, z)
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), ESP_ROT).add(ESP_POS);
    const sideX = (BOX.w + 1.2) / 2 + 0.02;
    const runs = [
      // [cor, ponto na protoboard (local), destino (mundo)]
      [0xff8a1c, [-1.8, -2.3], new THREE.Vector3(sideX, 0.35, 2.2)],    // PWM_GATE  (lampadas)
      [0xd8342a, [-1.0, -2.3], new THREE.Vector3(sideX, 0.35, 1.2)],    // HEAT_GATE (manta)
      [0x3b6fe0, [-0.2, -2.3], new THREE.Vector3(sideX, 0.35, 0.2)],    // FAN_GATE  (cooler)
      [0x2fb36a, [0.6, -2.3], new THREE.Vector3(sideX, 0.35, -0.8)],    // TEMP_S    (LM35)
      [0xe23b3b, [-2.6, 2.3], new THREE.Vector3(0.45, 0.44, 6.55)],     // 3V3 display
      [0x222428, [-1.8, 2.3], new THREE.Vector3(0.15, 0.44, 6.55)],     // GND display
      [0xf2c230, [-1.0, 2.3], new THREE.Vector3(-0.15, 0.44, 6.55)],    // CLK
      [0x34c6d8, [-0.2, 2.3], new THREE.Vector3(-0.45, 0.44, 6.55)],    // DIO
    ];
    for (const [color, [lx, lz], end] of runs) {
      const a = local(lx, lz);
      // sobe da protoboard, faz um arco e deita na mesa ate o destino
      const p1 = a.clone().add(new THREE.Vector3(0, 0.5, 0));
      const p2 = a.clone().lerp(end, 0.22); p2.y = 0.75;
      const p3 = a.clone().lerp(end, 0.55); p3.y = 0.1;
      const p4 = a.clone().lerp(end, 0.85); p4.y = 0.1;
      const curve = new THREE.CatmullRomCurve3([a, p1, p2, p3, p4, end]);
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, 0.055, 6, false),
        new THREE.MeshStandardMaterial({ color, roughness: 0.45, envMapIntensity: 0.4 }));
      this.scene.add(tube);
    }
  }

  // Frestas de entrada de ar, embaixo, na parede oposta ao cooler.
  #vents() {
    const mat = new THREE.MeshBasicMaterial({ color: 0x06080a });
    for (let i = 0; i < 4; i++) {
      const slot = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.22, 4.2), mat);
      slot.position.set(-BOX.w / 2 - 0.01, BOX.base + 0.9 + i * 0.5, 0);
      this.scene.add(slot);
    }
  }

  // Ar em quatro grupos, num unico Points aditivo (cor preta = invisivel):
  //   out    - jato quente saindo do cooler
  //   intake - ar frio entrando pelas frestas
  //   path   - caminho interno, das frestas ate o cooler (esquentando)
  //   conv   - conveccao subindo do dissipador quando a manta esquenta
  #air() {
    const pos = new Float32Array(AIR_N * 3);
    const col = new Float32Array(AIR_N * 3);
    this.airSeed = [];
    const add = (kind, n) => {
      for (let i = 0; i < n; i++) {
        const r = Math.sqrt(Math.random());
        const a = Math.random() * Math.PI * 2;
        this.airSeed.push({
          kind, p: Math.random(), v: 0.7 + Math.random() * 0.6,
          y: r * Math.sin(a), z: r * Math.cos(a),
          x0: (Math.random() - 0.5) * SINK.w * 0.9, z0: (Math.random() - 0.5) * SINK.w * 0.9,
          w: Math.random() * Math.PI * 2,
        });
      }
    };
    add('out', AIR.out); add('intake', AIR.intake); add('path', AIR.path); add('conv', AIR.conv);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.34, map: radialTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)'), vertexColors: true,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true,
    });
    this.air = new THREE.Points(geo, mat);
    this.air.frustumCulled = false;
    this.scene.add(this.air);
  }

  #updateAir(dt, f, heatLvl) {
    const pos = this.air.geometry.attributes.position.array;
    const col = this.air.geometry.attributes.color.array;
    const warm = Math.max(0, Math.min(1, (this.target.T - this.target.amb) / 30));
    const still = this.reduceMotion;
    const cold = [0.28, 0.5, 0.95], hot = [1.0, 0.55, 0.22];
    const mix = (k, m) => [cold[0] + (hot[0] - cold[0]) * m, cold[1] + (hot[1] - cold[1]) * m, cold[2] + (hot[2] - cold[2]) * m].map((c) => c * k);
    const ventX = -BOX.w / 2 + 0.5, fanX = BOX.w / 2 - 0.7;
    const topY = BOX.base + BOX.h - 0.9;
    for (let i = 0; i < AIR_N; i++) {
      const s = this.airSeed[i];
      let x, y, z, c;
      if (s.kind === 'out') {
        if (!still) s.p += dt * s.v * (0.2 + 1.3 * f);
        if (s.p > 1) s.p -= 1;
        x = BOX.w / 2 + 0.6 + s.p * 8;
        y = FAN_Y + s.y * 1.4 * (1 + s.p * 0.9) + s.p * 0.9;
        z = s.z * 1.4 * (1 + s.p * 0.9);
        c = mix((1 - s.p) * f * 1.1, 0.45 + 0.55 * warm);
      } else if (s.kind === 'intake') {
        if (!still) s.p += dt * s.v * (0.2 + 1.0 * f);
        if (s.p > 1) s.p -= 1;
        x = -BOX.w / 2 - 5.5 + s.p * 5.3;
        y = BOX.base + 1.7 + s.y * 0.7;
        z = s.z * 2.2;
        c = mix(Math.sin(s.p * Math.PI) * f * 0.9, 0);
      } else if (s.kind === 'path') {
        // curva das frestas (embaixo, -x) ate o cooler (em cima, +x)
        if (!still) s.p += dt * s.v * (0.12 + 0.85 * f);
        if (s.p > 1) s.p -= 1;
        const p = s.p;
        x = ventX + (fanX - ventX) * p;
        const base = BOX.base + 1.7 + (FAN_Y - BOX.base - 1.7) * (p * p * (3 - 2 * p));
        y = base + s.y * 1.1 * (1 - 0.5 * p) + Math.sin(p * Math.PI) * 1.2;
        z = s.z * 3.2 * (1 - 0.55 * p);
        c = mix(Math.sin(Math.min(1, p * 1.15) * Math.PI) * f * 0.85, p);
      } else {
        // conveccao: sobe do dissipador e, com o cooler ligado, e' puxada para ele
        if (!still) s.p += dt * s.v * (0.18 + 0.25 * heatLvl);
        if (s.p > 1) { s.p -= 1; s.x0 = (Math.random() - 0.5) * SINK.w * 0.9; s.z0 = (Math.random() - 0.5) * SINK.w * 0.9; }
        const p = s.p;
        const y0 = SINK.y + SINK.base + SINK.fin;
        y = y0 + p * (topY - y0);
        x = s.x0 + Math.sin(s.w + p * 6) * 0.25 + (fanX - s.x0) * f * p * p;
        z = s.z0 * (1 - 0.6 * p * f) + Math.cos(s.w + p * 5) * 0.25;
        const k = Math.sin(Math.min(1, p * 1.2) * Math.PI) * heatLvl * (1 - 0.6 * f);
        c = [1.25 * k, 0.5 * k, 0.18 * k];
      }
      pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
      col[i * 3] = c[0]; col[i * 3 + 1] = c[1]; col[i * 3 + 2] = c[2];
    }
    this.air.geometry.attributes.position.needsUpdate = true;
    this.air.geometry.attributes.color.needsUpdate = true;
    this.air.visible = f > 0.01 || heatLvl > 0.02;
  }

  // Modulo TM1637 apoiado na frente da base.
  #displayModule() {
    const g = new THREE.Group();
    g.position.set(0, 1.35, (BOX.d + 1.2) / 2 + 0.35);
    g.rotation.x = -0.28;
    this.scene.add(g);

    const pcb = new THREE.Mesh(new THREE.BoxGeometry(4.2, 2.4, 0.16),
      new THREE.MeshStandardMaterial({ color: 0x1b4f8f, roughness: 0.55, envMapIntensity: 0.4 }));
    g.add(pcb);
    const bezel = new THREE.Mesh(new THREE.BoxGeometry(3.6, 1.45, 0.42),
      new THREE.MeshStandardMaterial({ color: 0x0b0c0e, roughness: 0.4 }));
    bezel.position.set(0, 0.15, 0.25);
    g.add(bezel);
    const pins = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.22, 0.3),
      new THREE.MeshStandardMaterial({ color: 0xc9a227, metalness: 0.9, roughness: 0.3 }));
    pins.position.set(0, -1.0, 0.2);
    g.add(pins);
    // suporte: o modulo se apoia na base
    const foot = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.12, 0.9),
      new THREE.MeshStandardMaterial({ color: 0x0c0f12, roughness: 0.4 }));
    foot.position.set(0, -1.25, -0.35);
    g.add(foot);

    this.dispCanvas = document.createElement('canvas');
    this.dispCanvas.width = 512; this.dispCanvas.height = 192;
    this.dispTex = new THREE.CanvasTexture(this.dispCanvas);
    this.dispTex.colorSpace = THREE.SRGBColorSpace;
    const face = new THREE.Mesh(new THREE.PlaneGeometry(3.3, 1.24),
      new THREE.MeshBasicMaterial({ map: this.dispTex, toneMapped: false }));
    face.position.set(0, 0.15, 0.47);
    g.add(face);
    this.#drawDisplay(null);
  }

  #drawDisplay(cells) {
    const c = this.dispCanvas.getContext('2d');
    const W = this.dispCanvas.width, H = this.dispCanvas.height;
    c.fillStyle = '#0a0606';
    c.fillRect(0, 0, W, H);
    const list = cells || Array.from({ length: 4 }, () => ({ bits: 0x40, dp: false }));
    for (let i = 0; i < 4; i++) drawSevenSeg(c, 26 + i * 122, 22, 96, 148, list[i].bits, list[i].dp);
    this.dispTex.needsUpdate = true;
  }

  #lamp(x, y) {
    const g = new THREE.Group();
    g.position.set(x, y, 0);
    this.scene.add(g);

    const socket = new THREE.Mesh(
      new THREE.CylinderGeometry(0.5, 0.55, 0.9, 24),
      new THREE.MeshStandardMaterial({ color: 0x2a2f35, roughness: 0.6, envMapIntensity: 0.4 }),
    );
    socket.position.y = -0.45;
    g.add(socket);

    // W5W: bulbo de vidro de ~10 mm, sem base metalica
    const glassMat = new THREE.MeshPhysicalMaterial({
      color: 0xffffff, transparent: true, opacity: 0.35, roughness: 0.05,
      clearcoat: 1, envMapIntensity: 1.2, emissive: COLD.clone(), emissiveIntensity: 0,
      depthWrite: false,
    });
    const glass = new THREE.Mesh(new THREE.CapsuleGeometry(0.46, 1.25, 8, 24), glassMat);
    glass.position.y = -0.9 - 1.08;
    g.add(glass);

    const filMat = new THREE.MeshBasicMaterial({ color: 0x3a2a22 });
    const fil = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 0.55, 8), filMat);
    fil.rotation.z = Math.PI / 2;
    fil.position.y = glass.position.y - 0.15;
    g.add(fil);

    const light = new THREE.PointLight(COLD.clone(), 0, 0, 2);
    light.position.y = glass.position.y;
    g.add(light);

    return { glassMat, filMat, light };
  }

  #sensor(x, y, z, top) {
    const g = new THREE.Group();
    g.position.set(x, y, z);
    this.scene.add(g);
    const black = new THREE.MeshStandardMaterial({ color: 0x111316, roughness: 0.5, envMapIntensity: 0.5 });
    // corpo TO-92: meio cilindro
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.55, 20, 1, false, 0, Math.PI), black);
    g.add(body);
    const flat = new THREE.Mesh(new THREE.PlaneGeometry(0.56, 0.55), black);
    flat.rotation.y = Math.PI / 2;
    g.add(flat);
    // tres fios subindo ate o teto
    const wireMat = new THREE.MeshStandardMaterial({ color: 0x8a6b46, metalness: 0.6, roughness: 0.4 });
    [-0.15, 0, 0.15].forEach((dz, i) => {
      const len = top - 0.6 - y;
      const w = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, len, 6), wireMat);
      w.position.set(0, len / 2 + 0.28, dz + (i - 1) * 0.02);
      g.add(w);
    });
  }

  #resize() {
    if (!this.renderer) return;
    const { width, height } = this.host.getBoundingClientRect();
    if (width < 2 || height < 2) return;
    this.renderer.setSize(width, height, false);
    this.composer.setSize(width, height);
    this.bloom.resolution.set(width / 2, height / 2);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    if (!this.framed || this.lastAspect !== this.camera.aspect) this.#frameBox();
  }

  // Afasta a camera o bastante para a caixa (esfera de ~9 cm) caber inteira,
  // tanto na vertical quanto na horizontal. Em tela de celular, em pe, o
  // eixo limitante e' o horizontal. Mantem a direcao atual da camera.
  #frameBox() {
    const radius = 11.2;      // caixa + protoboard na mesa
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * this.camera.aspect);
    const dist = radius / Math.sin(Math.min(vfov, hfov) / 2);
    // em retrato, sobe o alvo para a caixa ficar acima da leitura de temperatura
    const portrait = this.camera.aspect < 0.9;
    this.controls.target.set(1.4, BOX.base + BOX.h * (portrait ? 0.25 : 0.32), 1.6);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    this.camera.position.copy(this.controls.target).addScaledVector(dir, dist);
    this.controls.maxDistance = Math.max(48, dist * 1.6);
    this.framed = true;
    this.lastAspect = this.camera.aspect;
  }

  #frame() {
    if (!this.visible || this.hidden) return;
    const dt = Math.min(this.clock.getDelta(), 0.1);

    const t = this.target;
    const goal = t.fault ? 0 : Math.max(0, Math.min(1, t.ue));
    // inercia termica do filamento: ~0,25 s
    this.shown.b += (goal - this.shown.b) * (1 - Math.exp(-dt / 0.25));
    const heatGoal = Math.max(0, Math.min(1, (t.T - t.amb) / 30));
    this.shown.heat += (heatGoal - this.shown.heat) * (1 - Math.exp(-dt / 0.8));

    const p = this.shown.b;
    // Luz visivel de um filamento cresce bem mais rapido que a potencia.
    const lum = Math.pow(p, 1.7);
    const color = COLD.clone().lerp(HOT, Math.pow(p, 0.7));

    for (const L of this.lamps) {
      L.light.color.copy(color);
      L.light.intensity = 70 * lum;
      L.glassMat.emissive.copy(color);
      L.glassMat.emissiveIntensity = 0.1 + 1.6 * lum;
      L.filMat.color.copy(p < 0.03 ? new THREE.Color(0x3a2a22) : color.clone().multiplyScalar(1 + 5 * lum));
    }

    this.heatMat.opacity = 0.09 * this.shown.heat;
    this.edgeMat.color.copy(ACRYLIC_EDGE).lerp(TUNGSTEN, Math.min(1, lum * 0.85));
    this.edgeMat.opacity = 0.5 + 0.4 * lum;
    this.bloom.strength = 0.25 + 0.65 * lum;

    // cooler: inercia do rotor ~0,8 s; giro visual (o real e' rapido demais)
    const fanGoal = Math.max(0, Math.min(1, t.fan || 0));
    this.shown.fan += (fanGoal - this.shown.fan) * (1 - Math.exp(-dt / 0.8));
    const f = this.shown.fan;
    // Giro proporcional ao PWM, limitado a ~10 rad/s na tela: o rotor real
    // (ate 6000 rpm) viraria efeito estroboscopico a 60 quadros/s.
    if (!this.reduceMotion && f > 0.005) this.fanAngle += (0.6 + (FAN_VISUAL_MAX - 0.6) * f) * dt;
    this.fanRotor.rotation.x = this.fanAngle;
    this.fanBlurMat.opacity = Math.min(0.6, f * 0.75);
    this.fanStreakMat.opacity = 0.5 * f;
    this.fanLabelMat.opacity += ((fanGoal > 0.01 ? 1 : 0) - this.fanLabelMat.opacity) * (1 - Math.exp(-dt / 0.3));
    const labelKey = Math.round(fanGoal * 100);
    if (labelKey !== this.fanLabelKey && fanGoal > 0.01) { this.fanLabelKey = labelKey; this.#drawFanLabel(fanGoal); }

    // manta: a potencia esquenta a borda; o dissipador segue a temperatura dele
    const padGoal = t.fault ? 0 : Math.max(0, Math.min(1, t.heat || 0));
    this.shown.pad += (padGoal - this.shown.pad) * (1 - Math.exp(-dt / 0.6));
    const sinkGoal = t.sink != null ? t.sink : t.T + 40 * padGoal;
    this.shown.sink += (sinkGoal - this.shown.sink) * (1 - Math.exp(-dt / 0.8));
    const sinkHot = Math.max(0, Math.min(1, (this.shown.sink - 30) / 70));
    this.padMat.emissiveIntensity = 1.4 * this.shown.pad;
    this.sinkMat.emissiveIntensity = 0.55 * sinkHot * sinkHot;
    const heatLvl = Math.max(0, Math.min(1, (this.shown.sink - t.T) / 14 + 0.5 * this.shown.pad));
    this.#updateAir(dt, f, heatLvl);

    // LED azul da ESP32 (GPIO2): o firmware inverte a cada amostra
    if (t.beat !== this.lastBeat) { this.lastBeat = t.beat; this.ledOn = t.fault ? true : !this.ledOn; }
    this.ledBlueMat.color.setRGB(this.ledOn ? 0.35 : 0.04, this.ledOn ? 0.6 : 0.07, this.ledOn ? 2.4 : 0.14);
    this.ledGlowMat.opacity = this.ledOn ? 0.9 : 0;

    if (t.displayKey !== this.drawnDisplay) {
      this.drawnDisplay = t.displayKey;
      this.#drawDisplay(t.display);
    }

    this.scene.background.copy(this.bgCold).lerp(this.bgWarm, lum * 0.8);
    this.scene.fog.color.copy(this.scene.background);
    document.documentElement.style.setProperty('--glow', lum.toFixed(3));

    this.controls.update();
    this.composer.render();
  }
}

// Display de 7 segmentos desenhado em canvas. bits: a=0 ... g=6.
function drawSevenSeg(c, x, y, w, h, bits, dp) {
  const t = w * 0.17;                  // espessura do segmento
  const sk = 0.10;                     // inclinacao, como num display real
  const on = '#ff3b2f', off = '#2a0d0b';
  const seg = (x0, y0, x1, y1) => {
    // hexagono alongado entre (x0,y0) e (x1,y1)
    c.beginPath();
    if (y0 === y1) {
      c.moveTo(x0, y0); c.lineTo(x0 + t / 2, y0 - t / 2); c.lineTo(x1 - t / 2, y1 - t / 2);
      c.lineTo(x1, y1); c.lineTo(x1 - t / 2, y1 + t / 2); c.lineTo(x0 + t / 2, y0 + t / 2);
    } else {
      c.moveTo(x0, y0); c.lineTo(x0 + t / 2, y0 + t / 2); c.lineTo(x1 + t / 2, y1 - t / 2);
      c.lineTo(x1, y1); c.lineTo(x1 - t / 2, y1 - t / 2); c.lineTo(x0 - t / 2, y0 + t / 2);
    }
    c.closePath();
    c.fill();
  };
  const P = (px, py) => [x + px + (h - py) * sk, y + py];   // aplica a inclinacao
  const g = 3;
  const L = t / 2 + g, R = w - t / 2 - g, T0 = t / 2, M = h / 2, B = h - t / 2;
  const segs = [
    [P(L, T0), P(R, T0)],             // a
    [P(R + g, T0 + g), P(R + g, M - g)],   // b
    [P(R + g, M + g), P(R + g, B - g)],   // c
    [P(L, B), P(R, B)],               // d
    [P(L - g, M + g), P(L - g, B - g)],   // e
    [P(L - g, T0 + g), P(L - g, M - g)],   // f
    [P(L, M), P(R, M)],               // g
  ];
  segs.forEach(([[ax, ay], [bx, by]], i) => {
    c.fillStyle = bits & (1 << i) ? on : off;
    if (Math.abs(ay - by) < 1) seg(ax, ay, bx, by);
    else seg(ax, ay, bx, by);
  });
  const [dx, dy] = P(w + t * 0.4, B);
  c.fillStyle = dp ? on : off;
  c.beginPath(); c.arc(dx, dy, t * 0.55, 0, Math.PI * 2); c.fill();
}

function radialTexture(inner, outer) {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(64, 64, 8, 64, 64, 64);
  grd.addColorStop(0, inner);
  grd.addColorStop(1, outer);
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function roundRect(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x + r, y);
  c.arcTo(x + w, y, x + w, y + h, r);
  c.arcTo(x + w, y + h, x, y + h, r);
  c.arcTo(x, y + h, x, y, r);
  c.arcTo(x, y, x + w, y, r);
  c.closePath();
}

function textTexture(text, px) {
  const c = document.createElement('canvas');
  c.width = 1024; c.height = 170;
  const g = c.getContext('2d');
  g.fillStyle = 'rgba(140,155,168,0.95)';
  g.font = `500 ${px * 2}px "Barlow", sans-serif`;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text, 512, 85);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// Meia protoboard: furos, canal central e trilhos vermelho/azul.
function breadboardCanvas() {
  const c = document.createElement('canvas');
  c.width = 1312; c.height = 880;              // 160 px/cm
  const g = c.getContext('2d');
  g.fillStyle = '#efece3';
  g.fillRect(0, 0, c.width, c.height);
  const pitch = 0.254 * 160;
  const hole = (x, y) => { g.fillStyle = '#4a4740'; g.fillRect(x - 6, y - 6, 12, 12); };
  // canal central
  g.fillStyle = '#d8d4c8';
  g.fillRect(0, c.height / 2 - 20, c.width, 40);
  for (let col = 0; col < 30; col++) {
    const x = 60 + col * pitch;
    for (let r = 0; r < 5; r++) { hole(x, c.height / 2 - 50 - r * pitch); hole(x, c.height / 2 + 50 + r * pitch); }
  }
  // trilhos
  const rail = (y, color) => { g.strokeStyle = color; g.lineWidth = 5; g.beginPath(); g.moveTo(40, y); g.lineTo(c.width - 40, y); g.stroke(); };
  rail(50, '#d33'); rail(150, '#36c'); rail(c.height - 150, '#d33'); rail(c.height - 50, '#36c');
  for (let col = 0; col < 25; col++) {
    const x = 80 + col * pitch * 1.2;
    hole(x, 85); hole(x, 115); hole(x, c.height - 115); hole(x, c.height - 85);
  }
  return c;
}

// Face da DevKit v1: PCB escura, serigrafia e nomes dos pinos.
function devkitCanvas() {
  const c = document.createElement('canvas');
  c.width = 1040; c.height = 560;              // 200 px/cm
  const g = c.getContext('2d');
  g.fillStyle = '#121a2a';
  g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = '#c9a227';
  for (let i = 0; i < 15; i++) {
    const x = 160 + i * 50.8;
    g.beginPath(); g.arc(x, 26, 12, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.arc(x, c.height - 26, 12, 0, Math.PI * 2); g.fill();
  }
  g.fillStyle = '#e8edf2';
  g.font = '600 30px "Barlow", sans-serif';
  g.textAlign = 'center';
  g.fillText('ESP32 DEVKIT V1', 720, 300);
  g.font = '500 20px "Barlow", sans-serif';
  const top = ['EN', 'VP', 'VN', 'D34', 'D35', 'D32', 'D33', 'D25', 'D26', 'D27', 'D14', 'D12', 'D13', 'GND', 'VIN'];
  const bot = ['D23', 'D22', 'TX0', 'RX0', 'D21', 'D19', 'D18', 'D5', 'TX2', 'RX2', 'D4', 'D2', 'D15', 'GND', '3V3'];
  top.forEach((t, i) => g.fillText(t, 160 + i * 50.8, 66));
  bot.forEach((t, i) => g.fillText(t, 160 + i * 50.8, c.height - 52));
  return c;
}

function shieldCanvas() {
  const c = document.createElement('canvas');
  c.width = 350; c.height = 320;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, 350, 320);
  grd.addColorStop(0, '#d9dde1'); grd.addColorStop(1, '#aeb4ba');
  g.fillStyle = grd;
  g.fillRect(0, 0, 350, 320);
  g.fillStyle = '#4a5058';
  g.font = '700 34px "Barlow", sans-serif';
  g.textAlign = 'center';
  g.fillText('ESP-WROOM-32', 175, 150);
  g.font = '500 22px "Barlow", sans-serif';
  g.fillText('Wi-Fi · BT', 175, 190);
  const tex = c;
  return tex;
}

function antennaTexture() {
  const c = document.createElement('canvas');
  c.width = 128; c.height = 320;
  const g = c.getContext('2d');
  g.fillStyle = '#1c2026';
  g.fillRect(0, 0, 128, 320);
  g.strokeStyle = '#c9a227';
  g.lineWidth = 8;
  g.beginPath();
  g.moveTo(64, 310);
  g.lineTo(64, 280);
  for (let i = 0; i < 7; i++) {
    const y = 260 - i * 34;
    g.lineTo(i % 2 ? 108 : 20, y + 17);
    g.lineTo(i % 2 ? 108 : 20, y - 17);
  }
  g.stroke();
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}
