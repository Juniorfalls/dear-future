import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import beat from '../../public/beat.json';

const B = beat.beats[4];
const T = B.triggers as unknown as Record<string, number>;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const Beat5: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - B.start * 30;
  const f = (k: string) => Math.round((T[k] - B.start) * 30);
  const appear = interpolate(local, [0, 14], [0, 1], clamp);
  const smallDrop = spring({frame: Math.max(0, frame - f('small')), fps, config: {damping: 12, stiffness: 70}});
  const goldDrop = spring({frame: Math.max(0, frame - f('t50')), fps, config: {damping: 13, stiffness: 55, mass: 1.1}});
  const balance = interpolate(frame, [f('t50'), f('t50') + 30], [0, 1], clamp);
  const angle = -8 * (1 - balance);
  const stat50 = interpolate(frame, [f('t50'), f('t50') + 16], [0, 1], clamp);
  const stat80 = interpolate(frame, [f('t80'), f('t80') + 16], [0, 1], clamp);
  const protect = interpolate(frame, [f('protect'), f('protect') + 18], [0, 1], clamp);

  return (
    <div className="seesaw" style={{opacity: appear}}>
      <svg className="seesaw-svg" viewBox="0 0 1100 520">
        <defs>
          <radialGradient id="coralBall" cx="35%" cy="30%">
            <stop offset="0%" stopColor="#FF9A9A" /><stop offset="100%" stopColor="#E24F5A" />
          </radialGradient>
          <radialGradient id="goldBall" cx="35%" cy="28%">
            <stop offset="0%" stopColor="#FFE6A3" /><stop offset="100%" stopColor="#D89826" />
          </radialGradient>
        </defs>
        <g transform={`rotate(${angle} 600 300)`}>
          <rect x={150} y={292} width={900} height={16} rx={8} fill="#B8C4CF" />
          <circle cx={600} cy={300} r={11} fill="#EDF3F7" />
          <g transform={`translate(0 ${(1 - smallDrop) * -170})`} opacity={smallDrop > .02 ? 1 : 0}>
            <circle cx={255} cy={235} r={34} fill="url(#coralBall)" />
            <text x={255} y={244} textAnchor="middle" fill="#2A0C0E" fontSize={21} fontWeight={800}>−50%</text>
          </g>
          <g transform={`translate(0 ${(1 - Math.min(1, goldDrop)) * -240})`} opacity={goldDrop > .02 ? 1 : 0}>
            <circle cx={925} cy={170} r={104 * Math.min(1.05, goldDrop)} fill="url(#goldBall)" />
            <text x={925} y={182} textAnchor="middle" fill="#3A2A08" fontSize={44} fontWeight={800}>+100%</text>
          </g>
        </g>
        <path d="M 600 300 L 520 470 L 680 470 Z" fill="#33414E" stroke="#566776" strokeWidth={3} />
        <text x={600} y={500} textAnchor="middle" fill="#9BA9B7" fontSize={19} fontWeight={700} letterSpacing={3}>SMALLER BASE</text>
        <text x={255} y={322} textAnchor="middle" fill="#FF8A8A" fontSize={17} fontWeight={700} letterSpacing={2}>LOSS</text>
        <text x={925} y={322} textAnchor="middle" fill="#F4C95D" fontSize={17} fontWeight={700} letterSpacing={2}>REQUIRED GAIN</text>
      </svg>
      <div className="seesaw-copy">
        <div className="seesaw-lead">A loss is measured from the old base.<br />The recovery is measured from the <b>smaller</b> one.</div>
        <div className="seesaw-stats">
          <div><span>−10%</span><b>+11.1%</b></div>
          <div style={{opacity: stat50}}><span>−50%</span><b>+100%</b></div>
          <div style={{opacity: stat80}}><span>−80%</span><b>+400%</b></div>
        </div>
        <div className="seesaw-close" style={{opacity: protect}}>PROTECT THE BASE. PROTECT THE COMPOUND.</div>
      </div>
    </div>
  );
};
