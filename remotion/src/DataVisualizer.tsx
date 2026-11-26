import React from 'react';
import {
  AbsoluteFill, Audio, Easing, Sequence, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import './data.css';
import beat from '../public/beat.json';

const T = beat.triggers as Record<string, number>;
const FPS = 30;
const at = (s: number) => Math.round(s * FPS);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const easeOut = Easing.out(Easing.cubic);
const easeInOut = Easing.inOut(Easing.cubic);

const BG = '#1E232B';
const TEAL = '#36D3C0';
const CORAL = '#FF6B6B';
const GOLD = '#F4C95D';
const MUTED = '#7E8C9B';
const BASE = 840;
const PX = 5.2;        // pixels per dollar
const BAR_X = 650;
const BAR_W = 220;
const Y100 = BASE - 100 * PX;
const H50 = 50 * PX;
const H75 = 75 * PX;
const H25 = 25 * PX;

const valueLine = (v: number) => BASE - v * PX;

export const DataVisualizer: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const fBar = at(T.bar), fDrop = at(T.drop), fFifty = at(T.fifty);
  const fGain = at(T.gain), fLand = at(T.land);
  const fRule = at(T.rule), fDash = at(T.dashed), fGap = at(T.gap);

  const intro = interpolate(frame, [0, 16], [0, 1], clamp);
  const grow = interpolate(frame, [fBar, fBar + 26], [0, 1], {...clamp, easing: easeOut});
  const drop = interpolate(frame, [fDrop, fDrop + 28], [0, 1], {...clamp, easing: easeInOut});
  const fiftyIn = interpolate(frame, [fFifty, fFifty + 12], [0, 1], clamp);
  const gainSpring = spring({
    frame: Math.max(0, frame - fGain), fps,
    config: {damping: 15, stiffness: 55, mass: 1.15},
  });
  const landP = interpolate(frame, [fLand, fLand + 7, fLand + 22], [0, 1, 0], clamp);
  const ruleIn = interpolate(frame, [fRule, fRule + 16], [0, 1], {...clamp, easing: easeOut});
  const dashIn = interpolate(frame, [fDash, fDash + 34], [0, 1], {...clamp, easing: easeOut});
  const gapIn = interpolate(frame, [fGap, fGap + 18], [0, 1], {...clamp, easing: easeOut});

  const tealH = 100 * PX * grow - 50 * PX * drop;
  const tealTop = BASE - tealH;
  const removedH = 50 * PX * Math.min(1, drop * 1.2);
  const coralX = BAR_X + 230 * drop;
  const coralOpacity = drop > 0 ? Math.max(0, 1 - drop * 1.25) : 0;
  const goldH = H25 * Math.min(1.04, gainSpring);
  const goldTop = BASE - H50 - goldH;
  const goldShake = Math.sin(frame * .9) * 1.4 * landP;
  const dashEndX = 610 + (1490 - 610) * dashIn;
  const show100 = interpolate(drop, [0, .35], [1, 0], clamp);
  const show50 = interpolate(drop, [.55, .9], [0, 1], clamp);

  const rows = [
    {label: 'START', value: '$100', cls: '', show: 1, at: 0},
    {label: 'AFTER −50%', value: '$50', cls: 'coral', show: drop, at: fDrop + 14},
    {label: 'AFTER +50%', value: '$75', cls: 'gold', show: interpolate(frame, [fLand - 10, fLand], [0, 1], clamp), at: fLand - 10},
  ];

  return (
    <AbsoluteFill className="stage">
      <Audio src={staticFile('vo_beat.mp3')} />
      <Sequence from={fDrop} durationInFrames={26}><Audio src={staticFile('sfx/down.wav')} volume={0.45} /></Sequence>
      <Sequence from={fGain} durationInFrames={28}><Audio src={staticFile('sfx/up.wav')} volume={0.42} /></Sequence>
      <Sequence from={fLand} durationInFrames={20}><Audio src={staticFile('sfx/thud.wav')} volume={0.5} /></Sequence>

      <div className="grain" />
      <div className="vignette" />

      <header className="masthead" style={{opacity: intro, transform: `translateY(${(1 - intro) * 14}px)`}}>
        <div className="kicker">BEAT 01 · THE HOOK</div>
        <h1>THE 50% TRAP</h1>
        <p>Why +50% doesn't undo −50%</p>
      </header>

      <div className="rule" style={{opacity: ruleIn, transform: `translateX(${(1 - ruleIn) * -18}px)`}}>
        −50% <span className="neq">+50%</span> ≠ 0%
      </div>

      <svg className="canvas" viewBox="0 0 1920 1080">
        <defs>
          <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#45E0CD" />
            <stop offset="100%" stopColor="#1C9D92" />
          </linearGradient>
          <linearGradient id="coralGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#FF8585" />
            <stop offset="100%" stopColor="#E94F57" />
          </linearGradient>
          <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFDD82" />
            <stop offset="100%" stopColor="#E9AE3D" />
          </linearGradient>
          <filter id="softGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* grid and axis */}
        {[0, 25, 50, 75, 100].map((v) => {
          const y = valueLine(v);
          const on = v <= 50 ? drop > .4 : true;
          return (
            <g key={v} opacity={v === 100 ? 1 : .95}>
              <line x1={570} x2={1500} y1={y} y2={y}
                stroke={v === 0 ? 'rgba(255,255,255,.34)' : 'rgba(255,255,255,.085)'}
                strokeWidth={v === 0 ? 1.5 : 1} />
              <text x={550} y={y + 6} textAnchor="end" fill={v === 100 ? '#A9B6C4' : MUTED}
                fontSize={19} fontWeight={600} letterSpacing={1}>${v}</text>
            </g>
          );
        })}

        {/* baseline glow */}
        <rect x={BAR_X - 16} y={BASE - 5} width={BAR_W + 32} height={10} rx={5}
          fill={TEAL} opacity={0.08 * grow} filter="url(#softGlow)" />

        {/* teal bar */}
        <rect x={BAR_X} y={tealTop} width={BAR_W} height={Math.max(0, tealH)} rx={9}
          fill="url(#tealGrad)" opacity={grow > 0 ? 1 : 0} />
        <rect x={BAR_X} y={tealTop} width={BAR_W} height={Math.min(26, Math.max(0, tealH))}
          rx={9} fill="#7DF0E2" opacity={.22} />

        {/* value labels */}
        <g opacity={show100 * (grow > .15 ? 1 : 0)}>
          <text x={BAR_X + BAR_W / 2} y={Y100 - 26} textAnchor="middle" fill="#EDF3F7"
            fontSize={58} fontWeight={800} letterSpacing={-1}>$100</text>
        </g>
        <g opacity={show50}>
          <text x={BAR_X + BAR_W / 2} y={BASE - H50 - 26} textAnchor="middle" fill="#EDF3F7"
            fontSize={54} fontWeight={800} letterSpacing={-1}>$50</text>
        </g>

        {/* coral slice sliding off */}
        {coralOpacity > 0 && (
          <g opacity={coralOpacity}>
            <rect x={coralX} y={Y100} width={BAR_W} height={removedH} rx={9} fill="url(#coralGrad)" />
            <text x={coralX + BAR_W / 2} y={Y100 + removedH / 2 + 6} textAnchor="middle"
              fill="#FFF4F1" fontSize={36} fontWeight={800}>−50%</text>
          </g>
        )}

        {/* gold stack */}
        <g opacity={gainSpring > .01 ? 1 : 0} filter="url(#softGlow)">
          <rect x={BAR_X} y={goldTop + goldShake} width={BAR_W} height={Math.max(0, goldH)} rx={8}
            fill="url(#goldGrad)" />
          <text x={BAR_X + BAR_W / 2} y={goldTop + H25 / 2 + 8 + goldShake} textAnchor="middle"
            fill="#3A2A08" fontSize={32} fontWeight={800}>+50%</text>
        </g>
        <g opacity={interpolate(gainSpring, [.55, .9], [0, 1], clamp)}>
          <text x={BAR_X + BAR_W / 2} y={BASE - H75 - 24 + goldShake} textAnchor="middle"
            fill="#FFE6A6" fontSize={58} fontWeight={800} letterSpacing={-1}>$75</text>
        </g>

        {/* original $100 dashed line */}
        <g opacity={dashIn > 0 ? 1 : 0}>
          <line x1={610} x2={dashEndX} y1={Y100} y2={Y100}
            stroke="#F4F7FA" strokeWidth={2.6} strokeDasharray="13 11" opacity={.92} />
          <text x={dashEndX + 16} y={Y100 + 7} fill="#DCE5ED" fontSize={20} fontWeight={700}
            letterSpacing={2} opacity={interpolate(dashIn, [.7, 1], [0, 1], clamp)}>ORIGINAL $100</text>
        </g>

        {/* $25 gap bracket */}
        <g opacity={gapIn}>
          <path d={`M 1042 ${Y100} L 1042 ${BASE - H75}`} stroke={GOLD} strokeWidth={2.5}
            fill="none" strokeDasharray="6 6" />
          <path d={`M 1030 ${Y100} L 1054 ${Y100} M 1030 ${BASE - H75} L 1054 ${BASE - H75}`}
            stroke={GOLD} strokeWidth={2.5} />
          <text x={1068} y={(Y100 + BASE - H75) / 2 + 8} fill={GOLD} fontSize={28} fontWeight={800}
            letterSpacing={1}>$25 GAP</text>
        </g>

        {/* footer ticker */}
        <text x={610} y={890} fill={MUTED} fontSize={14} fontWeight={600} letterSpacing={2.2}>
          VALUE OF A $100 INVESTMENT
        </text>
      </svg>

      <div className="info">
        {rows.map((r) => (
          <div className="info-row" key={r.label}
            style={{opacity: r.show, transform: `translateX(${(1 - Math.min(1, r.show)) * 12}px)`}}>
            <span className="lab">{r.label}</span>
            <span className={`val ${r.cls}`}>{r.value}</span>
          </div>
        ))}
        <div className="info-note" style={{opacity: gapIn}}>
          A 50% fall needs a <b>100% gain</b> to get back to $100.
        </div>
      </div>

      <div className="footer">
        <span className="dot" /> KINETIC DATA / BEAT 01
        <span className="sep" /> 100 → 50 → 75
      </div>
    </AbsoluteFill>
  );
};
