// Visor 3D de autos (three.js) con modelos reales en formato glTF/GLB.
//
// Los modelos van en static/models/. Por defecto se busca <tipo>.glb
// (sedan.glb, suv.glb, ...). En static/models/modelos.json se puede indicar,
// por tipo de carrocería:
//   archivo   nombre del .glb (varios tipos pueden compartir un mismo archivo)
//   nodo      nombre del objeto dentro del archivo, si trae varios autos
//   pintura   nombres de los materiales de la carrocería a pintar
//   mascara   true si la textura de la pintura trae en el canal alfa qué parte
//             es pintura (ver tools/preparar_modelos.py)
//   rotacion  giro extra en grados, si el modelo viene mal orientado
//   largo     largo en metros al que se escala (si no, uno típico por tipo)
//   credito / url   autor y enlace (se muestran en el pie de página)
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

const BASE = new URL("models/", import.meta.url);
const LARGOS = { moto: 2.1, hatchback: 4.0, sedan: 4.6, rural: 4.7, coupe: 4.5, suv: 4.6, pickup: 5.3, utilitario: 4.6 };
const NOMBRES = {
  hatchback: "Hatchback", sedan: "Sedán", rural: "Rural / Familiar", coupe: "Coupé",
  suv: "SUV / Todoterreno", pickup: "Pick-up", utilitario: "Utilitario / Furgón", moto: "Moto",
};
const PAINT_RE = /paint|body|carpaint|exterior|coat|lack|karosserie|carroceria|shell|color|colour/i;
const NOT_PAINT_RE = /glass|window|windshield|tire|tyre|rubber|chrome|light|lamp|interior|rim|wheel|plastic|mirror|plate|logo|grill|seat|black|trim|brake|caliper|disc|carbon|engine|under|shadow/i;

const loader = new GLTFLoader();
loader.setDRACOLoader(new DRACOLoader().setDecoderPath(
  "/static/vendor/three/examples/jsm/libs/draco/gltf/"));

let configPromise;
const getConfig = () => (configPromise ??= fetch(new URL("modelos.json", BASE))
  .then((r) => (r.ok ? r.json() : {})).catch(() => ({})));

// Un archivo se descarga una sola vez aunque haya varias tarjetas.
const archivos = {};
let modeloMoto;
// Moto genérica creada con geometría propia: no requiere descargas ni modelos externos.
function crearMoto() {
  const grupo = new THREE.Group();
  const material = (name, color, metalness = 0) => {
    const m = new THREE.MeshStandardMaterial({ color, metalness, roughness: metalness ? 0.32 : 0.65 });
    m.name = name;
    return m;
  };
  const pintura = material("moto_paint", 0xffffff, 0.35);
  const metal = material("engine_metal", 0xaab1ba, 0.8);
  const oscuro = material("black_frame", 0x24272b, 0.4);
  const goma = material("rubber_tire", 0x111214);
  const asiento = material("seat", 0x202126);
  const agregar = (geo, mat, x, y, z = 0) => {
    const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); grupo.add(m); return m;
  };
  const barra = (a, b, radio = 0.025, mat = metal) => {
    const desde = new THREE.Vector3(...a), hasta = new THREE.Vector3(...b);
    const dir = hasta.clone().sub(desde);
    const m = agregar(new THREE.CylinderGeometry(radio, radio, dir.length(), 10), mat, 0, 0);
    m.position.copy(desde.add(hasta).multiplyScalar(0.5));
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
  };
  for (const x of [-0.68, 0.68]) {
    agregar(new THREE.TorusGeometry(0.27, 0.065, 12, 32), goma, x, 0.335);
    agregar(new THREE.TorusGeometry(0.225, 0.02, 8, 28), metal, x, 0.335);
    for (let i = 0; i < 8; i++) {
      const ang = i * Math.PI / 4;
      barra([x, 0.335, 0], [x + Math.cos(ang) * 0.22, 0.335 + Math.sin(ang) * 0.22, 0], 0.009);
    }
    const eje = agregar(new THREE.CylinderGeometry(0.07, 0.07, 0.18, 16), metal, x, 0.335);
    eje.rotation.x = Math.PI / 2;
  }
  barra([-0.68, 0.335, 0], [-0.18, 0.52, 0], 0.035, oscuro);
  barra([-0.18, 0.52, 0], [0.32, 0.95, 0], 0.035, oscuro);
  barra([0.32, 0.95, 0], [-0.52, 0.85, 0], 0.035, oscuro);
  barra([-0.52, 0.85, 0], [-0.18, 0.52, 0], 0.035, oscuro);
  for (const z of [-0.11, 0.11]) {
    barra([0.68, 0.335, z], [0.38, 1.12, z], 0.028);
    barra([-0.68, 0.335, z], [-0.47, 0.83, z], 0.025);
  }
  agregar(new THREE.BoxGeometry(0.37, 0.32, 0.32), metal, -0.02, 0.57);
  for (let y = 0.49; y < 0.7; y += 0.04) agregar(new THREE.BoxGeometry(0.4, 0.018, 0.34), oscuro, -0.02, y);
  const tanque = agregar(new THREE.SphereGeometry(1, 24, 16), pintura, 0.08, 0.96);
  tanque.scale.set(0.33, 0.19, 0.2);
  agregar(new THREE.BoxGeometry(0.62, 0.11, 0.3), asiento, -0.42, 0.98);
  agregar(new THREE.BoxGeometry(0.32, 0.09, 0.27), pintura, -0.64, 0.88);
  barra([0.38, 1.12, 0], [0.35, 1.24, 0]);
  barra([0.35, 1.24, -0.35], [0.35, 1.24, 0.35], 0.025, oscuro);
  agregar(new THREE.SphereGeometry(0.1, 16, 12), material("headlight", 0xfff1c4), 0.51, 1.06);
  barra([-0.6, 0.28, 0.22], [0.13, 0.32, 0.22], 0.045);
  agregar(new THREE.BoxGeometry(0.06, 0.07, 0.18), material("taillight", 0xd52430), -0.82, 0.87);
  return grupo;
}
async function loadModel(type) {
  if (type === "moto") return { src: modeloMoto ??= crearMoto(), cfg: { pintura: ["moto_paint"] } };
  const cfg = (await getConfig())[type] || {};
  const file = cfg.archivo || `${type}.glb`;
  archivos[file] ??= loader.loadAsync(new URL(file, BASE).href);
  const gltf = await archivos[file];
  let src = gltf.scene;
  if (cfg.nodo) {
    // El cargador reemplaza los espacios de los nombres por "_".
    const body = gltf.scene.getObjectByName(cfg.nodo) ||
                 gltf.scene.getObjectByName(THREE.PropertyBinding.sanitizeNodeName(cfg.nodo));
    if (!body) throw new Error(`No existe el objeto "${cfg.nodo}" en ${file}`);
    src = conRuedas(gltf.scene, body);
  }
  return { src, cfg };
}

// Arma un grupo con la carrocería y los objetos sueltos que caen dentro de
// ella (en el pack las ruedas no cuelgan de la carrocería sino del mismo nivel).
function conRuedas(scene, body) {
  scene.updateMatrixWorld(true);
  const caja = new THREE.Box3().setFromObject(body);
  const grupo = new THREE.Group();
  const agregar = (o) => {
    const c = o.clone(true);
    o.matrixWorld.decompose(c.position, c.quaternion, c.scale);
    grupo.add(c);
  };
  agregar(body);
  const centro = new THREE.Vector3();
  for (const o of body.parent.children) {
    if (o === body || /body/i.test(o.name)) continue;
    new THREE.Box3().setFromObject(o).getCenter(centro);
    if (centro.x >= caja.min.x && centro.x <= caja.max.x &&
        centro.y >= caja.min.y && centro.y <= caja.max.y &&
        centro.z >= caja.min.z && centro.z <= caja.max.z) agregar(o);
  }
  return grupo;
}

// Pinta solo donde el alfa de la textura marca pintura; el resto queda como está.
function pintarConMascara(m, color) {
  const uniform = { value: new THREE.Color(color) };
  m.color.set(0xffffff);
  m.userData.uPaint = uniform;
  m.onBeforeCompile = (shader) => {
    shader.uniforms.uPaint = uniform;
    shader.fragmentShader = "uniform vec3 uPaint;\n" + shader.fragmentShader.replace(
      "#include <map_fragment>",
      `#include <map_fragment>
      #ifdef USE_MAP
        diffuseColor.rgb = mix(diffuseColor.rgb, diffuseColor.rgb * uPaint, sampledDiffuseColor.a);
        diffuseColor.a = opacity;
      #endif`);
  };
  m.customProgramCacheKey = () => "pintura-mascara";
  m.needsUpdate = true;
}

let shadowTexture;
function getShadowTexture() {
  if (shadowTexture) return shadowTexture;
  const c = document.createElement("canvas");
  c.width = c.height = 128;
  const ctx = c.getContext("2d");
  const grad = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, "rgba(0,0,0,0.6)");
  grad.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 128, 128);
  shadowTexture = new THREE.CanvasTexture(c);
  return shadowTexture;
}

// Clona el modelo con materiales propios y detecta cuáles son la pintura.
function prepareCar(src, cfg, type, color) {
  const model = src.clone(true);
  model.position.set(0, 0, 0);
  model.updateMatrixWorld(true);

  const clones = new Map(); // material original -> copia, para respetar materiales compartidos
  const areas = new Map();  // copia -> superficie aproximada que cubre
  const box = new THREE.Box3(), size = new THREE.Vector3();
  model.traverse((o) => {
    if (!o.isMesh) return;
    const cloneMat = (m) => {
      if (!clones.has(m)) clones.set(m, m.clone());
      return clones.get(m);
    };
    o.material = Array.isArray(o.material) ? o.material.map(cloneMat) : cloneMat(o.material);
    box.setFromObject(o).getSize(size);
    const area = size.x * size.y + size.y * size.z + size.x * size.z;
    for (const m of [].concat(o.material)) areas.set(m, (areas.get(m) || 0) + area);
  });

  const mats = [...areas.keys()];
  let paint;
  if (cfg.pintura?.length) {
    paint = mats.filter((m) => cfg.pintura.includes(m.name));
  } else {
    paint = mats.filter((m) => PAINT_RE.test(m.name) && !NOT_PAINT_RE.test(m.name));
    if (!paint.length) {
      const candidatos = mats.filter((m) => !NOT_PAINT_RE.test(m.name) && !m.transparent && m.opacity === 1);
      candidatos.sort((a, b) => areas.get(b) - areas.get(a));
      paint = candidatos.slice(0, 1);
    }
  }
  for (const m of paint) {
    if (cfg.mascara && m.map) {
      pintarConMascara(m, color);
    } else {
      // Si la pintura trae textura de color, se quita para que el color elegido se vea limpio.
      if (m.map && mats.length > 2) { m.map = null; m.needsUpdate = true; }
      m.color.set(color);
    }
  }

  // Orientar a lo largo del eje X, escalar a tamaño real y apoyar en el piso.
  const wrap = new THREE.Group();
  wrap.add(model);
  if (cfg.rotacion) model.rotation.y += THREE.MathUtils.degToRad(cfg.rotacion);
  box.setFromObject(wrap).getSize(size);
  if (size.z > size.x) {
    model.rotation.y += Math.PI / 2;
    box.setFromObject(wrap).getSize(size);
  }
  wrap.scale.setScalar((cfg.largo || LARGOS[type] || 4.5) / size.x);
  box.setFromObject(wrap);
  const center = box.getCenter(new THREE.Vector3());
  wrap.position.set(-center.x, -box.min.y, -center.z);
  box.setFromObject(wrap).getSize(size);

  const root = new THREE.Group();
  root.add(wrap);
  const shadow = new THREE.Mesh(
    new THREE.PlaneGeometry(size.x * 1.25, size.z * 1.7).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ map: getShadowTexture(), transparent: true, depthWrite: false }));
  shadow.position.y = 0.005;
  root.add(shadow);
  root.userData = { paint, length: size.x, width: size.z, height: size.y };
  return root;
}

function dispose(obj) {
  // Geometrías y texturas se comparten con el modelo cargado: solo se liberan las copias de materiales.
  obj.traverse((o) => {
    if (!o.isMesh) return;
    for (const m of [].concat(o.material)) m.dispose();
  });
}

export function mountCar(el, { type = "sedan", color = "#2e6fd8", interactive = false } = {}) {
  // En celulares la pantalla ya es muy densa: más resolución solo gasta batería.
  const dpr = window.devicePixelRatio || 1;
  const tactil = window.matchMedia("(pointer: coarse)").matches;
  const renderer = new THREE.WebGLRenderer({ antialias: dpr < 2, alpha: true, powerPreference: "low-power" });
  renderer.setPixelRatio(Math.min(dpr, tactil ? 1.5 : 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  el.appendChild(renderer.domElement);
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute("aria-label", `Modelo 3D de un vehículo (${NOMBRES[type] || type})`);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;
  const sun = new THREE.DirectionalLight(0xffffff, 1.6);
  sun.position.set(5, 8, 4);
  scene.add(sun, new THREE.HemisphereLight(0xffffff, 0x445066, 0.4));

  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100);
  camera.position.set(0, 0.36, 1);
  let car = null;
  let spinning = true;
  let pedido = 0;

  let controls = null;
  if (interactive) {
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.minPolarAngle = 0.7;
    controls.maxPolarAngle = 1.5;
    // En pantallas táctiles el dedo vertical tiene que mover la página, no el auto: solo se gira en
    // horizontal (OrbitControls pone touch-action: none, que bloquea el scroll).
    renderer.domElement.style.touchAction = "pan-y";
    if (tactil) controls.minPolarAngle = controls.maxPolarAngle = 1.23;
    controls.addEventListener("start", () => { spinning = false; });
    controls.addEventListener("end", () => { spinning = true; });
  }

  function frame() {
    const w = el.clientWidth || 1, h = el.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    if (car) {
      const vfov = THREE.MathUtils.degToRad(camera.fov);
      const hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
      const { length, width, height } = car.userData;
      const dist = Math.max(Math.hypot(length, width) / 2 / Math.tan(hfov / 2),
                            (height / 2 + 0.3) / Math.tan(vfov / 2)) * 1.12;
      const target = new THREE.Vector3(0, height * 0.45, 0);
      const dir = controls ? camera.position.clone().sub(controls.target).normalize()
                           : new THREE.Vector3(0, 0.36, 1).normalize();
      camera.position.copy(target).addScaledVector(dir, dist);
      camera.lookAt(target);
      if (controls) { controls.target.copy(target); controls.update(); }
    }
    camera.updateProjectionMatrix();
  }

  async function setType(t) {
    const mio = ++pedido;
    el.dataset.type = t;
    el.classList.add("car-stage-loading");
    el.classList.remove("car-stage-missing");
    try {
      const { src, cfg } = await loadModel(t);
      if (mio !== pedido) return;
      const rot = car ? car.rotation.y : -0.6;
      if (car) { scene.remove(car); dispose(car); }
      car = prepareCar(src, cfg, t, color);
      car.rotation.y = rot;
      scene.add(car);
      frame();
      renderer.domElement.setAttribute("aria-label", `Modelo 3D de un vehículo (${NOMBRES[t] || t})`);
      el.classList.add("car-listo");
    } catch (err) {
      if (mio !== pedido) return;
      console.warn(`Modelo 3D "${t}" no disponible:`, err);
      if (car) { scene.remove(car); dispose(car); car = null; }
      el.dataset.msg = `Vista 3D de ${NOMBRES[t] || t}: falta cargar el modelo`;
      el.classList.add("car-stage-missing");
    } finally {
      if (mio === pedido) el.classList.remove("car-stage-loading");
    }
  }

  function setColor(c) {
    color = c;
    if (car) for (const m of car.userData.paint) (m.userData.uPaint ? m.userData.uPaint.value : m.color).set(c);
  }

  setType(type);
  new ResizeObserver(frame).observe(el);

  const clock = new THREE.Clock();
  const loop = () => {
    const dt = Math.min(clock.getDelta(), 0.05);
    if (car && spinning) car.rotation.y += dt * 0.5;
    if (controls) controls.update();
    renderer.render(scene, camera);
  };
  // Solo animar cuando está a la vista.
  new IntersectionObserver(([entry]) => {
    renderer.setAnimationLoop(entry.isIntersecting ? loop : null);
    clock.getDelta();
  }).observe(el);

  return { setType, setColor };
}

// Montaje automático: <div data-car3d data-type="sedan" data-color="#hex">
// Opcionales: data-interactive, data-type-from / data-color-from (selectores
// de inputs que actualizan el modelo en vivo).
// Cada visor arranca recién cuando está por aparecer en pantalla.
function montar(el) {
  let car;
  try {
    car = mountCar(el, {
      type: el.dataset.type,
      color: el.dataset.color,
      interactive: "interactive" in el.dataset,
    });
  } catch (err) {
    console.warn("No se pudo iniciar el visor 3D", err);
    el.classList.add("car-stage-off");
    return;
  }
  if (el.dataset.typeFrom) {
    document.querySelectorAll(el.dataset.typeFrom).forEach((i) =>
      i.addEventListener("change", () => i.checked !== false && car.setType(i.value)));
  }
  if (el.dataset.colorFrom) {
    document.querySelectorAll(el.dataset.colorFrom).forEach((i) =>
      i.addEventListener("input", () => car.setColor(i.value)));
  }
}

const cerca = new IntersectionObserver((entradas) => {
  for (const e of entradas) {
    if (!e.isIntersecting) continue;
    cerca.unobserve(e.target);
    montar(e.target);
  }
}, { rootMargin: "300px 0px" });
document.querySelectorAll("[data-car3d]").forEach((el) => cerca.observe(el));
