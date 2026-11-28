import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import './animal.css';
import episode from '../public/animal.json';
import voiceWords from '../public/vo_words.json';

type Word = {word: string; start: number; end: number};
type Stat = {value: number; unit: string; label: string; caption: string};

const DATA = episode as unknown as {
  series: string;
  episode: number;
  total: number;
  title: string;
  titleWords: string[];
  subtitle: string;
  species: string;
  image: string;
  audio: string;
  duration: number;
  stat: Stat;
  timeline: Record<string, number>;
};

const WORDS = (voiceWords as Word[]).slice();
const TL = DATA.timeline;

/* ---------------------------------------------------------------- helpers */

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** 0 -> 1 progress for a reveal that starts at `at` seconds. */
const reveal = (t: number, at: number, dur = 0.9) =>
  interpolate(t, [at, at + dur], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

/** Frames of film grain, baked as an SVG turbulence tile. */
const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>
     <filter id='n'>
       <feTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='3' stitchTiles='stitch'/>
       <feColorMatrix type='saturate' values='0'/>
     </filter>
     <rect width='220' height='220' filter='url(#n)' opacity='0.55'/>
   </svg>`,
)}")`;

/** Group the narration into short caption lines: one line on screen at a time. */
const buildLines = (words: Word[], maxChars = 44, maxWords = 7) => {
  const lines: {start: number; end: number; words: Word[]}[] = [];
  let bucket: Word[] = [];
  let chars = 0;
  const flush = () => {
    if (bucket.length) {
      lines.push({
        start: bucket[0].start,
        end: bucket[bucket.length - 1].end,
        words: bucket,
      });
      bucket = [];
      chars = 0;
    }
  };
  for (const w of words) {
    const len = w.word.replace(/[^\w']/g, '').length;
    if (bucket.length && (chars + len + 1 > maxChars || bucket.length >= maxWords)) flush();
    bucket.push(w);
    chars += len + 1;
    // break on sentence ends so a caption page never stops mid-clause when it can help it
    if (/[.!?]$/.test(w.word) && bucket.length >= 3) flush();
  }
  flush();
  return lines;
};

const LINES = buildLines(WORDS);

/* ---------------------------------------------------------------- layers */

const Backdrop: React.FC<{t: number; frame: number; flash: number; vertical: boolean}> = ({
  t,
  frame,
  flash,
  vertical,
}) => {
  const beat = 1 - Math.exp(-t * 0.55);
  const scale = interpolate(beat, [0, 1], [vertical ? 1.22 : 1.16, 1.035]);
  const driftX = interpolate(beat, [0, 1], [-2.1, 0.7]);
  const driftY = interpolate(beat, [0, 1], [1.4, -1.1]);

  return (
    <div className="plate">
      <Img
        src={staticFile(DATA.image)}
        style={{
          transform: `scale(${scale + flash * 0.03}) translate(${driftX}%, ${driftY}%) rotate(${-0.35 + beat * 0.35}deg)`,
          filter: `brightness(${1 + flash * 0.38}) saturate(${1.04 + flash * 0.3}) contrast(1.04)`,
        }}
      />
      <div className="grade-cool" />
      <div className="grade-warm" style={{opacity: 0.55 + Math.sin(t * 0.7) * 0.12}} />
      <div className="vignette" />
      <div
        className="bloom"
        style={{
          background: `radial-gradient(46% 40% at 58% 46%, rgba(214,248,255,${flash * 0.92}) 0%, rgba(150,215,255,${flash * 0.35}) 42%, rgba(120,200,255,0) 74%)`,
          mixBlendMode: 'screen',
        }}
      />
      <div
        className="bloom"
        style={{
          background: `rgba(226,244,255,${flash * 0.16})`,
          mixBlendMode: 'screen',
        }}
      />
      <div
        className="grain"
        style={{
          backgroundImage: GRAIN,
          backgroundPosition: `${(frame * 17) % 220}px ${(frame * 29) % 220}px`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(120% 90% at 50% 120%, rgba(0,0,0,${0.35 + flash * 0.1}) 0%, rgba(0,0,0,0) 60%)`,
        }}
      />
    </div>
  );
};

const Title: React.FC<{t: number}> = ({t}) => {
  const at = TL.titleAt ?? 0;
  return (
    <h1 className="title">
      {DATA.titleWords.map((word, i) => {
        const p = reveal(t, at + i * 0.13, 1.0);
        const italic = /^(the|an|a)$/i.test(word) ? ' italic' : '';
        return (
          <span
            key={`${word}-${i}`}
            className={`word${italic}`}
            style={{
              opacity: p,
              transform: `translateY(${(1 - p) * 34}px)`,
              filter: `blur(${(1 - p) * 12}px)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </h1>
  );
};

const StatBlock: React.FC<{t: number; flash: number}> = ({t, flash}) => {
  const at = TL.statAt ?? 4;
  const p = reveal(t, at, 1.0);
  const count = interpolate(t, [at, at + 1.25], [0, DATA.stat.value], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      className="stat"
      style={{
        opacity: p,
        transform: `translateY(${(1 - p) * 26}px)`,
        filter: `blur(${(1 - p) * 6}px)`,
      }}
    >
      <div className="stat-value" style={{color: flash > 0.2 ? '#ffffff' : undefined}}>
        {Math.round(count).toLocaleString('en-US')}
      </div>
      <div className="stat-unit">{DATA.stat.unit}</div>
      <div className="stat-label">{DATA.stat.label}</div>
    </div>
  );
};

const Captions: React.FC<{t: number}> = ({t}) => {
  const line = LINES.find((l) => t >= l.start - 0.08 && t <= l.end + 0.5);
  if (!line) return null;
  return (
    <div className="captions">
      <div className="caption-line">
        {line.words.map((w, i) => {
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

/* ---------------------------------------------------------------- scene */

export const AnimalDocumentary: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const vertical = height > width;

  const flashAt = TL.flashAt ?? DATA.duration * 0.55;
  const flash = interpolate(
    t,
    [flashAt, flashAt + 0.07, flashAt + 0.58],
    [0, 1, 0],
    {...clamp, easing: Easing.out(Easing.quad)},
  );
  const outroAt = TL.outroAt ?? DATA.duration - 3;
  const outro = reveal(t, outroAt, 1.2);
  const fade = interpolate(frame, [durationInFrames - 22, durationInFrames - 1], [0, 1], clamp);

  const subtitle = reveal(t, TL.subtitleAt ?? 2.4, 1.0);
  const species = reveal(t, (TL.subtitleAt ?? 2.4) + 0.35, 1.0);
  const ruleP = reveal(t, (TL.titleAt ?? 0) + 0.62, 1.1);

  return (
    <AbsoluteFill className={vertical ? 'doc vertical' : 'doc'}>
      <Audio src={staticFile(DATA.audio)} volume={1} />

      <Backdrop t={t} frame={frame} flash={flash} vertical={vertical} />

      <div className="ui">
        <div>
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
        </div>

        <div className="bottom">
          <div className="headline" style={{opacity: 1}}>
            <Title t={t} />
            <div
              className="rule"
              style={{transform: `scaleX(${ruleP})`, opacity: 0.9}}
            />
            <p
              className="subtitle"
              style={{
                opacity: subtitle,
                transform: `translateY(${(1 - subtitle) * 18}px)`,
                filter: `blur(${(1 - subtitle) * 6}px)`,
              }}
            >
              {DATA.subtitle}
            </p>
            <p className="species" style={{opacity: species * 0.95}}>
              {DATA.species}
            </p>
          </div>

          <StatBlock t={t} flash={flash} />
        </div>
      </div>

      <div className="caption-scrim" />
      <Captions t={t} />

      {/* the last-second vignette pulse on the closing beat */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          boxShadow: `inset 0 0 ${180 + outro * 120}px ${40 + outro * 40}px rgba(0,0,0,${0.45 + outro * 0.2})`,
        }}
      />
      <AbsoluteFill style={{background: '#000', opacity: fade, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
