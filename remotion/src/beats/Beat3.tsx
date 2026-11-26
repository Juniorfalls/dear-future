import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import beat from '../../public/beat.json';

const B = beat.beats[2];
const T = B.triggers as unknown as Record<string, number>;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const ROWS = [
  {key: 'ten', loss: 10, gain: '11.1%', coral: 12, gold: 30},
  {key: 't25', loss: 25, gain: '33.3%', coral: 22, gold: 48},
  {key: 'fifty', loss: 50, gain: '100%', coral: 40, gold: 74},
  {key: 'eighty', loss: 80, gain: '400%', coral: 62, gold: 100},
];

export const Beat3: React.FC = () => {
  const frame = useCurrentFrame();
  const local = frame - B.start * 30;
  const appear = interpolate(local, [0, 14], [0, 1], clamp);

  return (
    <div className="ladder" style={{opacity: appear}}>
      <div className="ladder-legend">
        <span><i className="swatch coral" /> DROP</span>
        <span><i className="swatch gold" /> GAIN NEEDED TO RECOVER</span>
      </div>
      {ROWS.map((r, i) => {
        const f = Math.round((T[r.key] - B.start) * 30);
        const p = interpolate(frame, [f, f + 20], [0, 1], clamp);
        return (
          <div className="ladder-row" key={r.key} style={{opacity: p, transform: `translateY(${(1 - p) * 16}px)`}}>
            <div className="row-label">−{r.loss}%</div>
            <div className="row-track">
              <div className="row-bar coral" style={{width: `${r.coral * p}%`}}>
                <span>−{r.loss}%</span>
              </div>
              <div className="row-bar gold" style={{width: `${r.gold * p}%`}}>
                <span>+{r.gain}</span>
              </div>
            </div>
            <div className="row-arrow">→</div>
          </div>
        );
      })}
      <div className="ladder-note" style={{opacity: interpolate(frame, [Math.round((T.smaller - B.start) * 30), Math.round((T.smaller - B.start) * 30) + 16], [0, 1], clamp)}}>
        The smaller the base, the larger the climb.
      </div>
    </div>
  );
};
