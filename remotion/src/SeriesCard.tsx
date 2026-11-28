import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import './animal.css';
import castJson from '../public/cast.json';

type Animal = {rank: number; title: string; subtitle: string; species: string; image: string};

const CAST = castJson as unknown as Animal[];
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'>
     <filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.82' numOctaves='3' stitchTiles='stitch'/>
       <feColorMatrix type='saturate' values='0'/></filter>
     <rect width='220' height='220' filter='url(#n)' opacity='0.55'/></svg>`,
)}")`;

const rise = (t: number, at: number, dur = 0.85) =>
  interpolate(t, [at, at + dur], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

const CardBackdrop: React.FC<{image: string; frame: number; dim: number}> = ({image, frame, dim}) => (
  <AbsoluteFill>
    <Img
      src={staticFile(image)}
      style={{
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        objectPosition: '62% 50%',
        opacity: dim,
        filter: 'saturate(.85) contrast(1.05)',
        transform: `scale(${1.06 + (frame / 2400) * 0.04})`,
      }}
    />
    <AbsoluteFill
      style={{
        background:
          'radial-gradient(ellipse 70% 60% at 50% 45%, rgba(0,0,0,.35) 0%, rgba(0,0,0,.82) 78%, rgba(0,0,0,.96) 100%)',
      }}
    />
    {/* keeps the brightest part of the still from competing with the card type */}
    <AbsoluteFill
      style={{background: 'radial-gradient(ellipse 52% 46% at 50% 52%, rgba(0,0,0,.62) 0%, rgba(0,0,0,0) 72%)'}}
    />
    <div
      className="grain"
      style={{
        backgroundImage: GRAIN,
        backgroundPosition: `${(frame * 17) % 220}px ${(frame * 29) % 220}px`,
      }}
    />
  </AbsoluteFill>
);

export const SeriesIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const kicker = rise(t, 0.18);
  const title = rise(t, 0.55, 1.05);
  const sub = rise(t, 1.1, 1.0);
  const rule = rise(t, 0.3, 1.2);

  return (
    <AbsoluteFill className="doc">
      <CardBackdrop image={CAST[0].image} frame={frame} dim={0.34} />
      <div className="card-body">
        <div className="card-kicker" style={{opacity: kicker, letterSpacing: `${5 + (1 - kicker) * 10}px`}}>
          A natural history of the impossible
        </div>
        <div className="card-rule" style={{transform: `scaleX(${rule})`, opacity: 0.9}} />
        <h1
          className="card-title"
          style={{
            opacity: title,
            transform: `translateY(${(1 - title) * 22}px)`,
            filter: `blur(${(1 - title) * 10}px)`,
          }}
        >
          5 Animals With
          <br />
          Impossible Superpowers
        </h1>
        <p className="card-sub" style={{opacity: sub}}>
          Five bodies. Five rules of physics, broken.
        </p>
      </div>
    </AbsoluteFill>
  );
};

export const SeriesOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const t = frame / fps;
  const head = rise(t, 0.15, 0.9);
  const wordmark = rise(t, 3.4, 1.0);
  const fade = interpolate(frame, [durationInFrames - 24, durationInFrames - 1], [0, 1], clamp);

  return (
    <AbsoluteFill className="doc">
      <CardBackdrop image={CAST[4].image} frame={frame} dim={0.22} />
      <div className="card-body">
        <div className="card-kicker" style={{opacity: head}}>
          {frame < 20 ? '' : 'The cast'}
        </div>
        <div className="card-rule" style={{transform: `scaleX(${rise(t, 0.2, 1.0)})`, width: '460px'}} />
        <div className="cast">
          {CAST.map((a, i) => {
            const p = rise(t, 0.45 + i * 0.42, 0.9);
            return (
              <div key={a.rank} className="cast-item" style={{opacity: p, transform: `translateY(${(1 - p) * 26}px)`}}>
                <div className="cast-thumb">
                  <Img
                    src={staticFile(a.image)}
                    style={{
                      width: '100%',
                      height: '100%',
                      objectFit: 'cover',
                      transform: `scale(${1.12 - p * 0.06})`,
                    }}
                  />
                  <span className="cast-rank">{String(a.rank).padStart(2, '0')}</span>
                </div>
                <div className="cast-name">{a.title.replace(/^The /, '')}</div>
                <div className="cast-species">{a.species}</div>
              </div>
            );
          })}
        </div>
        <div className="card-wordmark" style={{opacity: wordmark, transform: `translateY(${(1 - wordmark) * 14}px)`}}>
          <span className="brand-rule" />
          IMPOSSIBLE SUPERPOWERS
        </div>
      </div>
      <AbsoluteFill style={{background: '#000', opacity: fade, pointerEvents: 'none'}} />
    </AbsoluteFill>
  );
};
