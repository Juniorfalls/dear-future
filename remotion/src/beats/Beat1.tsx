import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import beat from '../../public/beat.json';

const T = beat.beats[0].triggers as unknown as Record<string, number>;
const FPS = 30;
const at = (s: number) => Math.round(s * FPS);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);
const easeInOut = (x: number) => x < .5 ? 4*x*x*x : 1 - Math.pow(-2*x+2,3)/2;

const BASE = 840, PX = 5.2, BAR_X = 650, BAR_W = 220;
const Y100 = BASE - 100 * PX, H50 = 50 * PX, H75 = 75 * PX, H25 = 25 * PX;
const valueLine = (v: number) => BASE - v * PX;

export const Beat1: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const fDrop = at(T.drop), fFifty = at(T.fifty), fGain = at(T.gain);
  const fLand = at(T.land), fRule = at(T.rule), fDash = at(T.dashed), fGap = at(T.gap);

  const grow = easeOut(interpolate(frame, [at(T.bar), at(T.bar) + 26], [0, 1], clamp));
  const drop = easeInOut(interpolate(frame, [fDrop, fDrop + 28], [0, 1], clamp));
  const fiftyIn = interpolate(frame, [fFifty, fFifty + 12], [0, 1], clamp);
  const gainSpring = spring({frame: Math.max(0, frame - fGain), fps, config: {damping: 15, stiffness: 55, mass: 1.15}});
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

  return (
    <div className="b1-canvas">
      <div className="rule" style={{opacity: ruleIn, transform: `translateX(${(1 - ruleIn) * -18}px)`}}>
        −50% <span className="neq">+50%</span> ≠ 0%
      </div>
      <svg className="canvas" viewBox="0 0 1920 1080">
        <defs>
          <linearGradient id="tealGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#45E0CD" /><stop offset="100%" stopColor="#1C9D92" />
          </linearGradient>
          <linearGradient id="coralGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#FF8585" /><stop offset="100%" stopColor="#E94F57" />
          </linearGradient>
          <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFDD82" /><stop offset="100%" stopColor="#E9AE3D" />
          </linearGradient>
          <filter id="softGlow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="14" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {[0, 25, 50, 75, 100].map((v) => {
          const y = valueLine(v);
          return (
            <g key={v}>
              <line x1={570} x2={1500} y1={y} y2={y} stroke={v === 0 ? 'rgba(255,255,255,.34)' : 'rgba(255,255,255,.085)'} strokeWidth={v === 0 ? 1.5 : 1} />
              <text x={550} y={y + 6} textAnchor="end" fill={v === 100 ? '#A9B6C4' : '#7E8C9B'} fontSize={19} fontWeight={600} letterSpacing={1}>${v}</text>
            </g>
          );
        })}
        <rect x={BAR_X - 16} y={BASE - 5} width={BAR_W + 32} height={10} rx={5} fill="#36D3C0" opacity={0.08 * grow} filter="url(#softGlow)" />
        <rect x={BAR_X} y={tealTop} width={BAR_W} height={Math.max(0, tealH)} rx={9} fill="url(#tealGrad)" opacity={grow > 0 ? 1 : 0} />
        <rect x={BAR_X} y={tealTop} width={BAR_W} height={Math.min(26, Math.max(0, tealH))} rx={9} fill="#7DF0E2" opacity={.22} />
        <g opacity={show100 * (grow > .15 ? 1 : 0)}>
          <text x={BAR_X + BAR_W / 2} y={Y100 - 26} textAnchor="middle" fill="#EDF3F7" fontSize={58} fontWeight={800}>$100</text>
        </g>
        <g opacity={show50}>
          <text x={BAR_X + BAR_W / 2} y={BASE - H50 - 26} textAnchor="middle" fill="#EDF3F7" fontSize={54} fontWeight={800}>$50</text>
        </g>
        {coralOpacity > 0 && (
          <g opacity={coralOpacity}>
            <rect x={coralX} y={Y100} width={BAR_W} height={removedH} rx={9} fill="url(#coralGrad)" />
            <text x={coralX + BAR_W / 2} y={Y100 + removedH / 2 + 6} textAnchor="middle" fill="#FFF4F1" fontSize={36} fontWeight={800}>−50%</text>
          </g>
        )}
        <g opacity={gainSpring > .01 ? 1 : 0} filter="url(#softGlow)">
          <rect x={BAR_X} y={goldTop + goldShake} width={BAR_W} height={Math.max(0, goldH)} rx={8} fill="url(#goldGrad)" />
          <text x={BAR_X + BAR_W / 2} y={goldTop + H25 / 2 + 8 + goldShake} textAnchor="middle" fill="#3A2A08" fontSize={32} fontWeight={800}>+50%</text>
        </g>
        <g opacity={interpolate(gainSpring, [.55, .9], [0, 1], clamp)}>
          <text x={BAR_X + BAR_W / 2} y={BASE - H75 - 24 + goldShake} textAnchor="middle" fill="#FFE6A6" fontSize={58} fontWeight={800}>$75</text>
        </g>
        <g opacity={dashIn > 0 ? 1 : 0}>
          <line x1={610} x2={dashEndX} y1={Y100} y2={Y100} stroke="#F4F7FA" strokeWidth={2.6} strokeDasharray="13 11" opacity={.92} />
          <text x={dashEndX + 16} y={Y100 + 7} fill="#DCE5ED" fontSize={20} fontWeight={700} letterSpacing={2} opacity={interpolate(dashIn, [.7, 1], [0, 1], clamp)}>ORIGINAL $100</text>
        </g>
        <g opacity={gapIn}>
          <path d={`M 1042 ${Y100} L 1042 ${BASE - H75}`} stroke="#F4C95D" strokeWidth={2.5} fill="none" strokeDasharray="6 6" />
          <path d={`M 1030 ${Y100} L 1054 ${Y100} M 1030 ${BASE - H75} L 1054 ${BASE - H75}`} stroke="#F4C95D" strokeWidth={2.5} />
          <text x={1068} y={(Y100 + BASE - H75) / 2 + 8} fill="#F4C95D" fontSize={28} fontWeight={800} letterSpacing={1}>$25 GAP</text>
        </g>
        <text x={610} y={890} fill="#7E8C9B" fontSize={14} fontWeight={600} letterSpacing={2.2}>VALUE OF A $100 INVESTMENT</text>
      </svg>
      <div className="info">
        <div className="info-row" style={{opacity: 1}}><span className="lab">START</span><span className="val">$100</span></div>
        <div className="info-row" style={{opacity: drop}}><span className="lab">AFTER −50%</span><span className="val coral">$50</span></div>
        <div className="info-row" style={{opacity: interpolate(frame, [fLand - 10, fLand], [0, 1], clamp)}}><span className="lab">AFTER +50%</span><span className="val gold">$75</span></div>
        <div className="info-note" style={{opacity: gapIn}}>A 50% fall needs a <b>100% gain</b> to get back to $100.</div>
      </div>
    </div>
  );
};
