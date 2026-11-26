import React from 'react';
import {interpolate, Easing} from 'remotion';

const ease = Easing.out(Easing.cubic);

export const BeatFrame: React.FC<{
  index: number;
  kicker: string;
  title: string;
  subtitle: string;
  local: number;
  bare?: boolean;
  children: React.ReactNode;
}> = ({index, kicker, title, subtitle, local, bare, children}) => {
  const inn = interpolate(local, [0, .55], [0, 1], {extrapolateRight: 'clamp', easing: ease});
  return (
    <>
      <header className="masthead" style={{opacity: inn, transform: `translateY(${(1 - inn) * 18}px)`}}>
        <div className="kicker">BEAT 0{index} · {kicker}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </header>
      {bare ? children : <div className="content">{children}</div>}
      <div className="footer">
        <span className="dot" /> KINETIC DATA / BEAT 0{index}
        <span className="sep" /> {title}
      </div>
      <div className="beat-fade" style={{opacity: interpolate(local, [0, .28], [1, 0], {extrapolateRight: 'clamp'})}} />
    </>
  );
};
