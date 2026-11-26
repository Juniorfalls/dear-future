import * as THREE from 'three';

const W = 1920, H = 1080, FPS = 30, DUR = 9.2;
const out = document.getElementById('out'), octx = out.getContext('2d');
const glCanvas = document.getElementById('gl');

const renderer = new THREE.WebGLRenderer({canvas: glCanvas, antialias: true, preserveDrawingBuffer: true});
renderer.setSize(W, H, false);
renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#f6e6c6');
scene.fog = new THREE.Fog('#f6e6c6', 14, 26);
const camera = new THREE.PerspectiveCamera(33, W / H, .1, 60);
camera.position.set(0, 2.0, 11.7);
camera.lookAt(0, 1.9, 0);

// ---------- textures ----------
function canvasTex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8; return t;
}
const wood = canvasTex(1024, 1024, (x, w, h) => {
  x.fillStyle = '#b98550'; x.fillRect(0, 0, w, h);
  for (let i = 0; i < 10; i++) {
    x.fillStyle = i % 2 ? '#b07c49' : '#c08d58';
    x.fillRect(0, i * h / 10, w, h / 10 - 3);
    x.strokeStyle = 'rgba(90,55,28,.28)'; x.lineWidth = 2;
    x.beginPath(); x.moveTo(0, i * h / 10); x.lineTo(w, i * h / 10); x.stroke();
    for (let g = 0; g < 6; g++) {
      x.strokeStyle = 'rgba(120,80,40,.10)'; x.beginPath();
      x.moveTo(0, i * h / 10 + 8 + g * 12); x.bezierCurveTo(w * .3, i * h / 10 + 2 + g * 12, w * .7, i * h / 10 + 20 + g * 12, w, i * h / 10 + 8 + g * 12); x.stroke();
    }
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

// ---------- room ----------
const floor = new THREE.Mesh(new THREE.PlaneGeometry(22, 16), new THREE.MeshStandardMaterial({map: wood, roughness: .68}));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

const back = new THREE.Mesh(new THREE.PlaneGeometry(23, 10), new THREE.MeshStandardMaterial({color: '#f7e2b7', roughness: .95}));
back.position.set(0, 5, -4.4); back.receiveShadow = true; scene.add(back);
const left = new THREE.Mesh(new THREE.PlaneGeometry(18, 10), new THREE.MeshStandardMaterial({color: '#d7ebef', roughness: .95}));
left.position.set(-8.6, 5, 0); left.rotation.y = Math.PI / 2; left.receiveShadow = true; scene.add(left);
const baseboard = new THREE.Mesh(new THREE.BoxGeometry(23, .22, .12), new THREE.MeshStandardMaterial({color: '#a8cfd8'}));
baseboard.position.set(0, .22, -4.36); scene.add(baseboard);

// window
const win = new THREE.Group(); win.position.set(5.3, 3.5, -4.3);
const skyPlane = new THREE.Mesh(new THREE.PlaneGeometry(3.3, 2.5), new THREE.MeshBasicMaterial({map: sky}));
win.add(skyPlane);
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

// ---------- people ----------
const skin = new THREE.MeshStandardMaterial({color: '#f0c49c', roughness: .8});
const dark = new THREE.MeshStandardMaterial({color: '#26303d', roughness: .85});
const hairMat = new THREE.MeshStandardMaterial({color: '#33251f', roughness: .9});
const shoeMat = new THREE.MeshStandardMaterial({color: '#1c2026', roughness: .7});

function limb(len, rad, mat) {
  return new THREE.Mesh(new THREE.CapsuleGeometry(rad, Math.max(.01, len - rad * 2), 6, 12), mat);
}

function makeTeacher() {
  const g = new THREE.Group();
  const shirt = new THREE.MeshStandardMaterial({color: '#2f6fb3', roughness: .8});
  const pants = new THREE.MeshStandardMaterial({color: '#33415c', roughness: .85});
  const tie = new THREE.MeshStandardMaterial({color: '#d94f4f', roughness: .7});
  // legs
  for (const s of [-1, 1]) {
    const leg = limb(.98, .085, pants); leg.position.set(s * .13, .5, 0); leg.castShadow = true; g.add(leg);
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(.24, .13, .42), shoeMat);
    shoe.position.set(s * .13, .07, .08); shoe.castShadow = true; g.add(shoe);
  }
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(.27, .5, 8, 16), shirt);
  torso.position.set(0, 1.48, 0); torso.castShadow = true; g.add(torso);
  const tieMesh = new THREE.Mesh(new THREE.BoxGeometry(.09, .55, .04), tie);
  tieMesh.position.set(0, 1.5, .265); g.add(tieMesh);
  const collar = new THREE.Mesh(new THREE.BoxGeometry(.26, .08, .05), new THREE.MeshStandardMaterial({color: '#f4f1e8'}));
  collar.position.set(0, 1.76, .24); g.add(collar);
  // head
  const head = new THREE.Mesh(new THREE.SphereGeometry(.235, 24, 20), skin);
  head.position.set(0, 2.12, 0); head.castShadow = true; g.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.245, 24, 16, 0, Math.PI * 2, 0, Math.PI * .58), hairMat);
  hair.position.set(0, 2.16, -.02); g.add(hair);
  for (const s of [-1, 1]) {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(.022, 8, 8), new THREE.MeshStandardMaterial({color: '#1b2430'}));
    eye.position.set(s * .075, 2.14, .215); g.add(eye);
  }
  const smile = new THREE.Mesh(new THREE.TorusGeometry(.055, .011, 6, 14, Math.PI), new THREE.MeshStandardMaterial({color: '#8a5b48'}));
  smile.position.set(0, 2.045, .215); smile.rotation.z = Math.PI; g.add(smile);
  // arms with pivots
  const arm = (side) => {
    const pivot = new THREE.Group(); pivot.position.set(side * .29, 1.7, 0);
    const upper = limb(.5, .07, shirt); upper.position.y = -.25; upper.castShadow = true; pivot.add(upper);
    const elbow = new THREE.Group(); elbow.position.y = -.48;
    const fore = limb(.45, .06, skin); fore.position.y = -.22; elbow.add(fore);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(.065, 10, 8), skin); hand.position.y = -.45; elbow.add(hand);
    pivot.add(elbow); g.add(pivot);
    return {pivot, elbow};
  };
  const arms = {l: arm(-1), r: arm(1)};
  return {group: g, arms};
}

const teacher = makeTeacher();
teacher.group.position.set(3.35, 0, -2.05);
teacher.group.rotation.y = -.05;
scene.add(teacher.group);

const shirtCols = ['#4a9d6e', '#d1604f', '#4f77c8'];
function makeStudent(shirtColor, hairColor) {
  const g = new THREE.Group();
  const shirt = new THREE.MeshStandardMaterial({color: shirtColor, roughness: .85});
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(.24, .42, 8, 14), shirt);
  body.position.y = .95; body.castShadow = true; g.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(.2, 20, 16), skin);
  head.position.y = 1.42; head.castShadow = true; g.add(head);
  const hair = new THREE.Mesh(new THREE.SphereGeometry(.212, 20, 14, 0, Math.PI * 2, 0, Math.PI * .62), new THREE.MeshStandardMaterial({color: hairColor, roughness: .95}));
  hair.position.set(0, 1.45, -.02); g.add(hair);
  const chair = new THREE.Mesh(new THREE.BoxGeometry(.62, .07, .6), new THREE.MeshStandardMaterial({color: '#8a5a33'}));
  chair.position.y = .52; g.add(chair);
  return g;
}
const students = [];
for (let i = 0; i < 3; i++) {
  const s = makeStudent(shirtCols[i], ['#2f231d', '#6b4a2f', '#302a2a'][i]);
  s.position.set(-2.6 + i * 2.6, 0, 1.75);
  s.rotation.y = Math.PI;
  scene.add(s); students.push(s);
}

function makeDesk(x, z) {
  const g = new THREE.Group();
  const top = new THREE.Mesh(new THREE.BoxGeometry(1.85, .09, 1.0), new THREE.MeshStandardMaterial({color: '#b5793f', roughness: .6}));
  top.position.y = 1.02; top.castShadow = true; top.receiveShadow = true; g.add(top);
  for (const sx of [-.78, .78]) for (const sz of [-.38, .38]) {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(.07, .98, .07), new THREE.MeshStandardMaterial({color: '#6b4326'}));
    leg.position.set(sx, .5, sz); g.add(leg);
  }
  g.position.set(x, 0, z); scene.add(g);
}
for (let i = 0; i < 3; i++) makeDesk(-2.6 + i * 2.6, 2.35);

// posters and plants
const poster = canvasTex(400, 520, (x, w, h) => {
  x.fillStyle = '#e7f3e9'; x.fillRect(0, 0, w, h);
  x.fillStyle = '#2f6b4f'; x.font = 'bold 120px Arial'; x.textAlign = 'center'; x.fillText('a/b', w / 2, 250);
  x.font = 'bold 54px Arial'; x.fillText('FRACTIONS', w / 2, 380);
});
const p1 = new THREE.Mesh(new THREE.PlaneGeometry(.95, 1.24), new THREE.MeshStandardMaterial({map: poster}));
p1.position.set(7.45, 3.2, -3.2); p1.rotation.y = -Math.PI / 2; scene.add(p1);

const plant = new THREE.Group();
const pot = new THREE.Mesh(new THREE.CylinderGeometry(.22, .17, .35, 16), new THREE.MeshStandardMaterial({color: '#c96f4a'}));
pot.position.y = .18; plant.add(pot);
for (let i = 0; i < 7; i++) {
  const leaf = new THREE.Mesh(new THREE.SphereGeometry(.22, 10, 8), new THREE.MeshStandardMaterial({color: i % 2 ? '#4e8f4a' : '#3f7a3d'}));
  leaf.scale.set(.5, 1.1, .4); leaf.position.set(Math.sin(i) * .18, .55 + (i % 3) * .18, Math.cos(i) * .12);
  leaf.rotation.z = Math.sin(i) * .5; plant.add(leaf);
}
plant.position.set(-7.2, 0, -2.6); scene.add(plant);

// ---------- lighting ----------
scene.add(new THREE.HemisphereLight('#fff4dc', '#8a6a4a', 1.05));
const sun = new THREE.DirectionalLight('#fff1cf', 2.5);
sun.position.set(6.5, 7.5, 4.5); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -9; sun.shadow.camera.right = 9; sun.shadow.camera.top = 8; sun.shadow.camera.bottom = -3;
scene.add(sun);
const fill = new THREE.DirectionalLight('#cfe6ff', .55); fill.position.set(-5, 4, 5); scene.add(fill);
const glow = new THREE.PointLight('#ffe9b8', .6, 12); glow.position.set(-2, 4.5, 1.5); scene.add(glow);

// ---------- whiteboard drawing ----------
const STEPS = [
  {text: '2x + 4 = 10', y: 400, size: 132, t0: .25, color: '#1f2c3a'},
  {text: '2x = 6', y: 630, size: 132, t0: 2.95, color: '#1f2c3a'},
  {text: 'x = 3', y: 860, size: 150, t0: 7.26, color: '#b8362b'}
];
let boardSig = '';
function drawStep(x, text, y, size, color, p, box) {
  x.save();
  x.font = `700 ${size}px "Trebuchet MS", Arial, sans-serif`;
  x.textAlign = 'center'; x.fillStyle = color;
  const wid = x.measureText(text).width;
  if (p < 1) { x.beginPath(); x.rect(1024 - wid / 2 - 30, y - size, (wid + 60) * p, size * 1.45); x.clip(); }
  x.fillText(text, 1024, y);
  if (box) {
    x.strokeStyle = color; x.lineWidth = 7;
    x.strokeRect(1024 - wid / 2 - 34, y - size * .86, wid + 68, size * 1.2);
  }
  x.restore();
}
function drawBoard(t) {
  const p = STEPS.map(s => Math.min(1, Math.max(0, (t - s.t0) / .34)));
  const sig = p.map(v => v.toFixed(2)).join(',') + '|' + (t > 8.0);
  if (sig === boardSig) return; boardSig = sig;
  bx.fillStyle = '#fbfbf5'; bx.fillRect(0, 0, 2048, 1120);
  bx.fillStyle = 'rgba(60,80,90,.05)'; bx.fillRect(0, 0, 2048, 12);
  bx.font = '700 76px "Trebuchet MS", Arial'; bx.textAlign = 'center'; bx.fillStyle = '#2b5f8f';
  bx.fillText('SOLVING FOR X', 1024, 170);
  bx.strokeStyle = '#8fb4cc'; bx.lineWidth = 6; bx.beginPath(); bx.moveTo(760, 205); bx.lineTo(1288, 205); bx.stroke();
  STEPS.forEach((s, i) => drawStep(bx, s.text, s.y, s.size, s.color, p[i], i === 2 && t > 7.95));
  // faint grid dots for a real whiteboard
  bx.fillStyle = 'rgba(60,80,90,.045)';
  for (let gx = 80; gx < 2048; gx += 90) for (let gy = 60; gy < 1120; gy += 90) bx.fillRect(gx, gy, 2, 2);
  boardTex.needsUpdate = true;
}

// ---------- captions ----------
let words = [];
const cues = [
  {a: 0, b: 10, text: 'To solve for X, we first subtract four from both sides,'},
  {a: 11, b: 15, text: 'leaving 2x = 6.'},
  {a: 16, b: 20, text: 'Then we divide by 2,'},
  {a: 21, b: 25, text: 'giving us X = 3.'}
];
const CUES = [
  {a: 0, b: 10, text: 'To solve for X, we first subtract four from both sides,'},
  {a: 11, b: 15, text: 'leaving 2x = 6.'},
  {a: 16, b: 20, text: 'Then we divide by 2,'},
  {a: 21, b: 25, text: 'giving us X = 3.'}
];
function drawCaptions(t) {
  const cue = CUES.find(c => t >= (words[c.a]?.start ?? 0) - .05 && t < (words[c.b]?.end ?? 0) + .45);
  if (!cue) return;
  const active = words.findIndex((w, i) => i >= cue.a && i <= cue.b && t >= w.start - .02 && t < w.end + .04);
  octx.save();
  octx.font = '600 44px "Helvetica Neue", Arial, sans-serif';
  octx.textAlign = 'center'; octx.textBaseline = 'middle';
  const tw = octx.measureText(cue.text).width;
  octx.fillStyle = 'rgba(12,18,24,.72)';
  const px = 960 - tw / 2 - 34, py = 1000;
  octx.beginPath(); octx.roundRect(px, py - 38, tw + 68, 76, 18); octx.fill();
  octx.lineWidth = 8; octx.strokeStyle = 'rgba(8,12,16,.9)';
  octx.strokeText(cue.text, 960, py);
  octx.fillStyle = '#f4ecd8'; octx.fillText(cue.text, 960, py);
  octx.restore();
}

// ---------- animation ----------
function ease(t) { return t * t * (3 - 2 * t); }
function animatePeople(t) {
  const bob = Math.sin(t * 1.8) * .012;
  teacher.group.position.y = bob;
  const step2 = t > 2.95, step3 = t > 7.26;
  const point = Math.min(1, Math.max(0, (t - 1.1) / 1.2));
  teacher.arms.r.pivot.rotation.x = .30 + .06 * Math.sin(t * 1.4) + (step2 ? .16 : 0);
  teacher.arms.r.pivot.rotation.z = -1.02 - .10 * point + (step3 ? -.12 : 0);
  teacher.arms.r.elbow.rotation.x = .25 + .12 * point;
  teacher.arms.l.pivot.rotation.x = .10 + .05 * Math.sin(t * 1.1);
  teacher.arms.l.pivot.rotation.z = .12;
  teacher.group.rotation.y = -.05 + Math.sin(t * .6) * .02;
  for (let i = 0; i < students.length; i++) {
    students[i].position.y = Math.sin(t * 1.4 + i * 2.1) * .008;
    students[i].rotation.y = Math.PI + Math.sin(t * .5 + i) * .015;
  }
}

window.renderFrame = (t) => {
  t = Math.max(0, Math.min(DUR - 1 / 60, t));
  // slow cinematic push-in
  const k = ease(t / DUR);
  camera.position.set(.10 + k * .06, 2.02 - k * .10, 11.7 - k * 1.35);
  camera.lookAt(.1 + k * .04, 1.95 - k * .04, 0);
  camera.updateProjectionMatrix();

  drawBoard(t);
  animatePeople(t);
  renderer.render(scene, camera);

  octx.setTransform(1, 0, 0, 1, 0, 0);
  octx.drawImage(renderer.domElement, 0, 0, W, H);
  // warm film wash + vignette
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
drawBoard(0);
renderer.render(scene, camera);
window.READY = true;
