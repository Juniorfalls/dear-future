import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadCinzel} from '@remotion/google-fonts/Cinzel';
import {loadFont as loadMerriweather} from '@remotion/google-fonts/Merriweather';
import type {CinematicProps, Scene} from './types';

/**
 * Epic titles in Cinzel (a Trajan-style capital serif, the documentary
 * standard), narration in Merriweather. Both ship through
 * @remotion/google-fonts, so the render waits for the real fonts instead of
 * falling back to a system serif.
 */
const cinzel = loadCinzel('normal', {weights: ['400', '700'], subsets: ['latin']});
const merriweather = loadMerriweather('normal', {
  weights: ['300', '400', '700'],
  subsets: ['latin'],
});

const INK = '#F4EFE4';
const SHADE = 'rgba(3, 4, 6, ';

/** Cinematic 2.35:1-ish letterbox: ~9.5% of the frame height top and bottom. */
const LETTERBOX_RATIO = 0.095;

type SceneProps = {
  scene: Scene;
  index: number;
  sceneFrames: number;
  overlap: number;
  bar: number;
};

/**
 * One shot: full-bleed still with a very slow Ken Burns push, plus the caption
 * lower third. Incoming scenes fade in on top of the outgoing one (which stays
 * opaque underneath), so a crossfade never dips to black in the middle.
 */
const CinematicScene: React.FC<SceneProps> = ({scene, index, sceneFrames, overlap, bar}) => {
  const frame = useCurrentFrame();

  // Ken Burns: a slow, linear push (no easing curve, so it reads as a steady
  // camera move) with a gentle lateral drift that alternates per shot.
  const scale = interpolate(frame, [0, sceneFrames], [1.04, 1.17], {
    extrapolateRight: 'clamp',
  });
  const drift = index % 2 === 0 ? 1 : -1;
  const panX = interpolate(frame, [0, sceneFrames], [-1.3 * drift, 1.3 * drift], {
    extrapolateRight: 'clamp',
  });
  const panY = interpolate(frame, [0, sceneFrames], [0.7, -0.7], {
    extrapolateRight: 'clamp',
  });

  // Crossfade in; the previous scene stays fully opaque behind this one.
  const reveal =
    index === 0
      ? 1
      : interpolate(frame, [0, overlap], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

  // Captions: slow fade in once the shot has settled, long hold, slow fade out
  // before the next shot takes over.
  const captionIn = overlap + Math.round(sceneFrames * 0.08);
  const captionFadeIn = 34;
  const captionFadeOut = 30;
  const captionOut = sceneFrames - captionFadeOut - Math.round(sceneFrames * 0.04);

  const captionOpacity = interpolate(
    frame,
    [captionIn, captionIn + captionFadeIn, captionOut, captionOut + captionFadeOut],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  const captionShift = interpolate(
    frame,
    [captionIn, captionIn + captionFadeIn + 10],
    [18, 0],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
      easing: Easing.out(Easing.cubic),
    },
  );
  const kickerOpacity = captionOpacity * 0.85;

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

      {/* Readability wash: light at the top for the wordmark, heavy at the
          bottom so the caption always sits on near-solid black. */}
      <AbsoluteFill
        style={{
          background:
            `linear-gradient(180deg, ${SHADE}0.6) 0%, ${SHADE}0) 22%, ` +
            `${SHADE}0) 40%, ${SHADE}0.55) 62%, ${SHADE}0.93) 84%, ` +
            `${SHADE}1) 100%)`,
        }}
      />

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          padding: `0 130px ${bar + 62}px`,
        }}
      >
        <div
          style={{
            maxWidth: 1400,
            textAlign: 'center',
            transform: `translateY(${captionShift}px)`,
            opacity: captionOpacity,
          }}
        >
          {scene.kicker ? (
            <div
              style={{
                fontFamily: cinzel.fontFamily,
                fontWeight: 400,
                fontSize: 24,
                letterSpacing: 10,
                textTransform: 'uppercase',
                color: 'rgba(214, 189, 140, 0.86)',
                marginBottom: 22,
                opacity: kickerOpacity,
                textShadow: '0 2px 14px rgba(0, 0, 0, 0.85)',
              }}
            >
              {scene.kicker}
            </div>
          ) : null}
          <div
            style={{
              fontFamily: merriweather.fontFamily,
              fontWeight: 300,
              fontSize: 56,
              lineHeight: 1.44,
              color: INK,
              textShadow: '0 3px 26px rgba(0, 0, 0, 0.95), 0 0 2px rgba(0, 0, 0, 0.9)',
            }}
          >
            {scene.caption}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Wordmark: React.FC<{title: string; bar: number}> = ({title, bar}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [0, 40, durationInFrames - 55, durationInFrames - 16],
    [0, 1, 1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  return (
    <AbsoluteFill style={{padding: `${bar + 44}px 104px`, opacity}}>
      <div
        style={{
          fontFamily: cinzel.fontFamily,
          fontWeight: 700,
          fontSize: 34,
          letterSpacing: 16,
          textTransform: 'uppercase',
          color: 'rgba(244, 239, 228, 0.78)',
          textShadow: '0 2px 20px rgba(0, 0, 0, 0.75)',
        }}
      >
        {title}
      </div>
      <div
        style={{
          width: 104,
          height: 2,
          marginTop: 16,
          background: 'rgba(214, 189, 140, 0.55)',
        }}
      />
    </AbsoluteFill>
  );
};

/** Cinematic letterbox: solid black bars top and bottom, drawn last so the
 *  edges stay perfectly hard over the gradient and vignette. */
const Letterbox: React.FC<{bar: number}> = ({bar}) => (
  <>
    <div style={{position: 'absolute', top: 0, left: 0, width: '100%', height: bar, backgroundColor: '#000'}} />
    <div style={{position: 'absolute', bottom: 0, left: 0, width: '100%', height: bar, backgroundColor: '#000'}} />
  </>
);

const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        'radial-gradient(ellipse at 50% 45%, rgba(0, 0, 0, 0) 38%, rgba(0, 0, 0, 0.58) 100%)',
      pointerEvents: 'none',
    }}
  />
);

const Curtain: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const opacity = interpolate(
    frame,
    [durationInFrames - 26, durationInFrames - 1],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  return <AbsoluteFill style={{backgroundColor: '#000', opacity}} />;
};

export const CinematicDoc: React.FC<CinematicProps> = ({
  title,
  scenes,
  sceneDurationInSeconds,
  overlapInSeconds,
}) => {
  const {fps, height} = useVideoConfig();
  const sceneFrames = Math.max(1, Math.round(sceneDurationInSeconds * fps));
  const overlap = Math.min(sceneFrames - 1, Math.round(overlapInSeconds * fps));
  const step = sceneFrames - overlap;
  const bar = Math.round(height * LETTERBOX_RATIO);

  return (
    <AbsoluteFill style={{backgroundColor: '#03040a'}}>
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
            bar={bar}
          />
        </Sequence>
      ))}
      <Vignette />
      <Wordmark title={title} bar={bar} />
      <Letterbox bar={bar} />
      <Curtain />
    </AbsoluteFill>
  );
};
