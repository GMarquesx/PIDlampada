/*
 * A camara em 3D - Rev. D: policarbonato 6 mm, 25 x 25 x 25 cm.
 *
 * Unidade = 1 cm. Paredes de policarbonato cristal presas por cantoneiras
 * de aluminio, sobre uma base de MDF. A frente e' uma porta (dobradicas a
 * esquerda, puxador e ima a direita). No teto, cinco W5W numa chapa de
 * aluminio; o brilho e a cor de cada uma seguem a potencia real entregue.
 *
 * No piso, de baixo para cima: isolante, manta de silicone de 80 W (a borda
 * laranja aparece), dois dissipadores aletados e, 7 cm acima do piso, a
 * prateleira de aluminio perfurado onde ficam as amostras. A ventoinha de
 * circulacao M2 (60 mm, sempre ligada) sopra o ar pelas aletas; o ar quente
 * sobe pelos furos da prateleira.
 *
 * Cooler de exaustao de 80 mm na parede direita, no alto; frestas de
 * entrada embaixo na parede oposta, na altura do dissipador. Gira na
 * proporcao do PWM, com etiqueta de % e rpm, e o ar mostra o caminho.
 *
 * Na mesa: modulo TM1637 (mesma leitura do Wokwi) e a ESP32 DevKit v1 numa
 * protoboard, com jumpers e o LED azul (GPIO2) piscando a cada amostra.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const BOX = { w: 25, h: 25, d: 25, base: 1.6, t: 0.6 };   // medidas externas da caixa de PC
const BASE_W = BOX.w + 5, BASE_D = BOX.d + 5;              // base de MDF 300 x 300
const IN = BOX.w - 2 * BOX.t;                              // 23,8 cm por dentro
const FLOOR = BOX.base;                                    // piso interno
const TOP = BOX.base + BOX.h;
const SHELF_Y = FLOOR + 7.0;                               // prateleira perfurada
const LAMP_X = [-9, -4.5, 0, 4.5, 9];
const FAN_Y = TOP - 6.2;                                   // exaustao 80 mm
const FAN_SCALE = 2;                                       // geometria base = 40 mm
const CIRC = { scale: 1.5, y: FLOOR + 3.6, z: -IN / 2 + 1.3 };   // M2 60 mm, parede do fundo
const SINK = { w: 20, base: 0.5, fin: 2.4, fins: 13, y: FLOOR + 0.45 };

// Cor do filamento por potencia: vermelho-alaranjado fraco ate branco quente.
const COLD = new THREE.Color('#ff4a12');
const HOT = new THREE.Color('#ffd7a3');
const PC_EDGE = new THREE.Color('#a9dcec');
const TUNGSTEN = new THREE.Color('#ffb25b');
const ESP_POS = new THREE.Vector3(14.5, 0, 22.5);         // protoboard na mesa
const ESP_ROT = -0.35;
const AIR = { out: 110, intake: 60, path: 170, circ: 90, conv: 130 };
const AIR_N = AIR.out + AIR.intake + AIR.path + AIR.circ + AIR.conv;
const FAN_RPM_MAX = 3000;                                  // ventoinha 80 mm a 12 V
const FAN_VISUAL_MAX = 9;                                  // rad/s na tela (sem efeito estroboscopico)

export class ChamberScene {
  constructor(host) {
    this.host = host;
    this.target = { ue: 0, T: 25, amb: 25, fault: false, fan: 0, display: null, displayKey: '',
      heat: 0, hon: 1, sink: null, beat: null };
    this.shown = { b: 0, heat: 0, fan: 0, pad: 0, sink: 25 };
    this.fanAngle = 0;
    this.circAngle = 0;
    this.ledOn = false;
    this.lastBeat = null;
    this.fanLabelKey = '';
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
    this.bgCold = new THREE.Color('#10171e');
    this.bgWarm = new THREE.Color('#2b1c10');
    this.scene.background = this.bgCold.clone();
    this.scene.fog = new THREE.Fog(this.bgCold.clone(), 110, 280);
    const pmrem = new THREE.PMREMGenerator(r);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(r), 0.04).texture;

    this.camera = new THREE.PerspectiveCamera(30, 1, 1, 500);
    this.camera.position.set(44, 34, 56);

    this.controls = new OrbitControls(this.camera, r.domElement);
    this.controls.target.set(3, FLOOR + 10, 4);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.minDistance = 35;
    this.controls.maxDistance = 160;
    this.controls.minPolarAngle = 0.35;
    this.controls.maxPolarAngle = 1.48;
    this.controls.autoRotate = !this.reduceMotion;
    this.controls.autoRotateSpeed = 0.5;
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

    new IntersectionObserver(([e]) => { this.visible = e.isIntersecting; }).observe(host);
    document.addEventListener('visibilitychange', () => { this.hidden = document.hidden; });

    this.clock = new THREE.Clock();
    r.setAnimationLoop(() => this.#frame());
  }

  setState(next) { Object.assign(this.target, next); }

  #build() {
    const s = this.scene;
    s.add(new THREE.HemisphereLight(0x9fb6cc, 0x0b0f13, 0.4));

    const ground = new THREE.Mesh(new THREE.CircleGeometry(170, 64),
      new THREE.MeshStandardMaterial({ color: 0x1b242d, roughness: 0.92, metalness: 0, envMapIntensity: 0.2 }));
    ground.rotation.x = -Math.PI / 2;
    s.add(ground);
    const shadow = new THREE.Mesh(new THREE.PlaneGeometry(BASE_W * 1.8, BASE_D * 1.8),
      new THREE.MeshBasicMaterial({ map: radialTexture('rgba(0,0,0,0.75)', 'rgba(0,0,0,0)'), transparent: true, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = 0.02;
    s.add(shadow);

    // base de MDF 15 mm pintada de preto (isola melhor que acrilico)
    const base = new THREE.Mesh(new THREE.BoxGeometry(BASE_W, BOX.base, BASE_D),
      new THREE.MeshStandardMaterial({ color: 0x15181c, roughness: 0.8, envMapIntensity: 0.4 }));
    base.position.y = BOX.base / 2;
    s.add(base);

    // volume interno que esquenta de cor com a temperatura
    this.heatMat = new THREE.MeshBasicMaterial({ color: 0xff8a3d, transparent: true, opacity: 0, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.BackSide });
    const heat = new THREE.Mesh(new THREE.BoxGeometry(IN - 0.4, BOX.h - BOX.t - 0.4, IN - 0.4), this.heatMat);
    heat.position.y = FLOOR + (BOX.h - BOX.t) / 2;
    s.add(heat);

    // chapa de aluminio no teto com as cinco lampadas
    const plate = new THREE.Mesh(new THREE.BoxGeometry(21.5, 0.3, 6.5),
      new THREE.MeshStandardMaterial({ color: 0xc9d0d6, metalness: 1, roughness: 0.32, envMapIntensity: 0.9 }));
    plate.position.y = TOP - BOX.t - 0.15;
    s.add(plate);
    this.lamps = LAMP_X.map((x) => this.#lamp(x, TOP - BOX.t - 0.3));

    // LM35 pendurado a meia altura, acima da prateleira
    this.#sensor(5.5, SHELF_Y + 7.5, -4.5, TOP - BOX.t + 0.3);

    this.#heater();
    this.#shelf();
    this.#walls();
    this.#fans();
    this.#vents();
    this.#air();
    this.#displayModule();
    this.#espBoard();
    this.#wires();
  }

  // Paredes de PC (cada uma um painel de 6 mm), cantoneiras e a porta.
  #walls() {
    this.pcMat = new THREE.MeshPhysicalMaterial({
      color: 0xe6f6fb, transparent: true, opacity: 0.07, roughness: 0.04, metalness: 0,
      clearcoat: 0.4, clearcoatRoughness: 0.05, envMapIntensity: 0.18, side: THREE.DoubleSide, depthWrite: false,
    });
    this.edgeMat = new THREE.LineBasicMaterial({ color: PC_EDGE.clone(), transparent: true, opacity: 0.45 });
    const t = BOX.t, w = BOX.w, h = BOX.h, d = BOX.d;
    const cy = BOX.base + h / 2;
    const panels = [
      [[t, h, d - 2 * t], [-w / 2 + t / 2, cy, 0]],          // esquerda (frestas)
      [[t, h, d - 2 * t], [w / 2 - t / 2, cy, 0]],           // direita (cooler)
      [[w, h, t], [0, cy, -d / 2 + t / 2]],                  // fundo
      [[w, t, d - 2 * t], [0, TOP - t / 2, 0]],              // tampa
    ];
    for (const [[sx, sy, sz], [x, y, z]] of panels) {
      const geo = new THREE.BoxGeometry(sx, sy, sz);
      const m = new THREE.Mesh(geo, this.pcMat);
      m.position.set(x, y, z);
      m.renderOrder = 2;
      this.scene.add(m);
      const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo), this.edgeMat);
      e.position.copy(m.position);
      e.renderOrder = 3;
      this.scene.add(e);
    }
    // porta: painel da frente, levemente afastado, com dobradicas e puxador
    const door = new THREE.Group();
    door.position.set(-w / 2, cy, d / 2 - t / 2);
    this.scene.add(door);
    const dgeo = new THREE.BoxGeometry(w - 0.1, h - 0.1, t);
    const dm = new THREE.Mesh(dgeo, this.pcMat);
    dm.position.x = w / 2;
    dm.renderOrder = 2;
    door.add(dm);
    const de = new THREE.LineSegments(new THREE.EdgesGeometry(dgeo), this.edgeMat);
    de.position.copy(dm.position);
    de.renderOrder = 3;
    door.add(de);
    const steel = new THREE.MeshStandardMaterial({ color: 0xc3c9cf, metalness: 1, roughness: 0.3 });
    [-7, 7].forEach((yy) => {
      const hinge = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 3, 16), steel);
      hinge.position.set(-0.1, yy, t / 2 + 0.3);
      door.add(hinge);
    });
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 6, 12), steel);
    handle.position.set(w - 2, 0, t / 2 + 0.6);
    door.add(handle);
    [-3, 3].forEach((yy) => {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.6), steel);
      leg.position.set(w - 2, yy, t / 2 + 0.3);
      door.add(leg);
    });

    // cantoneiras de aluminio 25 x 25 por fora nas 8 arestas fixas (a frente fica livre para a porta)
    const alu = new THREE.MeshStandardMaterial({ color: 0xb7bec5, metalness: 0.9, roughness: 0.35, envMapIntensity: 0.8 });
    const a = 0.65, x0 = w / 2 + 0.05, z0 = d / 2 + 0.05, y0 = BOX.base, y1 = TOP;
    const beam = (len, axis, x, y, z) => {
      const geo = axis === 'x' ? new THREE.BoxGeometry(len, a, a) : axis === 'y' ? new THREE.BoxGeometry(a, len, a) : new THREE.BoxGeometry(a, a, len);
      const m = new THREE.Mesh(geo, alu);
      m.position.set(x, y, z);
      this.scene.add(m);
    };
    for (const sx of [-1, 1]) beam(h - 2 * a, 'y', sx * (x0 - a / 2), y0 + h / 2, -(z0 - a / 2));
    for (const yy of [y0 + a / 2, y1 - a / 2]) {
      beam(w, 'x', 0, yy, -(z0 - a / 2));
      for (const sx of [-1, 1]) beam(d - 2 * BOX.t, 'z', sx * (x0 - a / 2), yy, 0);
    }
  }

  // Fabrica de ventoinha: geometria de 40 mm voltada para +x, escalada.
  #makeFan(scale, sticker = 0x9aa3ab) {
    const g = new THREE.Group();
    const frameShape = new THREE.Shape();
    frameShape.moveTo(-2, -2); frameShape.lineTo(2, -2); frameShape.lineTo(2, 2); frameShape.lineTo(-2, 2); frameShape.lineTo(-2, -2);
    const hole = new THREE.Path();
    hole.absarc(0, 0, 1.78, 0, Math.PI * 2, true);
    frameShape.holes.push(hole);
    const frameGeo = new THREE.ExtrudeGeometry(frameShape, { depth: 1.0, bevelEnabled: false, curveSegments: 40 });
    frameGeo.translate(0, 0, -0.5);
    const plastic = new THREE.MeshStandardMaterial({ color: 0x16191d, roughness: 0.55, envMapIntensity: 0.5 });
    const frame = new THREE.Mesh(frameGeo, plastic);
    frame.rotation.y = Math.PI / 2;
    g.add(frame);
    const rotor = new THREE.Group();
    g.add(rotor);
    const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 0.7, 28), plastic);
    hub.rotation.z = Math.PI / 2;
    rotor.add(hub);
    const st = new THREE.Mesh(new THREE.CircleGeometry(0.5, 28),
      new THREE.MeshStandardMaterial({ color: sticker, metalness: 0.6, roughness: 0.35 }));
    st.rotation.y = Math.PI / 2;
    st.position.x = 0.36;
    rotor.add(st);
    const bladeMat = new THREE.MeshStandardMaterial({ color: 0x23282e, roughness: 0.5, envMapIntensity: 0.5, side: THREE.DoubleSide });
    for (let i = 0; i < 7; i++) {
      const arm = new THREE.Group();
      arm.rotation.x = (i / 7) * Math.PI * 2;
      const blade = new THREE.Mesh(new THREE.BoxGeometry(0.05, 1.08, 0.62), bladeMat);
      blade.position.y = 1.15;
      blade.rotation.y = 0.5;
      arm.add(blade);
      rotor.add(arm);
    }
    const blurMat = new THREE.MeshBasicMaterial({ color: 0x2a3038, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide });
    const blur = new THREE.Mesh(new THREE.RingGeometry(0.62, 1.74, 40), blurMat);
    blur.rotation.y = Math.PI / 2;
    g.add(blur);
    const streakMat = new THREE.MeshBasicMaterial({ color: 0x9aa6c8, transparent: true, opacity: 0, depthWrite: false,
      side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
    for (const r of [1.05, 1.4]) {
      const ring = new THREE.Mesh(new THREE.RingGeometry(r, r + 0.035, 48), streakMat);
      ring.rotation.y = Math.PI / 2;
      ring.position.x = 0.38;
      g.add(ring);
    }
    g.scale.setScalar(scale);
    return { g, rotor, blurMat, streakMat };
  }

  #fans() {
    // exaustao 80 mm na parede +x
    const ex = this.#makeFan(FAN_SCALE);
    ex.g.position.set(BOX.w / 2 + 0.05, FAN_Y, 0);
    this.scene.add(ex.g);
    this.fanRotor = ex.rotor; this.fanBlurMat = ex.blurMat; this.fanStreakMat = ex.streakMat;

    // circulacao M2 60 mm no fundo, embaixo da prateleira, soprando para +z
    const ci = this.#makeFan(CIRC.scale, 0x5d8fd8);
    ci.g.rotation.y = -Math.PI / 2;
    ci.g.position.set(0, CIRC.y, CIRC.z);
    this.scene.add(ci.g);
    this.circRotor = ci.rotor; this.circBlur = ci.blurMat;

    // etiqueta flutuante do cooler: PWM e rotacao estimada
    this.fanLabelCanvas = document.createElement('canvas');
    this.fanLabelCanvas.width = 720; this.fanLabelCanvas.height = 128;
    this.fanLabelTex = new THREE.CanvasTexture(this.fanLabelCanvas);
    this.fanLabelTex.colorSpace = THREE.SRGBColorSpace;
    this.fanLabelMat = new THREE.SpriteMaterial({ map: this.fanLabelTex, transparent: true, opacity: 0, depthWrite: false, toneMapped: false });
    this.fanLabel = new THREE.Sprite(this.fanLabelMat);
    this.fanLabel.scale.set(13, 2.3, 1);
    this.fanLabel.position.set(BOX.w / 2 + 6, FAN_Y + 7, 0);
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

  // Frestas de entrada na parede -x: 2 fileiras de 9 furos de 8 mm (PIDL-MEC-001).
  #vents() {
    const mat = new THREE.MeshBasicMaterial({ color: 0x06080a });
    const geo = new THREE.CircleGeometry(0.4, 20);
    for (const yy of [3.5, 5.0]) {
      for (let i = 0; i < 9; i++) {
        const hole = new THREE.Mesh(geo, mat);
        hole.rotation.y = -Math.PI / 2;
        hole.position.set(-BOX.w / 2 - 0.02, FLOOR + yy, -7.2 + i * 1.8);
        this.scene.add(hole);
      }
    }
  }

  // Isolante, manta de silicone de 80 W e dois dissipadores aletados.
  #heater() {
    const g = new THREE.Group();
    this.scene.add(g);
    const insul = new THREE.Mesh(new THREE.BoxGeometry(22.6, 0.3, 22.6),
      new THREE.MeshStandardMaterial({ color: 0xd9d4c7, roughness: 0.95, envMapIntensity: 0.3 }));
    insul.position.y = FLOOR + 0.15;
    g.add(insul);
    this.padMat = new THREE.MeshStandardMaterial({ color: 0xc2441c, roughness: 0.7, emissive: new THREE.Color(0xff4a12), emissiveIntensity: 0 });
    const pad = new THREE.Mesh(new THREE.BoxGeometry(20.6, 0.15, 20.6), this.padMat);
    pad.position.y = FLOOR + 0.375;
    g.add(pad);
    const wireMat = new THREE.MeshStandardMaterial({ color: 0xb3261e, roughness: 0.5 });
    [-0.6, 0.6].forEach((dx) => {
      const w = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 2.0, 8), wireMat);
      w.rotation.x = Math.PI / 2;
      w.position.set(7.5 + dx, FLOOR + 0.4, -11.0);
      g.add(w);
    });
    this.sinkMat = new THREE.MeshStandardMaterial({ color: 0xb9c1c8, metalness: 0.9, roughness: 0.38, envMapIntensity: 0.9,
      emissive: new THREE.Color(0xff5a1f), emissiveIntensity: 0 });
    for (const zc of [-5.05, 5.05]) {
      const sb = new THREE.Mesh(new THREE.BoxGeometry(SINK.w, SINK.base, 9.9), this.sinkMat);
      sb.position.set(0, SINK.y + SINK.base / 2, zc);
      g.add(sb);
      const pitch = SINK.w / SINK.fins;
      for (let i = 0; i < SINK.fins; i++) {
        const fin = new THREE.Mesh(new THREE.BoxGeometry(0.22, SINK.fin, 9.9), this.sinkMat);
        fin.position.set(-SINK.w / 2 + pitch * (i + 0.5), SINK.y + SINK.base + SINK.fin / 2, zc);
        g.add(fin);
      }
    }
    // TH2 (KSD301) na lateral do dissipador
    const can = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 0.5, 24),
      new THREE.MeshStandardMaterial({ color: 0xcfd5da, metalness: 1, roughness: 0.25 }));
    can.rotation.z = Math.PI / 2;
    can.position.set(SINK.w / 2 + 0.4, SINK.y + 1.2, 6);
    g.add(can);
  }

  // Prateleira de aluminio perfurado (furos de 5 mm, ~40 % aberta) sobre
  // quatro espacadores, 7 cm acima do piso. Com amostras em cima.
  #shelf() {
    const holes = new THREE.CanvasTexture(perforationCanvas());
    holes.wrapS = holes.wrapT = THREE.RepeatWrapping;
    holes.repeat.set(16, 16);
    const mat = new THREE.MeshStandardMaterial({ color: 0xc4cad0, metalness: 0.85, roughness: 0.4, envMapIntensity: 0.9,
      alphaMap: holes, alphaTest: 0.5, side: THREE.DoubleSide });
    this.shelfMat = mat;
    const top = new THREE.Mesh(new THREE.PlaneGeometry(IN - 0.6, IN - 0.6), mat);
    top.rotation.x = -Math.PI / 2;
    top.position.y = SHELF_Y;
    this.scene.add(top);
    const rim = new THREE.MeshStandardMaterial({ color: 0xc4cad0, metalness: 0.85, roughness: 0.4 });
    const L = IN - 0.6;
    [[L, 0.4, 0.15, 0, L / 2], [L, 0.4, 0.15, 0, -L / 2], [0.15, 0.4, L, L / 2, 0], [0.15, 0.4, L, -L / 2, 0]].forEach(([sx, sy, sz, x, z]) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), rim);
      m.position.set(x, SHELF_Y - 0.2, z);
      this.scene.add(m);
    });
    const post = new THREE.MeshStandardMaterial({ color: 0xd4c27a, metalness: 0.9, roughness: 0.3 });
    for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
      const p = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, SHELF_Y - FLOOR, 12), post);
      p.position.set(sx * (L / 2 - 0.8), FLOOR + (SHELF_Y - FLOOR) / 2, sz * (L / 2 - 0.8));
      this.scene.add(p);
    }
    // amostras: duas placas de Petri e um vaso com muda
    const glass = new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.25, roughness: 0.05, clearcoat: 1, depthWrite: false });
    [[-6, 4], [-2.2, 6.5]].forEach(([x, z]) => {
      const dish = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 0.9, 32, 1, true), glass);
      dish.position.set(x, SHELF_Y + 0.45, z);
      this.scene.add(dish);
      const agar = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.5, 0.25, 32),
        new THREE.MeshStandardMaterial({ color: 0xe8c86a, roughness: 0.6, transparent: true, opacity: 0.85 }));
      agar.position.set(x, SHELF_Y + 0.15, z);
      this.scene.add(agar);
    });
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 1.7, 3.6, 24),
      new THREE.MeshStandardMaterial({ color: 0xb4532a, roughness: 0.85 }));
    pot.position.set(4.5, SHELF_Y + 1.8, -4.5);
    this.scene.add(pot);
    const soil = new THREE.Mesh(new THREE.CylinderGeometry(2.05, 2.05, 0.2, 24),
      new THREE.MeshStandardMaterial({ color: 0x3b2a1e, roughness: 1 }));
    soil.position.set(4.5, SHELF_Y + 3.45, -4.5);
    this.scene.add(soil);
    const leaf = new THREE.MeshStandardMaterial({ color: 0x4f9a3a, roughness: 0.6, side: THREE.DoubleSide });
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 2.6, 8), leaf);
    stem.position.set(4.5, SHELF_Y + 4.8, -4.5);
    this.scene.add(stem);
    [[0.9, 0.5], [-0.9, -0.4], [0.2, 1.0]].forEach(([dx, rot], i) => {
      const l = new THREE.Mesh(new THREE.SphereGeometry(0.8, 12, 8), leaf);
      l.scale.set(1, 0.25, 0.55);
      l.position.set(4.5 + dx, SHELF_Y + 5.2 + i * 0.5, -4.5);
      l.rotation.z = rot;
      this.scene.add(l);
    });
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

  // Jumpers: da protoboard ate a lateral da base (gates e sensor) e ate o display.
  #wires() {
    const local = (x, z) => new THREE.Vector3(x, 0.9, z)
      .applyAxisAngle(new THREE.Vector3(0, 1, 0), ESP_ROT).add(ESP_POS);
    const front = BASE_D / 2 + 0.02;
    this.dispGroup.updateMatrixWorld(true);
    const pin = (x) => this.dispGroup.localToWorld(new THREE.Vector3(x, -1.0, 0.36));
    const runs = [
      [0xff8a1c, [-1.8, -2.3], new THREE.Vector3(9, 0.8, front)],      // PWM_GATE  (lampadas)
      [0xd8342a, [-1.0, -2.3], new THREE.Vector3(10, 0.8, front)],     // HEAT_GATE (manta)
      [0x3b6fe0, [-0.2, -2.3], new THREE.Vector3(11, 0.8, front)],     // FAN_GATE  (cooler)
      [0x2fb36a, [0.6, -2.3], new THREE.Vector3(12, 0.8, front)],      // TEMP_S    (LM35)
      [0xe23b3b, [-2.6, 2.3], pin(0.45)],                               // 3V3 display
      [0x222428, [-1.8, 2.3], pin(0.15)],                               // GND
      [0xf2c230, [-1.0, 2.3], pin(-0.15)],                              // CLK
      [0x34c6d8, [-0.2, 2.3], pin(-0.45)],                              // DIO
    ];
    for (const [color, [lx, lz], end] of runs) {
      const a = local(lx, lz);
      const p1 = a.clone().add(new THREE.Vector3(0, 0.6, 0));
      const p2 = a.clone().lerp(end, 0.25); p2.y = 0.9;
      const p3 = a.clone().lerp(end, 0.6); p3.y = 0.12;
      const p4 = a.clone().lerp(end, 0.88); p4.y = Math.max(0.12, end.y * 0.5);
      const curve = new THREE.CatmullRomCurve3([a, p1, p2, p3, p4, end]);
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 60, 0.07, 6, false),
        new THREE.MeshStandardMaterial({ color, roughness: 0.45, envMapIntensity: 0.4 }));
      this.scene.add(tube);
    }
  }

  // Ar em cinco grupos, num unico Points aditivo (cor preta = invisivel):
  //   out    - jato quente saindo do cooler
  //   intake - ar frio entrando pelas frestas
  //   path   - caminho interno com o cooler ligado: frestas -> aletas ->
  //            furos da prateleira -> cooler, esquentando no caminho
  //   circ   - ventoinha M2 soprando pelas aletas, embaixo da prateleira
  //   conv   - ar quente subindo pelos furos da prateleira
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
          x0: (Math.random() - 0.5) * (IN - 3), z0: (Math.random() - 0.5) * (IN - 3), h: Math.random(),
          w: Math.random() * Math.PI * 2,
        });
      }
    };
    add('out', AIR.out); add('intake', AIR.intake); add('path', AIR.path); add('circ', AIR.circ); add('conv', AIR.conv);
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.75, map: radialTexture('rgba(255,255,255,1)', 'rgba(255,255,255,0)'), vertexColors: true,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true,
    });
    this.air = new THREE.Points(geo, mat);
    this.air.frustumCulled = false;
    this.scene.add(this.air);
  }

  #updateAir(dt, f, heatLvl) {
    const pos = this.air.geometry.attributes.position.array;
    const col = this.air.geometry.attributes.color.array;
    const warm = Math.max(0, Math.min(1, (this.target.T - this.target.amb) / 40));
    const still = this.reduceMotion;
    const cold = [0.28, 0.5, 0.95], hot = [1.0, 0.55, 0.22];
    const mix = (k, m) => [cold[0] + (hot[0] - cold[0]) * m, cold[1] + (hot[1] - cold[1]) * m, cold[2] + (hot[2] - cold[2]) * m].map((c) => c * k);
    const ventX = -IN / 2 + 0.5, fanX = IN / 2 - 1.5;
    const ceil = TOP - BOX.t - 3;
    const smooth = (a, b, x) => { const u = Math.max(0, Math.min(1, (x - a) / (b - a))); return u * u * (3 - 2 * u); };
    for (let i = 0; i < AIR_N; i++) {
      const s = this.airSeed[i];
      let x, y, z, c;
      if (s.kind === 'out') {
        if (!still) s.p += dt * s.v * (0.2 + 1.2 * f);
        if (s.p > 1) s.p -= 1;
        x = BOX.w / 2 + 1.5 + s.p * 20;
        y = FAN_Y + s.y * 3.2 * (1 + s.p * 0.9) + s.p * 2.4;
        z = s.z * 3.2 * (1 + s.p * 0.9);
        c = mix((1 - s.p) * f * 1.1, 0.45 + 0.55 * warm);
      } else if (s.kind === 'intake') {
        if (!still) s.p += dt * s.v * (0.2 + 0.9 * f);
        if (s.p > 1) s.p -= 1;
        x = -BOX.w / 2 - 14 + s.p * 14;
        y = FLOOR + 3.2 + s.y * 2.0;
        z = s.z * 6.5;
        c = mix(Math.sin(s.p * Math.PI) * f * 0.9, 0);
      } else if (s.kind === 'path') {
        if (!still) s.p += dt * s.v * (0.1 + 0.7 * f);
        if (s.p > 1) s.p -= 1;
        const p = s.p;
        x = ventX + (fanX - ventX) * smooth(0, 1, p);
        y = FLOOR + 2 + s.h * 2.4 + (FAN_Y - FLOOR - 3) * smooth(0.3, 0.95, p) + Math.sin(p * 9 + s.w) * 0.4;
        z = s.z * 9 * (1 - 0.65 * smooth(0.4, 1, p));
        c = mix(Math.sin(Math.min(1, p * 1.12) * Math.PI) * f * 0.85, smooth(0.15, 0.7, p));
      } else if (s.kind === 'circ') {
        // M2: do fundo para a frente, entre as aletas
        if (!still) s.p += dt * s.v * 0.55;
        if (s.p > 1) s.p -= 1;
        x = s.x0 * 0.85;
        y = SINK.y + 0.8 + s.h * (SHELF_Y - SINK.y - 1.6);
        z = CIRC.z + 2 + s.p * (IN - 4);
        const k = Math.sin(s.p * Math.PI) * (0.18 + 0.8 * heatLvl);
        c = mix(k, 0.25 + 0.75 * heatLvl);
      } else {
        // conveccao: sobe pelos furos da prateleira; com o cooler, e' puxada para ele
        if (!still) s.p += dt * s.v * (0.16 + 0.22 * heatLvl);
        if (s.p > 1) { s.p -= 1; s.x0 = (Math.random() - 0.5) * (IN - 3); s.z0 = (Math.random() - 0.5) * (IN - 3); }
        const p = s.p;
        y = SHELF_Y + 0.3 + p * (ceil - SHELF_Y);
        x = s.x0 + Math.sin(s.w + p * 6) * 0.6 + (fanX - s.x0) * f * p * p;
        z = s.z0 * (1 - 0.6 * p * f) + Math.cos(s.w + p * 5) * 0.6;
        const k = Math.sin(Math.min(1, p * 1.2) * Math.PI) * heatLvl * (1 - 0.6 * f);
        c = [1.25 * k, 0.5 * k, 0.18 * k];
      }
      pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
      col[i * 3] = c[0]; col[i * 3 + 1] = c[1]; col[i * 3 + 2] = c[2];
    }
    this.air.geometry.attributes.position.needsUpdate = true;
    this.air.geometry.attributes.color.needsUpdate = true;
  }

  #displayModule() {
    const g = new THREE.Group();
    g.position.set(-3.5, 1.35, BASE_D / 2 + 1.4);
    g.rotation.x = -0.28;
    this.scene.add(g);
    this.dispGroup = g;

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

    const light = new THREE.PointLight(COLD.clone(), 0, 0, 2);   // decaimento fisico (unidade = cm)
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

  // Afasta a camera o bastante para a caixa e a protoboard caberem inteiras,
  // tanto na vertical quanto na horizontal. Mantem a direcao atual.
  #frameBox() {
    const radius = 27;
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * this.camera.aspect);
    const dist = radius / Math.sin(Math.min(vfov, hfov) / 2);
    const portrait = this.camera.aspect < 0.9;
    this.controls.target.set(3, FLOOR + BOX.h * (portrait ? 0.3 : 0.38), 5);
    const dir = this.camera.position.clone().sub(this.controls.target).normalize();
    this.camera.position.copy(this.controls.target).addScaledVector(dir, dist);
    this.controls.maxDistance = Math.max(160, dist * 1.6);
    this.framed = true;
    this.lastAspect = this.camera.aspect;
  }

  #frame() {
    if (!this.visible || this.hidden) return;
    const dt = Math.min(this.clock.getDelta(), 0.1);

    const t = this.target;
    const goal = t.fault ? 0 : Math.max(0, Math.min(1, t.ue));
    this.shown.b += (goal - this.shown.b) * (1 - Math.exp(-dt / 0.25));      // inercia do filamento
    const heatGoal = Math.max(0, Math.min(1, (t.T - t.amb) / 45));
    this.shown.heat += (heatGoal - this.shown.heat) * (1 - Math.exp(-dt / 0.8));

    const p = this.shown.b;
    const lum = Math.pow(p, 1.7);
    const color = COLD.clone().lerp(HOT, Math.pow(p, 0.7));
    for (const L of this.lamps) {
      L.light.color.copy(color);
      L.light.intensity = 230 * lum;
      L.glassMat.emissive.copy(color);
      L.glassMat.emissiveIntensity = 0.1 + 1.6 * lum;
      L.filMat.color.copy(p < 0.03 ? new THREE.Color(0x3a2a22) : color.clone().multiplyScalar(1 + 5 * lum));
    }
    this.heatMat.opacity = 0.07 * this.shown.heat;
    this.edgeMat.color.copy(PC_EDGE).lerp(TUNGSTEN, Math.min(1, lum * 0.8));
    this.edgeMat.opacity = 0.4 + 0.4 * lum;
    this.bloom.strength = 0.25 + 0.6 * lum;

    // cooler: inercia ~0,8 s; giro proporcional ao PWM, limitado na tela
    const fanGoal = Math.max(0, Math.min(1, t.fan || 0));
    this.shown.fan += (fanGoal - this.shown.fan) * (1 - Math.exp(-dt / 0.8));
    const f = this.shown.fan;
    if (!this.reduceMotion && f > 0.005) this.fanAngle += (0.6 + (FAN_VISUAL_MAX - 0.6) * f) * dt;
    this.fanRotor.rotation.x = this.fanAngle;
    this.fanBlurMat.opacity = Math.min(0.6, f * 0.75);
    this.fanStreakMat.opacity = 0.5 * f;
    this.fanLabelMat.opacity += ((fanGoal > 0.01 ? 1 : 0) - this.fanLabelMat.opacity) * (1 - Math.exp(-dt / 0.3));
    const labelKey = Math.round(fanGoal * 100);
    if (labelKey !== this.fanLabelKey && fanGoal > 0.01) { this.fanLabelKey = labelKey; this.#drawFanLabel(fanGoal); }

    // M2 sempre ligada, rotacao constante
    if (!this.reduceMotion) this.circAngle += 6 * dt;
    this.circRotor.rotation.x = this.circAngle;
    this.circBlur.opacity = 0.45;

    // manta e dissipador
    const padGoal = t.fault ? 0 : Math.max(0, Math.min(1, t.heat || 0));
    this.shown.pad += (padGoal - this.shown.pad) * (1 - Math.exp(-dt / 0.6));
    const sinkGoal = t.sink != null ? t.sink : t.T + 25 * padGoal;
    this.shown.sink += (sinkGoal - this.shown.sink) * (1 - Math.exp(-dt / 0.8));
    const sinkHot = Math.max(0, Math.min(1, (this.shown.sink - 30) / 80));
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

// Furo de chapa perfurada: um furo redondo por ladrilho (alpha: branco = chapa).
function perforationCanvas() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  g.fillStyle = '#fff';
  g.fillRect(0, 0, 64, 64);
  g.fillStyle = '#000';
  for (const [x, y] of [[16, 16], [48, 16], [32, 48], [0, 48], [64, 48]]) {
    g.beginPath(); g.arc(x, y, 10.5, 0, Math.PI * 2); g.fill();
  }
  return c;
}
