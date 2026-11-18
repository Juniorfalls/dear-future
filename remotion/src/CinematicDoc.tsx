import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadCinzel} from '@remotion/google-fonts/Cinzel';
import {loadFont as loadMerriweather} from '@remotion/google-fonts/Merriweather';
import type {CinematicProps, Scene} from './types';

const cinzel = loadCinzel('normal', {weights: ['400', '600'], subsets: ['latin']});
const merriweather = loadMerriweather('normal', {weights: ['300', '400'], subsets: ['latin']});

const INK = '#F6F2EA';
const SHADE = 'rgba(4, 5, 8, ';

type SceneProps = {
  scene: Scene;
  index: number;
  sceneFrames: number;
  overlap: number;
};

/**
 * One shot: full-bleed still with a slow Ken Burns push, plus the caption
 * lower third. Incoming scenes fade in on top of the outgoing one (which stays
 * opaque underneath), so a crossfade never dips to black in the middle.
 */
const CinematicScene: React.FC<SceneProps> = ({scene, index, sceneFrames, overlap}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Ken Burns: slow, linear push so it reads as a camera move, not a zoom effect.
  const scale = interpolate(frame, [0, sceneFrames], [1.05, 1.24], {
    easing: Easing.inOut(Easing.ease),
    extrapolateRight: 'clamp',
  });
  const panX = interpolate(frame, [0, sceneFrames], [-1.7, 1.7], {extrapolateRight: 'clamp'});
  const panY = interpolate(frame, [0, sceneFrames], [1.0, -1.0], {extrapolateRight: 'clamp'});

  // Crossfade in; the previous scene stays fully opaque behind this one.
  const reveal =
    index === 0
      ? 1
      : interpolate(frame, [0, overlap], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

  const captionStart = Math.round(overlap * 0.5);
  const rise = spring({
    frame: frame - captionStart,
    fps,
    config: {damping: 200},
    durationInFrames: 32,
  });
  const captionOpacity = interpolate(
    frame,
    [captionStart, captionStart + 24, sceneFrames - 36, sceneFrames - 14],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const captionShift = interpolate(rise, [0, 1], [28, 0]);
  const kickerOpacity = interpolate(
    frame,
    [captionStart + 6, captionStart + 30, sceneFrames - 36, sceneFrames - 14],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{opacity: reveal}}>
      <AbsoluteFill style={{overflow: 'hidden'}}>
        <Img
          src={scene.image}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: `scale(${scale}) translate(${panX}%, ${panY}%)`,
          }}
        />
      </AbsoluteFill>

      {/* Readability wash: light at the top for the wordmark, heavy at the bottom. */}
      <AbsoluteFill
        style={{
          background:
            `linear-gradient(180deg, ${SHADE}0.55) 0%, ${SHADE}0) 24%, ` +
            `${SHADE}0) 44%, ${SHADE}0.82) 76%, ${SHADE}0.97) 100%)`,
        }}
      />

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          padding: '0 120px 128px',
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            textAlign: 'center',
            transform: `translateY(${captionShift}px)`,
          }}
        >
          {scene.kicker ? (
            <div
              style={{
                fontFamily: cinzel.fontFamily,
                fontWeight: 400,
                fontSize: 24,
                letterSpacing: 9,
                textTransform: 'uppercase',
                color: 'rgba(236, 225, 203, 0.68)',
                marginBottom: 20,
                opacity: kickerOpacity,
              }}
            >
              {scene.kicker}
            </div>
          ) : null}
          <div
            style={{
              fontFamily: merriweather.fontFamily,
              fontWeight: 300,
              fontSize: 58,
              lineHeight: 1.42,
              color: INK,
              textShadow: '0 2px 22px rgba(0, 0, 0, 0.85)',
              opacity: captionOpacity,
            }}
          >
            {scene.caption}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Wordmark: React.FC<{title: string}> = ({title}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, 34, durationInFrames - 50, durationInFrames - 12],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{padding: '74px 96px', opacity}}>
      <div
        style={{
          fontFamily: cinzel.fontFamily,
          fontWeight: 600,
          fontSize: 30,
          letterSpacing: 14,
          textTransform: 'uppercase',
          color: 'rgba(246, 242, 234, 0.66)',
          textShadow: '0 2px 16px rgba(0, 0, 0, 0.6)',
        }}
      >
        {title}
      </div>
      <div
        style={{
          width: 92,
          height: 2,
          marginTop: 16,
          background: 'rgba(246, 242, 234, 0.34)',
        }}
      />
    </AbsoluteFill>
  );
};

const Curtain: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [durationInFrames - 26, durationInFrames - 1],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return <AbsoluteFill style={{backgroundColor: '#04050a', opacity}} />;
};

const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        'radial-gradient(ellipse at 50% 45%, rgba(0, 0, 0, 0) 40%, rgba(0, 0, 0, 0.52) 100%)',
      pointerEvents: 'none',
    }}
  />
);

export const CinematicDoc: React.FC<CinematicProps> = ({
  title,
  scenes,
  sceneDurationInSeconds,
  overlapInSeconds,
}) => {
  const {fps} = useVideoConfig();
  const sceneFrames = Math.max(1, Math.round(sceneDurationInSeconds * fps));
  const overlap = Math.min(sceneFrames - 1, Math.round(overlapInSeconds * fps));
  const step = sceneFrames - overlap;

  return (
    <AbsoluteFill style={{backgroundColor: '#04050a'}}>
      {scenes.map((scene, index) => (
        <Sequence
          key={`${index}-${scene.image}`}
          from={index * step}
          durationInFrames={sceneFrames}
          name={`Scene ${index + 1}`}
        >
          <CinematicScene
            scene={scene}
            index={index}
            sceneFrames={sceneFrames}
            overlap={overlap}
          />
        </Sequence>
      ))}
      <Vignette />
      <Wordmark title={title} />
      <Curtain />
    </AbsoluteFill>
  );
};
