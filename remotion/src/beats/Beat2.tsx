import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import beat from '../../public/beat.json';

const B = beat.beats[1];
const T = B.triggers as unknown as Record<string, number>;
const F = (s: number) => Math.round((s - B.start) * 30);
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const Beat2: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const local = frame - B.start * 30;
  const fSplit = F(T.split), fLose = F(T.lose), fNine = F(T.nine), fNarrow = F(T.narrow), fBase = F(T.base);
  const lost = interpolate(frame, [fLose, fLose + 18], [0, 1], clamp);
  const nine = interpolate(frame, [fNine, fNine + 14], [0, 1], clamp);
  const zoom = spring({frame: Math.max(0, frame - fNarrow), fps, config: {damping: 14, stiffness: 65}});
  const final = interpolate(frame, [fBase - 12, fBase], [0, 1], clamp);
  const appear = interpolate(local, [0, 14], [0, 1], clamp);

  return (
    <div className="split" style={{opacity: appear}}>
      <section className="pane">
        <div className="pane-kicker">THE SAME $100</div>
        <div className="pane-title">10 blocks of $10</div>
        <div className="ten-grid">
          {Array.from({length: 10}).map((_, i) => (
            <div key={i} className="ten-block" style={{
              opacity: i === 0 ? 1 - lost * .95 : 1,
              transform: i === 0 ? `translate(-${lost * 170}px, ${lost * 60}px) rotate(${lost * -14}deg)` : undefined,
              background: i === 0 ? `linear-gradient(180deg, #FF8585, #E94F57)` : undefined,
            }}>
              <span>$10</span>
            </div>
          ))}
        </div>
        <div className="pane-note" style={{opacity: lost}}>
          One block leaves → <b className="coral-text">$90 remains</b>
        </div>
      </section>

      <section className="pane pane-right">
        <div className="zoom-wrap" style={{transform: `scale(${.72 + zoom * .28})`, opacity: Math.min(1, zoom * 1.4)}}>
          <div className="zoom-ring"><span>$90</span></div>
          <div className="zoom-handle" />
          <div className="loss-chip">−$10</div>
        </div>
        <div className="gain-box" style={{opacity: nine, transform: `translateY(${(1 - nine) * 16}px)`}}>
          <div className="gain-block"><span>+$9</span></div>
          <div className="gain-copy">10% of $90<br /><small>only 9% of $100</small></div>
        </div>
        <div className="total-row" style={{opacity: final}}>
          <span>NEW TOTAL</span><b>$99</b>
        </div>
        <div className="pane-note narrow-note" style={{opacity: zoom}}>
          The recovery block is already narrower than the one that left.
        </div>
      </section>
    </div>
  );
};
