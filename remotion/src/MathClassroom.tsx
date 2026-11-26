import React, {useEffect, useRef, useState} from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import katex from 'katex';
import {createTikTokStyleCaptions, type Caption} from '@remotion/captions';
import 'katex/dist/katex.min.css';
import './styles.css';
import episode from '../public/episode.json';
import voiceWords from '../public/vo_words.json';
import lipsync from '../public/lipsync.json';

type Line = {id: string; latex: string; plain: string; at: number};

const WALK = Array.from({length: 6}, (_, i) => `characters/teacher_walk_${i}.png`);
const TYPE_SECONDS: Record<string, number> = {l1: 1.9, l2: 1.35, l3: 1.05};
const LINE_TOP: Record<string, number> = {l1: 132, l2: 268, l3: 360};
const WORDS = voiceWords as {word: string; start: number; end: number}[];
const speakingAt = (t: number) =>
  WORDS.some((w) => t >= w.start - 0.05 && t <= w.end + 0.26);

const MOUTH: Record<string, number> = {A: 0, B: 1, C: 2, D: 3, E: 4, F: 5, G: 2, H: 3, X: 2};
const CUES = (lipsync as {mouthCues: {start: number; end: number; value: string}[]}).mouthCues;
const mouthAt = (t: number) => {
  const c = CUES.find((cue) => t >= cue.start && t < cue.end);
  return MOUTH[c?.value ?? 'X'] ?? 2;
};

const CAPTION_INPUT: Caption[] = WORDS.map((w, i) => ({
  text: (i === 0 ? '' : ' ') + w.word,
  startMs: Math.round(w.start * 1000),
  endMs: Math.round(w.end * 1000),
  timestampMs: Math.round(((w.start + w.end) / 2) * 1000),
  confidence: null,
}));
const {pages: CAPTION_PAGES} = createTikTokStyleCaptions({
  captions: CAPTION_INPUT,
  combineTokensWithinMilliseconds: 1750,
  breakOnSilenceAfterMilliseconds: 350,
});

const TypedEquation: React.FC<{
  line: Line;
  time: number;
  frame: number;
  top: number;
  hero?: boolean;
}> = ({line, time, frame, top, hero}) => {
  const clipRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const duration = TYPE_SECONDS[line.id] ?? 1.4;
  const total = Array.from(line.plain).length;
  const pRaw = (time - line.at) / duration;
  const p = Math.max(0, Math.min(1, pRaw));
  const shown = Math.min(total, Math.ceil(p * total));
  const frac = shown / total;

  useEffect(() => {
    const measure = () => {
      if (clipRef.current) setWidth(clipRef.current.getBoundingClientRect().width);
    };
    measure();
    const raf = requestAnimationFrame(measure);
    document.fonts?.ready.then(measure).catch(() => undefined);
    return () => cancelAnimationFrame(raf);
  }, [line.latex]);

  const started = time >= line.at;
  const writing = p > 0 && p < 1;
  const handX = frac * width - 26;
  const handTilt = -8 + Math.sin(frame * 1.15) * 2.5;
  const html = katex.renderToString(line.latex, {displayMode: true, throwOnError: false});

  return (
    <div className={`eq-wrap${hero ? ' hero' : ''}`} style={{top, opacity: started ? 1 : 0}}>
      <div
        ref={clipRef}
        className="eq-clip"
        style={{clipPath: `inset(-45% ${Math.max(0, (1 - frac) * 100)}% -45% 0)`}}
        dangerouslySetInnerHTML={{__html: html}}
      />
      {writing && width > 0 ? (
        <Img
          src={staticFile('chalk_hand.png')}
          className="chalk-hand"
          style={{left: handX, top: -52, transform: `rotate(${handTilt}deg)`}}
        />
      ) : null}
    </div>
  );
};

const Desk: React.FC<{left: number; student: string; phase: number; time: number}> = ({
  left,
  student,
  phase,
  time,
}) => {
  const bob = Math.sin(time * 1.7 + phase) * 2.4;
  return (
    <>
      <Img
        src={staticFile(student)}
        className="student"
        style={{left: left + 44, bottom: 94 + bob}}
      />
      <div className="desk" style={{left}}>
        <div className="desk-shadow" />
        <div className="desk-back" />
        <div className="desk-top" />
        <div className="desk-leg l" />
        <div className="desk-leg r" />
      </div>
    </>
  );
};

const Subtitles: React.FC<{time: number; frame: number}> = ({time}) => {
  const ms = time * 1000;
  const page = CAPTION_PAGES.find((p) => ms >= p.startMs && ms < p.startMs + p.durationMs);
  if (!page) return null;
  return (
    <div className="caption-wrap">
      <div className="caption-plate">
        {page.tokens.map((tok, i) => {
          const active = ms >= tok.fromMs && ms <= tok.toMs;
          return (
            <span key={i} className={active ? 'caption-token active' : 'caption-token'}>
              {tok.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const MathClassroom: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const walking = t < 1.55;
  const talking = !walking && speakingAt(t);
  const mouthSrc = `characters/mouth_v3_${mouthAt(t)}.png`;
  const teacherSrc = WALK[Math.floor(t * 12) % 6];

  const walkX = interpolate(t, [0, 1.55], [-430, 118], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const teacherX = walking ? walkX : 118;
  const teacherBob = walking
    ? Math.abs(Math.sin(t * 9.5)) * 9
    : Math.sin(t * 1.8) * 2.2;

  const zoom = interpolate(frame, [0, 449], [1, 1.045]);
  const driftY = interpolate(frame, [0, 449], [0, -10]);

  return (
    <AbsoluteFill className="room">
      <Audio src={staticFile('vo.mp3')} />
      <div className="camera" style={{transform: `scale(${zoom}) translateY(${driftY}px)`}}>
        <div className="wall-accent" />
        <div className="baseboard" />
        <div className="floor" />

        <div className="clock"><div className="clock-pin" /></div>
        <div className="window" />
        <div className="sill" />

        <div className="board">
          <div className="board-title">SOLVING FOR X</div>
          {(episode.lines as Line[]).map((line) => (
            <TypedEquation
              key={line.id}
              line={line}
              time={t}
              frame={frame}
              top={LINE_TOP[line.id] ?? 180}
              hero={line.id === 'l3'}
            />
          ))}
          <div className="tray">
            <div className="chalk-stick c1" />
            <div className="chalk-stick c2" />
            <div className="chalk-stick c3" />
          </div>
        </div>

        {walking ? (
          <Img
            src={staticFile(teacherSrc)}
            className="teacher"
            style={{left: teacherX, bottom: 38 + teacherBob}}
          />
        ) : (
          <div className="teacher-wrap" style={{left: teacherX, bottom: 38 + teacherBob}}>
            <Img src={staticFile('characters/teacher_point.png')} className="teacher-body" />
            <Img
              src={staticFile(mouthSrc)}
              className={`teacher-mouth${talking ? ' is-talking' : ''}`}
            />
          </div>
        )}

        <Desk left={648} student="characters/student_1.png" phase={0.4} time={t} />
        <Desk left={984} student="characters/student_2.png" phase={2.2} time={t} />
        <Desk left={1320} student="characters/student_3.png" phase={4.1} time={t} />
      </div>
      <Subtitles time={t} frame={frame} />
    </AbsoluteFill>
  );
};
