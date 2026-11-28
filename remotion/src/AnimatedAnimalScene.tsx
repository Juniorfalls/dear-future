import React, {useMemo} from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {MantisShrimp, MANTIS_COLORS} from './three/MantisShrimp';
import './animal.css';
import episode from '../public/animal.json';
import voiceWords from '../public/vo_words.json';

type Word = {word: string; start: number; end: number};

const DATA = episode as unknown as {
  series: string;
  episode: number;
  total: number;
  title: string;
  titleWords: string[];
  subtitle: string;
  species: string;
  audio: string;
  duration: number;
  stat: {value: number; unit: string; label: string; caption: string};
  timeline: Record<string, number>;
};
const TL = DATA.timeline;
const WORDS = (voiceWords as Word[]).slice();

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const reveal = (t: number, at: number, dur = 0.9) =>
  interpolate(t, [at, at + dur], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>
     <filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='3' stitchTiles='stitch'/>
       <feColorMatrix type='saturate' values='0'/></filter>
     <rect width='220' height='220' filter='url(#n)' opacity='0.55'/></svg>`,
)}")`;

/* ------------------------------------------------------------ 3D world */

const CameraRig: React.FC<{t: number; vertical: boolean}> = ({t, vertical}) => {
  const {camera} = useThree();
  const yaw = Math.sin(t * 0.28) * 0.1;
  const dolly = 6.9 - t * 0.055;
  camera.position.set(
    Math.sin(yaw) * 0.55,
    0.45 + Math.sin(t * 0.5) * 0.08,
    vertical ? dolly + 2.1 : dolly,
  );
  camera.lookAt(0, -0.05, 0);
  camera.updateProjectionMatrix();
  return null;
};

const Bubbles: React.FC<{t: number; count?: number}> = ({t, count = 46}) => {
  const seeds = useMemo(
    () =>
      Array.from({length: count}, (_, i) => ({
        x: Math.sin(i * 12.9898) * 3.6,
        z: Math.cos(i * 7.233) * 2.2,
        speed: 0.16 + ((i * 37) % 100) / 420,
        offset: ((i * 53) % 100) / 100,
        r: 0.012 + ((i * 17) % 100) / 4200,
      })),
    [count],
  );
  return (
    <group>
      {seeds.map((b, i) => {
        const p = (t * b.speed + b.offset) % 1;
        return (
          <mesh key={i} position={[b.x + Math.sin(t * 0.6 + i) * 0.12, -1.5 + p * 4.2, b.z]}>
            <sphereGeometry args={[b.r, 6, 6]} />
            <meshBasicMaterial color="#cdeff7" transparent opacity={0.5 * (1 - p)} />
          </mesh>
        );
      })}
    </group>
  );
};

const GodRays: React.FC<{t: number}> = ({t}) => (
  <group>
    {[0, 1, 2, 3].map((i) => (
      <mesh
        key={i}
        position={[-1.6 + i * 1.15, 1.9, -1.4 + (i % 2) * 0.8]}
        rotation={[0, 0, 0.16 - i * 0.06 + Math.sin(t * 0.35 + i) * 0.02]}
      >
        <coneGeometry args={[0.55, 5.2, 12, 1, true]} />
        <meshBasicMaterial
          color="#9fe6ff"
          transparent
          opacity={0.045 + Math.sin(t * 0.8 + i * 1.7) * 0.014}
          side={2}
          depthWrite={false}
          blending={2}
        />
      </mesh>
    ))}
  </group>
);

const Reef: React.FC = () => (
  <group>
    <mesh position={[0, -1.62, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[9, 40]} />
      <meshStandardMaterial color="#0a1c21" roughness={0.98} metalness={0} />
    </mesh>
    {[
      {p: [-2.6, -1.5, -1.1], s: 0.55, c: '#123037'},
      {p: [2.9, -1.52, 0.4], s: 0.42, c: '#0f272d'},
      {p: [-1.4, -1.55, 1.6], s: 0.3, c: '#16343a'},
      {p: [1.8, -1.56, -1.9], s: 0.36, c: '#0d2429'},
    ].map((r, i) => (
      <mesh key={i} position={r.p as [number, number, number]} scale={r.s} rotation={[i * 0.7, i * 1.3, i * 0.4]}>
        <icosahedronGeometry args={[1, 0]} />
        <meshStandardMaterial color={r.c} roughness={0.95} flatShading />
      </mesh>
    ))}
    {/* the caustic pool the shrimp hovers in */}
    <mesh position={[0, -1.6, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <circleGeometry args={[2.6, 32]} />
      <meshBasicMaterial color="#2e7f8f" transparent opacity={0.18} blending={2} depthWrite={false} />
    </mesh>
  </group>
);

const Shockwave: React.FC<{p: number}> = ({p}) => {
  if (p <= 0 || p >= 1) return null;
  const r = 0.2 + p * 1.5;
  return (
    <group position={[1.95, -0.12, 0]}>
      <mesh>
        <ringGeometry args={[r * 0.82, r, 44]} />
        <meshBasicMaterial color="#d8f8ff" transparent opacity={0.75 * (1 - p)} blending={2} depthWrite={false} />
      </mesh>
      <mesh scale={[1, 1, 1]}>
        <sphereGeometry args={[r * 0.45, 14, 12]} />
        <meshBasicMaterial color="#eafaff" transparent opacity={0.3 * (1 - p)} blending={2} depthWrite={false} />
      </mesh>
    </group>
  );
};

/* ------------------------------------------------------------ UI overlay */

const buildLines = (words: Word[], maxChars = 44, maxWords = 7) => {
  const lines: {words: Word[]}[] = [];
  let bucket: Word[] = [];
  let chars = 0;
  const flush = () => {
    if (bucket.length) lines.push({words: bucket});
    bucket = [];
    chars = 0;
  };
  for (const w of words) {
    const len = w.word.replace(/[^\w']/g, '').length;
    if (bucket.length && (chars + len + 1 > maxChars || bucket.length >= maxWords)) flush();
    bucket.push(w);
    chars += len + 1;
    if (/[.!?]$/.test(w.word) && bucket.length >= 3) flush();
  }
  flush();
  return lines;
};
const LINES = buildLines(WORDS);

const Captions: React.FC<{t: number}> = ({t}) => {
  const idx = LINES.findIndex((l) => t >= l.words[0].start - 0.08 && t <= l.words[l.words.length - 1].end + 0.45);
  if (idx < 0) return null;
  return (
    <div className="captions">
      <div className="caption-line">
        {LINES[idx].words.map((w, i) => {
          const on = t >= w.start - 0.04 && t <= w.end + 0.06;
          return (
            <span key={`${w.start}-${i}`} className={on ? 'caption-word on' : 'caption-word'}>
              {w.word.replace(/[.,;:!?]$/, '')}
            </span>
          );
        })}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------ composition */

export const AnimatedAnimalScene: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const vertical = height > width;
  const u = vertical ? 1 : width / 1920;

  const flashAt = TL.flashAt ?? DATA.duration * 0.55;
  const punch = interpolate(t, [flashAt - 0.42, flashAt - 0.05, flashAt + 0.1, flashAt + 0.75], [0, 0.55, 1, 0], clamp);
  const shock = interpolate(t, [flashAt, flashAt + 0.55], [0, 1], clamp);
  const strikeLight = interpolate(t, [flashAt, flashAt + 0.08, flashAt + 0.5], [0, 1, 0], {...clamp, easing: Easing.out(Easing.quad)});

  const titleAt = TL.titleAt ?? 0;
  const subtitleP = reveal(t, TL.subtitleAt ?? 2.4, 1.0);
  const speciesP = reveal(t, (TL.subtitleAt ?? 2.4) + 0.35, 1.0);
  const ruleP = reveal(t, titleAt + 0.62, 1.1);
  const statAt = TL.statAt ?? 4;
  const statP = reveal(t, statAt, 1.0);
  const statCount = interpolate(t, [statAt, statAt + 1.2], [0, DATA.stat.value], {...clamp, easing: Easing.out(Easing.cubic)});
  const fadeOut = interpolate(frame, [durationInFrames - 20, durationInFrames - 1], [0, 1], clamp);

  return (
    <AbsoluteFill className={vertical ? 'doc vertical' : 'doc'} style={{['--u' as string]: u}}>
      <Audio src={staticFile(DATA.audio)} volume={1} />

      {/* deep-water backdrop: CSS gradient behind a transparent WebGL canvas */}
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(ellipse 90% 70% at 50% 8%, #17505f 0%, #0b2b36 38%, #05141a 72%, #020709 100%)',
        }}
      />

      <ThreeCanvas
        width={width}
        height={height}
        dpr={1}
        shadows={false}
        gl={{antialias: true, alpha: true}}
        camera={{fov: vertical ? 42 : 36, position: [0, 0.45, 6.9], near: 0.1, far: 100}}
        style={{position: 'absolute', inset: 0}}
      >
        <fogExp2 attach="fog" args={['#062028', 0.115]} />
        <ambientLight intensity={0.55} color="#9fd7e0" />
        <directionalLight position={[3.4, 5.2, 3.6]} intensity={2.1} color="#fff2d8" />
        <pointLight position={[-3.6, 1.2, -2.6]} intensity={22} color="#ff9d5c" distance={14} />
        <pointLight position={[-2.4, -0.6, 3.4]} intensity={12} color="#39b8d8" distance={12} />
        <pointLight
          position={[2.4, 0.6, 1.6]}
          intensity={8 + strikeLight * 46}
          color="#d9f6ff"
          distance={9}
        />

        <CameraRig t={t} vertical={vertical} />
        <GodRays t={t} />
        <Reef />
        <MantisShrimp time={t} punch={punch} flash={strikeLight} scale={vertical ? 1.16 : 1.0} />
        <Bubbles t={t} count={vertical ? 60 : 46} />
        <Shockwave p={shock} />
      </ThreeCanvas>

      {/* cinematic grade on top of the 3D layer */}
      <div className="vignette" />
      <div
        className="bloom"
        style={{
          background: `radial-gradient(46% 40% at 58% 46%, rgba(214,248,255,${strikeLight * 0.7}) 0%, rgba(120,200,255,0) 72%)`,
          mixBlendMode: 'screen',
        }}
      />
      <div className="grain" style={{backgroundImage: GRAIN, backgroundPosition: `${(frame * 17) % 220}px ${(frame * 29) % 220}px`}} />

      <div className="ui">
        <div className="topbar">
          <div className="brand">
            <span className="brand-rule" />
            {DATA.series}
          </div>
          <div>
            <div className="counter">
              <span className="now">{String(DATA.episode).padStart(2, '0')}</span>
              <span>/</span>
              <span>{String(DATA.total).padStart(2, '0')}</span>
            </div>
            <div className="pips">
              {Array.from({length: DATA.total}, (_, i) => (
                <span key={i} className={i < DATA.episode ? 'pip on' : 'pip'} />
              ))}
            </div>
          </div>
        </div>

        <div className="bottom">
          <div className="headline">
            <h1 className="title">
              {DATA.titleWords.map((word, i) => {
                const p = reveal(t, titleAt + i * 0.13, 1.0);
                return (
                  <span
                    key={`${word}-${i}`}
                    className={`word${/^(the|an|a)$/i.test(word) ? ' italic' : ''}`}
                    style={{opacity: p, transform: `translateY(${(1 - p) * 34}px)`, filter: `blur(${(1 - p) * 12}px)`}}
                  >
                    {word}
                  </span>
                );
              })}
            </h1>
            <div className="rule" style={{transform: `scaleX(${ruleP})`, opacity: 0.9}} />
            <p
              className="subtitle"
              style={{opacity: subtitleP, transform: `translateY(${(1 - subtitleP) * 18}px)`, filter: `blur(${(1 - subtitleP) * 6}px)`}}
            >
              {DATA.subtitle}
            </p>
            <p className="species" style={{opacity: speciesP * 0.95}}>
              {DATA.species}
            </p>
          </div>

          <div className="stat" style={{opacity: statP, transform: `translateY(${(1 - statP) * 26}px)`, filter: `blur(${(1 - statP) * 6}px)`}}>
            <div className="stat-value">{Math.round(statCount).toLocaleString('en-US')}</div>
            <div className="stat-unit">{DATA.stat.unit}</div>
            <div className="stat-label">{DATA.stat.label}</div>
          </div>
        </div>
      </div>

      <div className="caption-scrim" />
      <Captions t={t} />

      <AbsoluteFill style={{background: '#000', opacity: fadeOut, pointerEvents: 'none'}} />
      {/* keeps the imported palette alive for quick restyling in the scene file */}
      <span style={{display: 'none'}}>{MANTIS_COLORS.teal}</span>
    </AbsoluteFill>
  );
};
