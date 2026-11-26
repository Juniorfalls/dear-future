import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import beat from '../../public/beat.json';

const B = beat.beats[3];
const T = B.triggers as unknown as Record<string, number>;
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const Beat4: React.FC = () => {
  const frame = useCurrentFrame();
  const local = frame - B.start * 30;
  const appear = interpolate(local, [0, 14], [0, 1], clamp);
  const f = (k: string) => Math.round((T[k] - B.start) * 30);
  const off = interpolate(frame, [f('off'), f('off') + 16], [0, 1], clamp);
  const tax = interpolate(frame, [f('tax'), f('tax') + 16], [0, 1], clamp);
  const pay = interpolate(frame, [f('pay'), f('pay') + 16], [0, 1], clamp);
  const pathA = interpolate(frame, [f('pathA'), f('pathA') + 18], [0, 1], clamp);
  const pathB = interpolate(frame, [f('pathB'), f('pathB') + 18], [0, 1], clamp);
  const order = interpolate(frame, [f('order'), f('order') + 16], [0, 1], clamp);

  return (
    <div className="cards" style={{opacity: appear}}>
      <section className="card">
        <div className="card-kicker">TRAP 01</div>
        <h3>The Price Tag</h3>
        <div className="flow">
          <div className="stage"><small>PRICE</small><b>$100</b></div>
          <div className="flow-arrow" style={{opacity: off}}><span>−20%</span>→</div>
          <div className="stage" style={{opacity: off}}><small>AFTER OFF</small><b className="coral-text">$80</b></div>
          <div className="flow-arrow" style={{opacity: tax}}><span>+20% tax</span>→</div>
          <div className="stage" style={{opacity: pay}}><small>YOU PAY</small><b className="gold-text">$96</b></div>
        </div>
        <div className="mini-bars" style={{opacity: pay}}>
          {[{l: 'ORIGINAL', v: '$100', w: 100, c: 'teal'}, {l: 'AFTER −20%', v: '$80', w: 80, c: 'coral'}, {l: 'AFTER +20% TAX', v: '$96', w: 96, c: 'gold'}].map((b) => (
            <div className="mini-row" key={b.l}>
              <span>{b.l}</span>
              <div className="mini-track"><div className={`mini-fill ${b.c}`} style={{width: `${b.w}%`}} /></div>
              <b>{b.v}</b>
            </div>
          ))}
        </div>
        <div className="card-note" style={{opacity: pay}}>
          Tax applies to $80, not $100. The 20% is worth less on the way back up.
        </div>
      </section>

      <section className="card">
        <div className="card-kicker">TRAP 02</div>
        <h3>The Rollercoaster</h3>
        <div className="path">
          <div className="path-head"><span className="path-tag teal-tag">PATH A</span><b style={{opacity: pathA}}>$110.25</b></div>
          <div className="path-track">
            <span className="node" style={{opacity: pathA}}>+5%</span>
            <span className="path-line" style={{width: `${pathA * 100}%`}} />
            <span className="node" style={{opacity: pathA}}>+5%</span>
          </div>
          <div className="path-sub">two small gains, compounded</div>
        </div>
        <div className="path">
          <div className="path-head"><span className="path-tag coral-tag">PATH B</span><b className="coral-text" style={{opacity: pathB}}>$75</b></div>
          <div className="path-track">
            <span className="node" style={{opacity: pathB}}>+50%</span>
            <span className="path-line coral" style={{width: `${pathB * 100}%`}} />
            <span className="node" style={{opacity: pathB}}>−50%</span>
          </div>
          <div className="path-sub">one big gain, then one big loss</div>
        </div>
        <div className="end-bars" style={{opacity: order}}>
          <div className="end-row"><span>PATH A</span><div className="mini-track"><div className="mini-fill teal" style={{width: '100%'}} /></div><b>$110.25</b></div>
          <div className="end-row"><span>PATH B</span><div className="mini-track"><div className="mini-fill coral" style={{width: '68%'}} /></div><b>$75</b></div>
        </div>
        <div className="card-note" style={{opacity: order}}>Same two moves. Different order. Different base.</div>
      </section>
    </div>
  );
};
