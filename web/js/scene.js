/*
 * A camara em 3D.
 *
 * Unidade = 1 cm. Caixa de 10 x 8 x 10 cm sobre uma base de acrilico preto,
 * chapa de aluminio presa no teto e tres W5W penduradas nela, como na
 * proposta. O brilho e a cor de cada lampada seguem a potencia real
 * entregue (duty corrigido pela tensao), com a inercia de um filamento.
 *
 * Cooler de 40 mm na parede direita, perto do teto (onde o ar quente
 * fica), com frestas de entrada embaixo na parede oposta. Gira e mostra o
 * fluxo de ar na proporcao do PWM. Na frente da base, o modulo TM1637
 * mostra a mesma leitura do display do Wokwi.
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
const AIR_N = 140;

export class ChamberScene {
  constructor(host) {
    this.host = host;
    this.target = { ue: 0, T: 25, amb: 25, fault: false, fan: 0, display: null, displayKey: '' };
    this.shown = { b: 0, heat: 0, fan: 0 };
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
    this.#air();
    this.#displayModule();
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

  // Fluxo de ar: particulas saindo pelo cooler e entrando pelas frestas.
  #air() {
    const pos = new Float32Array(AIR_N * 3);
    const col = new Float32Array(AIR_N * 3);
    this.airSeed = [];
    for (let i = 0; i < AIR_N; i++) {
      const out = i < AIR_N * 0.6;            // 60 % saindo, 40 % entrando
      const r = Math.sqrt(Math.random()) * (out ? 1.5 : 2.0);
      const a = Math.random() * Math.PI * 2;
      this.airSeed.push({ out, p: Math.random(), y: r * Math.sin(a), z: r * Math.cos(a), v: 0.7 + Math.random() * 0.6 });
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.16, vertexColors: true, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending, sizeAttenuation: true,
    });
    this.air = new THREE.Points(geo, mat);
    this.scene.add(this.air);
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

  #updateAir(dt, f) {
    const pos = this.air.geometry.attributes.position.array;
    const col = this.air.geometry.attributes.color.array;
    const warm = Math.max(0, Math.min(1, (this.target.T - this.target.amb) / 30));
    for (let i = 0; i < AIR_N; i++) {
      const s = this.airSeed[i];
      if (!this.reduceMotion) s.p += dt * s.v * (0.15 + 1.1 * f);
      if (s.p > 1) s.p -= 1;
      let x, y, z, k;
      if (s.out) {                       // sai pelo cooler e se espalha
        x = BOX.w / 2 + 0.6 + s.p * 7.5;
        y = FAN_Y + s.y * (1 + s.p * 0.9) + s.p * 0.8;
        z = s.z * (1 + s.p * 0.9);
        k = (1 - s.p) * f;
        col[i * 3] = (0.55 + 0.45 * warm) * k;     // ar quente saindo
        col[i * 3 + 1] = (0.5 + 0.15 * warm) * k;
        col[i * 3 + 2] = (0.55 - 0.3 * warm) * k;
      } else {                           // entra pelas frestas
        x = -BOX.w / 2 - 5.5 + s.p * 5.2;
        y = BOX.base + 1.6 + s.y * 0.45;
        z = s.z;
        k = Math.sin(s.p * Math.PI) * f * 0.8;
        col[i * 3] = 0.38 * k; col[i * 3 + 1] = 0.5 * k; col[i * 3 + 2] = 0.75 * k;
      }
      pos[i * 3] = x; pos[i * 3 + 1] = y; pos[i * 3 + 2] = z;
    }
    this.air.geometry.attributes.position.needsUpdate = true;
    this.air.geometry.attributes.color.needsUpdate = true;
    this.air.visible = f > 0.01;
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
    const radius = 9.2;
    const vfov = THREE.MathUtils.degToRad(this.camera.fov);
    const hfov = 2 * Math.atan(Math.tan(vfov / 2) * this.camera.aspect);
    const dist = radius / Math.sin(Math.min(vfov, hfov) / 2);
    // em retrato, sobe o alvo para a caixa ficar acima da leitura de temperatura
    const portrait = this.camera.aspect < 0.9;
    this.controls.target.set(0, BOX.base + BOX.h * (portrait ? 0.3 : 0.4), 0);
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
    if (!this.reduceMotion) this.fanAngle += f * 26 * dt;
    this.fanRotor.rotation.x = this.fanAngle;
    this.fanBlurMat.opacity = Math.min(0.55, f * 0.7);
    this.#updateAir(dt, f);

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
