import * as THREE from 'three';

const FORMAT = new URLSearchParams(location.search).get('format') === 'vertical' ? 'vertical' : 'landscape';
const VERT = FORMAT === 'vertical';
const W = VERT ? 1080 : 1920, H = VERT ? 1920 : 1080, FPS = 30;
const EPISODE = await (await fetch('./assets/episode.json')).json();
const DUR = EPISODE.duration || 30;
const SCALE = Math.min(1, Math.max(.4, parseFloat(new URLSearchParams(location.search).get('scale') || '1')));
const IW = Math.round(W * SCALE), IH = Math.round(H * SCALE);
const out = document.getElementById('out'), octx = out.getContext('2d');
const glCanvas = document.getElementById('gl');
out.width = W; out.height = H; glCanvas.width = IW; glCanvas.height = IH;

const renderer = new THREE.WebGLRenderer({canvas: glCanvas, antialias: false, preserveDrawingBuffer: false, powerPreference: 'high-performance'});
renderer.setSize(IW, IH, false); renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.12;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#f6e6c6');
scene.fog = new THREE.Fog('#f6e6c6', 18, 34);
const camera = new THREE.PerspectiveCamera(VERT ? 48 : 33, W / H, .1, 80);

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const wood = canvasTex(1024, 1024, (x, w, h) => {
  x.fillStyle = '#b98550'; x.fillRect(0, 0, w, h);
  for (let i = 0; i < 10; i++) {
    x.fillStyle = i % 2 ? '#b07c49' : '#c08d58'; x.fillRect(0, i * h / 10, w, h / 10 - 3);
    x.strokeStyle = 'rgba(90,55,28,.28)'; x.lineWidth = 2;
    x.beginPath(); x.moveTo(0, i * h / 10); x.lineTo(w, i * h / 10); x.stroke();
  }
});
wood.wrapS = wood.wrapT = THREE.RepeatWrapping; wood.repeat.set(4, 4);
const sky = canvasTex(1024, 768, (x, w, h) => {
  const g = x.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, '#7ec8f2'); g.addColorStop(.55, '#bfe6fb'); g.addColorStop(1, '#eaf8ff');
  x.fillStyle = g; x.fillRect(0, 0, w, h);
  x.fillStyle = '#ffe58a'; x.beginPath(); x.arc(w * .78, h * .22, 70, 0, Math.PI * 2); x.fill();
  x.fillStyle = 'rgba(255,255,255,.9)';
  for (const [cx, cy, r] of [[.2, .3, 44], [.28, .25, 58], [.37, .32, 40], [.55, .18, 32], [.62, .22, 42], [.7, .19, 28]]) {
    x.beginPath(); x.arc(w * cx, h * cy, r, 0, Math.PI * 2); x.fill();
  }
  x.fillStyle = '#79b866'; x.beginPath(); x.moveTo(0, h); x.quadraticCurveTo(w * .3, h * .55, w * .6, h); x.fill();
  x.fillStyle = '#5e9c4e'; x.beginPath(); x.moveTo(w * .45, h); x.quadraticCurveTo(w * .72, h * .6, w, h); x.fill();
});

// room
const floor = new THREE.Mesh(new THREE.PlaneGeometry(26, 18), new THREE.MeshStandardMaterial({map: wood, roughness: .68}));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);
const back = new THREE.Mesh(new THREE.PlaneGeometry(26, 11), new THREE.MeshStandardMaterial({color: '#f7e2b7', roughness: .95}));
back.position.set(0, 5.5, -4.4); back.receiveShadow = true; scene.add(back);
const left = new THREE.Mesh(new THREE.PlaneGeometry(20, 11), new THREE.MeshStandardMaterial({color: '#d7ebef', roughness: .95}));
left.position.set(-8.6, 5.5, 0); left.rotation.y = Math.PI / 2; left.receiveShadow = true; scene.add(left);
const baseboard = new THREE.Mesh(new THREE.BoxGeometry(26, .22, .12), new THREE.MeshStandardMaterial({color: '#a8cfd8'}));
baseboard.position.set(0, .22, -4.36); scene.add(baseboard);

const win = new THREE.Group(); win.position.set(5.3, 3.5, -4.3);
win.add(new THREE.Mesh(new THREE.PlaneGeometry(3.3, 2.5), new THREE.MeshBasicMaterial({map: sky})));
const frameMat = new THREE.MeshStandardMaterial({color: '#f8f4ea', roughness: .5});
for (const [w, h, x, y] of [[3.6, .14, 0, 1.32], [3.6, .14, 0, -1.32], [.14, 2.75, -1.7, 0], [.14, 2.75, 1.7, 0], [.1, 2.6, 0, 0]]) {
  const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, .12), frameMat); b.position.set(x, y, .06); win.add(b);
}
const sill = new THREE.Mesh(new THREE.BoxGeometry(3.9, .14, .4), frameMat); sill.position.set(0, -1.4, .12); win.add(sill);
scene.add(win);

// whiteboard
const boardCanvas = document.createElement('canvas'); boardCanvas.width = 2048; boardCanvas.height = 1120;
const bx = boardCanvas.getContext('2d');
const boardTex = new THREE.CanvasTexture(boardCanvas); boardTex.colorSpace = THREE.SRGBColorSpace; boardTex.anisotropy = 8;
const boardFrame = new THREE.Mesh(new THREE.BoxGeometry(7.5, 4.2, .12), new THREE.MeshStandardMaterial({color: '#c9d1d4', metalness: .35, roughness: .45}));
boardFrame.position.set(-.5, 3.05, -4.18); boardFrame.castShadow = true; scene.add(boardFrame);
const board = new THREE.Mesh(new THREE.PlaneGeometry(7.1, 3.88), new THREE.MeshStandardMaterial({map: boardTex, roughness: .9}));
board.position.set(-.5, 3.05, -4.11); scene.add(board);
const tray = new THREE.Mesh(new THREE.BoxGeometry(7.3, .09, .3), new THREE.MeshStandardMaterial({color: '#9aa4a8'}));
tray.position.set(-.5, .92, -4.02); scene.add(tray);
for (const [x, c] of [[-2.2, '#2b5f8f'], [-1.7, '#c0392b'], [-1.25, '#2f2f2f']]) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(.035, .035, .26, 8), new THREE.MeshStandardMaterial({color: c}));
  m.rotation.z = Math.PI / 2; m.position.set(x, .97, -4.0); scene.add(m);
}

// people
const skin = new THREE.MeshStandardMaterial({color: '#f0c49c', roughness: .8});
const shoeMat = new THREE.MeshStandardMaterial({color: '#1c2026', roughness: .7});
const hairMat = new THREE.MeshStandardMaterial({color: '#33251f', roughness: .9});
function limb(len, rad, mat) { return new THREE.Mesh(new THREE.CapsuleGeometry(rad, Math.max(.01, len - rad * 2), 6, 12), mat); }

function makeTeacher() {
  const g = new THREE.Group();
  const shirt = new THREE.MeshStandardMaterial({color: '#2f6fb3', roughness: .8});
  const pants = new THREE.MeshStandardMaterial({color: '#33415c', roughness: .85});
  const tie = new THREE.MeshStandardMaterial({color: '#d94f4f', roughness: .7});
  for (const s of [-1, 1]) {
    const leg = limb(.98, .085, pants); leg.position.set(s * .13, .5, 0); leg.castShadow = true; g.add(leg);
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(.24, .13, .42), shoeMat); shoe.position.set(s * .13, .07, .08); shoe.castShadow = true; g.add(shoe);
  }
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(.27, .5, 8, 16), shirt);
  torso.position.set(0, 1.48, 0); torso.castShadow = true; g.add(torso);
  const tieMesh = new THREE.Mesh(new THREE.BoxGeometry(.09, .55, .04), tie); tieMesh.position.set(0, 1.5, .265); g.add(tieMesh);
  const collar = new THREE.Mesh(new THREE.BoxGeometry(.26, .08, .05), new THREE.MeshStandardMaterial({color: '#f4f1e8'})); collar.position.set(0, 1.76, .24); g.add(collar);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.235, 24, 20), skin); head.position.set(0, 2.12, 0); head.castShadow = true; g.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.245, 24, 16, 0, Math.PI * 2, 0, Math.PI * .58), hairMat); hair.position.set(0, 2.16, -.02); g.add(hair);
  for (const s of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(.022, 8, 8), new THREE.MeshStandardMaterial({color: '#1b2430'})); eye.position.set(s * .075, 2.14, .215); g.add(eye);
  }
  const smile = new THREE.Mesh(new THREE.TorusGeometry(.055, .011, 6, 14, Math.PI), new THREE.MeshStandardMaterial({color: '#8a5b48'}));
  smile.position.set(0, 2.045, .215); smile.rotation.z = Math.PI; g.add(smile);
  const arm = (side) => {
    const pivot = new THREE.Group(); pivot.position.set(side * .29, 1.7, 0);
    const upper = limb(.5, .07, shirt); upper.position.y = -.25; upper.castShadow = true; pivot.add(upper);
    const elbow = new THREE.Group(); elbow.position.y = -.48;
    const fore = limb(.45, .06, skin); fore.position.y = -.22; elbow.add(fore);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(.065, 10, 8), skin); hand.position.y = -.45; elbow.add(hand);
    pivot.add(elbow); g.add(pivot); return {pivot, elbow};
  };
  return {group: g, arms: {l: arm(-1), r: arm(1)}};
}
const teacher = makeTeacher(); teacher.group.position.set(3.35, 0, -2.05); teacher.group.rotation.y = -.05; scene.add(teacher.group);

const shirtCols = ['#4a9d6e', '#d1604f', '#4f77c8'];
function makeStudent(shirtColor, hairColor) {
  const g = new THREE.Group();
  const shirt = new THREE.MeshStandardMaterial({color: shirtColor, roughness: .85});
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(.24, .42, 8, 14), shirt); body.position.y = .95; body.castShadow = true; g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.2, 20, 16), skin); head.position.y = 1.42; head.castShadow = true; g.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.212, 20, 14, 0, Math.PI * 2, 0, Math.PI * .62), new THREE.MeshStandardMaterial({color: hairColor, roughness: .95})); hair.position.set(0, 1.45, -.02); g.add(hair);
  const chair = new THREE.Mesh(new THREE.BoxGeometry(.62, .07, .6), new THREE.MeshStandardMaterial({color: '#8a5a33'})); chair.position.y = .52; g.add(chair);
  return g;
}
const students = [];
for (let i = 0; i < 3; i++) {
  const s = makeStudent(shirtCols[i], ['#2f231d', '#6b4a2f', '#302a2a'][i]);
  s.position.set(-2.6 + i * 2.6, 0, 1.75); s.rotation.y = Math.PI; scene.add(s); students.push(s);
}
function makeDesk(x, z) {
  const g = new THREE.Group();
  const top = new THREE.Mesh(new THREE.BoxGeometry(1.85, .09, 1.0), new THREE.MeshStandardMaterial({color: '#b5793f', roughness: .6}));
  top.position.y = 1.02; top.castShadow = true; top.receiveShadow = true; g.add(top);
  for (const sx of [-.78, .78]) for (const sz of [-.38, .38]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(.07, .98, .07), new THREE.MeshStandardMaterial({color: '#6b4326'})); leg.position.set(sx, .5, sz); g.add(leg);
  }
  g.position.set(x, 0, z); scene.add(g);
}
for (let i = 0; i < 3; i++) makeDesk(-2.6 + i * 2.6, 2.35);

const poster = canvasTex(400, 520, (x, w, h) => {
  x.fillStyle = '#e7f3e9'; x.fillRect(0, 0, w, h);
  x.fillStyle = '#2f6b4f'; x.font = 'bold 120px Arial'; x.textAlign = 'center'; x.fillText('a/b', w / 2, 250);
  x.font = 'bold 54px Arial'; x.fillText('FRACTIONS', w / 2, 380);
});
const p1 = new THREE.Mesh(new THREE.PlaneGeometry(.95, 1.24), new THREE.MeshStandardMaterial({map: poster}));
p1.position.set(7.45, 3.2, -3.2); p1.rotation.y = -Math.PI / 2; scene.add(p1);

const clockG = new THREE.Group();
const rim = new THREE.Mesh(new THREE.TorusGeometry(.44, .05, 10, 40), new THREE.MeshStandardMaterial({color: '#3c4652'}));
clockG.add(rim);
const face = new THREE.Mesh(new THREE.CircleGeometry(.43, 40), new THREE.MeshStandardMaterial({color: '#fbfaf2'}));
face.position.z = .02; clockG.add(face);
for (let h = 0; h < 12; h++) {
  const tick = new THREE.Mesh(new THREE.BoxGeometry(.025, .06, .01), new THREE.MeshStandardMaterial({color: '#39424e'}));
  const a = h / 12 * Math.PI * 2;
  tick.position.set(Math.sin(a) * .35, Math.cos(a) * .35, .03); tick.rotation.z = -a; clockG.add(tick);
}
const hour = new THREE.Mesh(new THREE.BoxGeometry(.04, .22, .015), new THREE.MeshStandardMaterial({color: '#242c36'}));
hour.position.set(0, .1, .04); hour.rotation.z = -1.0; clockG.add(hour);
const minute = new THREE.Mesh(new THREE.BoxGeometry(.03, .33, .015), new THREE.MeshStandardMaterial({color: '#242c36'}));
minute.position.set(0, .15, .04); minute.rotation.z = .5; clockG.add(minute);
clockG.position.set(.4, 5.55, -4.3); scene.add(clockG);

const plant = new THREE.Group();
const pot = new THREE.Mesh(new THREE.CylinderGeometry(.22, .17, .35, 16), new THREE.MeshStandardMaterial({color: '#c96f4a'})); pot.position.y = .18; plant.add(pot);
for (let i = 0; i < 7; i++) {
  const leaf = new THREE.Mesh(new THREE.SphereGeometry(.22, 10, 8), new THREE.MeshStandardMaterial({color: i % 2 ? '#4e8f4a' : '#3f7a3d'}));
  leaf.scale.set(.5, 1.1, .4); leaf.position.set(Math.sin(i) * .18, .55 + (i % 3) * .18, Math.cos(i) * .12); leaf.rotation.z = Math.sin(i) * .5; plant.add(leaf);
}
plant.position.set(-7.2, 0, -2.6); scene.add(plant);

// light
scene.add(new THREE.HemisphereLight('#fff4dc', '#8a6a4a', 1.05));
const sun = new THREE.DirectionalLight('#fff1cf', 2.5); sun.position.set(6.5, 7.5, 4.5); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); sun.shadow.camera.left = -10; sun.shadow.camera.right = 10; sun.shadow.camera.top = 9; sun.shadow.camera.bottom = -3; scene.add(sun);
const fill = new THREE.DirectionalLight('#cfe6ff', .55); fill.position.set(-5, 4, 5); scene.add(fill);
const glow = new THREE.PointLight('#ffe9b8', .6, 12); glow.position.set(-2, 4.5, 1.5); scene.add(glow);

// board: a clean surface plus rasterised KaTeX equation planes
let boardSig = '';
function drawBoard(t) {
  const sig = String(Math.floor(t));
  if (sig === boardSig) return; boardSig = sig;
  bx.fillStyle = '#fbfbf5'; bx.fillRect(0, 0, 2048, 1120);
  bx.font = '700 64px "Trebuchet MS", Arial'; bx.textAlign = 'center'; bx.fillStyle = '#2b5f8f';
  bx.fillText(String(EPISODE.title || 'MATH').toUpperCase(), 1024, 150);
  bx.strokeStyle = '#8fb4cc'; bx.lineWidth = 5;
  bx.beginPath(); bx.moveTo(560, 188); bx.lineTo(1488, 188); bx.stroke();
  bx.fillStyle = 'rgba(60,80,90,.045)';
  for (let gx = 80; gx < 2048; gx += 90) for (let gy = 60; gy < 1120; gy += 90) bx.fillRect(gx, gy, 2, 2);
  boardTex.needsUpdate = true;
}
const EQ = [];
const eqDims = await (await fetch('./assets/eq_manifest.json')).json();
const texLoader = new THREE.TextureLoader();
const eqTextures = {};
for (const eq of EPISODE.equations) {
  const id = eq.id || '1';
  const d = eqDims[id] || {w: 1400, h: 600};
  const h = eq.height || 1.85, w = h * (d.w / d.h);
  const mat = new THREE.MeshBasicMaterial({transparent: true, opacity: 0, depthWrite: false});
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  mesh.position.set(-.5, eq.y || 3.0, -4.075);
  scene.add(mesh);
  EQ.push({mesh, at: eq.at || 0, id, w, h});
  texLoader.load(`./assets/eq_${id}.png`, tex => {
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    mat.map = tex; mat.needsUpdate = true;
  });
}

// coloured rings that reveal which variable is being explained
const RINGS = {};
for (const [name, color] of [['a', '#e0a23a'], ['b', '#4fa3d9'], ['c', '#d1604f']]) {
  const m = new THREE.Mesh(new THREE.TorusGeometry(.19, .028, 8, 32),
    new THREE.MeshBasicMaterial({color, transparent: true, opacity: 0, depthWrite: false}));
  const p = null; // targetPoint is defined below; position set after timeline build
  m.position.set(0, 0, -4.055); scene.add(m);
  RINGS[name] = m;
}
const RING_WINDOWS = {};
for (const a of (EPISODE.actions || [])) {
  if (a.action === 'pointAt' && RINGS[a.target]) {
    RING_WINDOWS[a.target] = [a.at || 0, (a.at || 0) + 2.8];
    const tp = null;
  }
}

// GSAP teacher timeline from episode.actions
let MASTER = null;
function targetPoint(target) {
  const eq = EQ[0];
  const cx = -.5, cy = eq ? eq.mesh.position.y : 3.0;
  const w = eq ? eq.w : 3.87, h = eq ? eq.h : 1.85;
  // normalised glyph positions in the rendered formula image (0..1, y down)
  const spots = {b: [.30, .32], a: [.74, .31], c: [.80, .31], equation_1: [.50, .50]};
  const [nx, ny] = spots[target] || spots.equation_1;
  return [cx + (nx - .5) * w, cy + (.5 - ny) * h];
}
function buildTimeline() {
  MASTER = gsap.timeline({paused: true});
  const T = teacher.group;
  const acts = [...(EPISODE.actions || [])].sort((a, b) => (a.at || 0) - (b.at || 0));
  for (const a of acts) {
    const at = Math.max(0, a.at || 0);
    if (a.action === 'walkTo') {
      MASTER.to(T.position, {x: a.x ?? 3.3, z: a.z ?? -2.05, duration: 1.7, ease: 'power2.inOut'}, at);
    } else if (a.action === 'turnToBoard') {
      MASTER.to(T.rotation, {y: 2.55, duration: .7, ease: 'power2.inOut'}, at);
    } else if (a.action === 'turnToCamera') {
      MASTER.to(T.rotation, {y: 0, duration: .7, ease: 'power2.inOut'}, at);
    } else if (a.action === 'writeOnBoard') {
      MASTER.to(T.rotation, {y: 2.45, duration: .5}, at);
      MASTER.to(teacher.arms.r.pivot.rotation, {x: .55, z: -1.15, duration: .35, yoyo: true, repeat: 3}, at);
      MASTER.to(teacher.arms.r.elbow.rotation, {x: .45, duration: .35, yoyo: true, repeat: 3}, at);
    } else if (a.action === 'pointAt') {
      const p = targetPoint(a.target);
      MASTER.to(T.rotation, {y: 1.35, duration: .55, ease: 'power2.inOut'}, at);
      MASTER.to(teacher.arms.r.pivot.rotation, {x: .35, z: -1.05 - (p[1] - 3.0) * .22, duration: .5, ease: 'power2.out'}, at);
      MASTER.to(teacher.arms.r.elbow.rotation, {x: .28, duration: .5}, at);
      MASTER.to(T.position, {x: Math.max(-1.2, Math.min(3.4, p[0] + .9)), duration: .6, ease: 'power2.inOut'}, at);
    }
  }
  MASTER.to(T.rotation, {y: 0, duration: .8}, Math.max(0, DUR - 1.2));
}
buildTimeline();
for (const name of Object.keys(RINGS)) {
  const p = targetPoint(name);
  RINGS[name].position.set(p[0], p[1], -4.05);
}

// camera setups
const SHOTS = [
  {t0: 0, t1: 8, name: 'wide'},
  {t0: 8, t1: 14.5, name: 'insert'},
  {t0: 14.5, t1: 21.5, name: 'ots'},
  {t0: 21.5, t1: 30, name: 'wide'}
];
const CAMS = VERT ? {
  wide: {pos: [0, 3.1, 15.0], look: [.1, 2.3, 0], push: [0, -.15, -1.0], fov: 48},
  insert: {pos: [-.5, 3.15, 13.2], look: [-.5, 3.0, -4.1], push: [0, -.05, -.6], fov: 40},
  ots: {pos: [-2.45, 1.72, 4.35], look: [-.5, 2.32, -4.0], push: [.1, -.03, -.5], fov: 50}
} : {
  wide: {pos: [0, 2.0, 11.7], look: [.1, 1.95, 0], push: [.08, -.08, -1.3], fov: 33},
  insert: {pos: [-.5, 3.05, 2.7], look: [-.5, 3.0, -4.1], push: [0, -.03, -.55], fov: 35},
  ots: {pos: [-2.55, 1.95, 4.3], look: [-.5, 2.5, -4.0], push: [.1, -.05, -.55], fov: 40}
};

// captions from word timings
let words = [];
const SCRIPT_TEXT = await (await fetch('./assets/script.txt')).text();
function buildCues() {
  // Split the written script at punctuation, then map each clause onto the
  // aligned words so a caption never starts or ends mid-phrase.
  const parts = SCRIPT_TEXT.replace(/\s+/g, ' ').trim()
    .split(/(?<=[.!?:;])\s+|(?<=,)\s+/).filter(p => /[A-Za-z0-9]/.test(p));
  const cues = []; let wi = 0;
  for (const part of parts) {
    const n = (part.match(/[A-Za-z0-9']+/g) || []).length;
    if (!n) continue;
    const seg = words.slice(wi, wi + n);
    if (!seg.length) break;
    cues.push({text: part, start: seg[0].start, end: seg[seg.length - 1].end});
    wi += n;
  }
  if (wi < words.length - 1) {
    // fallback: any unmatched tail becomes one final cue
    const seg = words.slice(wi);
    cues.push({text: seg.map(w => w.word).join(' ') + '.', start: seg[0].start, end: seg[seg.length - 1].end});
  }
  return cues;
}
let CUES = [];
function drawCaptions(t) {
  const cue = CUES.find(c => t >= c.start - .05 && t < c.end + .28);
  if (!cue) return;
  octx.save(); octx.textAlign = 'center'; octx.textBaseline = 'middle'; octx.lineJoin = 'round';
  const maxW = VERT ? W - 110 : 1500;
  const fs = VERT ? 44 : 44;
  octx.font = `600 ${fs}px "Helvetica Neue", Arial, sans-serif`;
  // wrap to max width
  const wordsArr = cue.text.split(' '); const lines = []; let line = '';
  for (const w of wordsArr) {
    const trial = line ? line + ' ' + w : w;
    if (octx.measureText(trial).width > maxW && line) { lines.push(line); line = w; } else line = trial;
  }
  if (line) lines.push(line);
  const lh = fs * 1.28, baseY = VERT ? H - 300 : H - 80;
  lines.forEach((ln, i) => {
    const y = baseY + (i - (lines.length - 1) / 2) * lh;
    const tw = octx.measureText(ln).width;
    octx.fillStyle = 'rgba(12,18,24,.74)';
    octx.beginPath(); octx.roundRect(W / 2 - tw / 2 - 26, y - fs * .78, tw + 52, fs * 1.56, 16); octx.fill();
    octx.lineWidth = 8; octx.strokeStyle = 'rgba(8,12,16,.9)'; octx.strokeText(ln, W / 2, y);
    octx.fillStyle = '#f4ecd8'; octx.fillText(ln, W / 2, y);
  });
  octx.restore();
}

function ease(t) { return t * t * (3 - 2 * t); }
function shootAt(t) { return SHOTS.find(s => t >= s.t0 && t < s.t1) || SHOTS[SHOTS.length - 1]; }

window.renderFrame = (t) => {
  t = Math.max(0, Math.min(DUR - 1 / 60, t));
  const sh = shootAt(t), c = CAMS[sh.name];
  const u = (t - sh.t0) / (sh.t1 - sh.t0), k = ease(Math.min(1, Math.max(0, u)));
  camera.position.set(c.pos[0] + c.push[0] * k, c.pos[1] + c.push[1] * k, c.pos[2] + c.push[2] * k);
  camera.fov = c.fov; camera.updateProjectionMatrix();
  camera.lookAt(c.look[0] + c.push[0] * k * .4, c.look[1], c.look[2]);

  if (MASTER) MASTER.time(t);
  for (const eq of EQ) {
    const a = Math.min(1, Math.max(0, (t - eq.at) / .45));
    eq.mesh.material.opacity = a;
    eq.mesh.visible = a > 0.001;
  }
  for (const [name, m] of Object.entries(RINGS)) {
    const w = RING_WINDOWS[name];
    const a = w ? Math.max(0, Math.min(1, (t - w[0] + .12) / .18) * Math.min(1, (w[1] - t) / .25)) : 0;
    m.material.opacity = a; m.visible = a > .01;
  }
  for (let i = 0; i < students.length; i++) {
    students[i].position.y = Math.sin(t * 1.4 + i * 2.1) * .006;
    students[i].rotation.y = Math.PI + Math.sin(t * .5 + i) * .012;
  }
  drawBoard(t);
  renderer.render(scene, camera);

  octx.setTransform(1, 0, 0, 1, 0, 0);
  octx.drawImage(renderer.domElement, 0, 0, W, H);
  octx.save();
  const vg = octx.createRadialGradient(W / 2, H * .45, H * .35, W / 2, H * .5, H * 1.1);
  vg.addColorStop(0, 'rgba(30,20,10,0)'); vg.addColorStop(1, 'rgba(30,20,10,.28)');
  octx.fillStyle = vg; octx.fillRect(0, 0, W, H);
  octx.globalCompositeOperation = 'soft-light'; octx.globalAlpha = .18;
  octx.fillStyle = '#ffd9a8'; octx.fillRect(0, 0, W, H);
  octx.restore();
  drawCaptions(t);
  return out.toDataURL('image/jpeg', .94);
};

const res = await fetch('./assets/vo_words.json');
words = await res.json();
CUES = buildCues();
drawBoard(0); renderer.render(scene, camera);
window.READY = true;
