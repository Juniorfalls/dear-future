import React from 'react';
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadCinzel} from '@remotion/google-fonts/Cinzel';
import {loadFont as loadMerriweather} from '@remotion/google-fonts/Merriweather';
import type {CinematicProps, Scene, SceneLayout} from './types';

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

/** Some free image hosts bake a watermark into the bottom edge of their
 *  output; drop that strip of the frame entirely. */
const WATERMARK_CROP_PX = 20;

/** Strength of the dust/fog layer. Subtle by design: it should read as air,
 *  not as an effect. */
const ATMOSPHERE_OPACITY = 0.12;

/** How often the diagonal light ray crosses the frame. */
const SWEEP_SECONDS = 5;

/** Deterministic pseudo-random in [0, 1), so every render of a frame matches. */
const rand = (index: number, salt: number) => {
  const value = Math.sin(index * 127.1 + salt * 311.7) * 43758.5453;
  return value - Math.floor(value);
};

type Mote = {
  x: number;
  y: number;
  size: number;
  speed: number;
  sway: number;
  phase: number;
  alpha: number;
};

/** Dust specks drifting upward through the light. Generated once so their
 *  paths are stable across scenes and re-renders. */
const MOTES: Mote[] = Array.from({length: 24}, (_, i) => ({
  x: rand(i, 1) * 100,
  y: rand(i, 2) * 100,
  size: 1.2 + rand(i, 3) * 3.4,
  speed: 0.006 + rand(i, 4) * 0.012,
  sway: 0.5 + rand(i, 5) * 2.4,
  phase: rand(i, 6) * Math.PI * 2,
  alpha: 0.25 + rand(i, 7) * 0.55,
}));

const FOG_BANKS = [
  {tint: '214, 189, 140', x: 18, y: 30, rx: 46, ry: 30, speed: 0.0022, phase: 0},
  {tint: '196, 214, 224', x: 78, y: 60, rx: 38, ry: 26, speed: 0.0016, phase: 2.1},
  {tint: '150, 170, 190', x: 46, y: 82, rx: 52, ry: 24, speed: 0.0012, phase: 4.2},
];

/** Brass edge and label ink shared by the presenter placeholder panels. */
const HOST_EDGE = 'rgba(214, 189, 140, 0.55)';
const HOST_LABEL = 'rgba(214, 189, 140, 0.92)';

/** Stage wall behind a full-frame presenter shot: a cool studio falloff onto
 *  black, so the placeholder panel reads as lit rather than pasted on. */
const HOST_STAGE =
  'radial-gradient(ellipse at 50% 42%, rgba(58, 72, 88, 0.55) 0%, ' +
  'rgba(9, 13, 19, 0.98) 62%, #03040a 100%)';

const HOST_PANEL =
  'linear-gradient(150deg, #2b3743 0%, #1d2a36 48%, #131d27 100%)';

/**
 * Stand-in for the virtual presenter until the host video is rendered.
 *
 * `full` fills the centre of the frame the way a talking-head shot will;
 * `pip` is the small rounded corner inset used over b-roll. Both are drawn at
 * 1080p-relative sizes so a vertical composition keeps the same proportions.
 * Replacing this component with a <Video> of the host is the whole swap.
 */
const HostPlaceholder: React.FC<{variant: 'full' | 'pip'; bar: number}> = ({
  variant,
  bar,
}) => {
  const {width, height} = useVideoConfig();
  // Design units are 1920x1080; everything below scales with the frame width.
  const s = width / 1920;
  const pipW = 470 * s;
  const pipH = (pipW * 9) / 16;

  const label = (fontSize: number, letterSpacing: number) => ({
    fontFamily: cinzel.fontFamily,
    fontWeight: 700,
    fontSize,
    letterSpacing,
    textTransform: 'uppercase' as const,
    color: HOST_LABEL,
  });

  const note = {
    fontFamily: merriweather.fontFamily,
    fontWeight: 300,
    fontSize: 20 * s,
    letterSpacing: 2 * s,
    color: 'rgba(244, 239, 228, 0.42)',
  };

  if (variant === 'full') {
    // The presenter shot lives in the stage band above the caption, so the
    // lower third never has to sit on top of the host's face. The panel is
    // sized from the space that is actually left over, keeping 16:9.
    const captionBand = 300 * s;
    const stageHeight = Math.max(200 * s, height - bar * 2 - captionBand);
    const panelW = Math.min(width * 0.56, 1060 * s, (stageHeight * 16) / 9);
    const panelH = (panelW * 9) / 16;
    return (
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          paddingTop: bar,
          paddingBottom: bar + captionBand,
        }}
      >
        <div
          style={{
            width: panelW,
            height: panelH,
            borderRadius: 18 * s,
            background: HOST_PANEL,
            border: `${Math.max(1, 2 * s)}px solid ${HOST_EDGE}`,
            boxShadow:
              `0 ${40 * s}px ${120 * s}px rgba(0, 0, 0, 0.72), ` +
              `inset 0 0 ${140 * s}px rgba(214, 189, 140, 0.07)`,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            gap: 20 * s,
          }}
        >
          <div style={label(44 * s, 18 * s)}>Host</div>
          <div style={note}>virtual presenter · placeholder</div>
        </div>
      </AbsoluteFill>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        left: 100 * s,
        // Clear the lower letterbox bar, then sit just above the caption block.
        bottom: bar + 78 * s,
        width: pipW,
        height: pipH,
        borderRadius: 22 * s,
        overflow: 'hidden',
        background: HOST_PANEL,
        border: `${Math.max(1.5, 3 * s)}px solid ${HOST_EDGE}`,
        boxShadow: `0 ${26 * s}px ${70 * s}px rgba(0, 0, 0, 0.78)`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 8 * s,
      }}
    >
      <div style={label(26 * s, 12 * s)}>Host</div>
      <div style={{...note, fontSize: 13 * s, letterSpacing: 1.4 * s}}>placeholder</div>
    </div>
  );
};

type SceneProps = {
  scene: Scene;
  index: number;
  sceneFrames: number;
  overlap: number;
  bar: number;
};

/**
 * One shot, framed by its `layout`:
 *
 *  - `host_full`  — no b-roll, presenter panel centred on the studio stage
 *  - `host_pip`   — full-bleed b-roll with the presenter inset bottom-left
 *  - `broll_only` — full-bleed b-roll
 *
 * B-roll shots get the 2.5D camera move — a quicker Ken Burns push, a slow
 * perspective tilt, and a blurred back plate that lags behind the foreground so
 * the frame gains a little depth. The caption lower third is shared by all three.
 * Incoming scenes fade in on top of the outgoing one (which stays opaque
 * underneath), so a crossfade never dips to black in the middle — including when
 * the layout changes, because a `host_full` shot covers the frame with its stage.
 */
const CinematicScene: React.FC<SceneProps> = ({scene, index, sceneFrames, overlap, bar}) => {
  const frame = useCurrentFrame();

  // Ken Burns: a steady push (no easing curve, so it reads as a camera move)
  // with a lateral drift that alternates per shot. Quicker than the original
  // pass, but still slow enough to feel like a dolly rather than a zoom.
  const scale = interpolate(frame, [0, sceneFrames], [1.06, 1.26], {
    extrapolateRight: 'clamp',
  });
  const drift = index % 2 === 0 ? 1 : -1;
  const panX = interpolate(frame, [0, sceneFrames], [-2.2 * drift, 2.2 * drift], {
    extrapolateRight: 'clamp',
  });
  const panY = interpolate(frame, [0, sceneFrames], [1.1, -1.1], {
    extrapolateRight: 'clamp',
  });

  // 2.5D: a gentle perspective orbit, flat at the cut so crossfades stay clean.
  const tiltProgress = Math.min(1, Math.max(0, frame / sceneFrames));
  const tiltY = Math.sin(tiltProgress * Math.PI) * 2.4 * drift;
  const tiltX = Math.sin(tiltProgress * Math.PI + 0.6) * 1.1;

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

  const imageSrc = scene.image && (scene.image.startsWith('http') ? scene.image : staticFile(scene.image));
  const layout: SceneLayout = scene.layout;
  const showsBroll = layout !== 'host_full';

  return (
    <AbsoluteFill style={{opacity: reveal}}>
      {showsBroll && imageSrc ? (
        <>
          {/* The watermark crop shortens the frame by a few pixels: everything
              inside is still cover-cropped, so the bottom edge is simply gone. */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: `calc(100% - ${WATERMARK_CROP_PX}px)`,
              overflow: 'hidden',
            }}
          >
            {/* Parallax back plate: same still, pushed further in, softened and
                dimmed, drifting with less travel than the foreground. It fills
                the edges the tilt exposes and reads as depth behind the subject. */}
            <AbsoluteFill>
              <Img
                src={imageSrc}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform:
                    `scale(${scale + 0.18}) ` +
                    `translate(${panX * 0.3}%, ${panY * 0.3}%)`,
                  filter: 'blur(14px) brightness(0.62) saturate(0.9)',
                }}
              />
            </AbsoluteFill>

            <AbsoluteFill style={{perspective: 1600}}>
              <Img
                // Local stills (committed under remotion/public) go through
                // staticFile(); remote URLs are used as-is.
                src={imageSrc}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  transform:
                    `scale(${scale}) ` +
                    `translate(${panX}%, ${panY}%) ` +
                    `rotateY(${tiltY}deg) rotateX(${tiltX}deg)`,
                  backfaceVisibility: 'hidden',
                }}
              />
            </AbsoluteFill>
          </div>
        </>
      ) : (
        // No b-roll behind the presenter: an opaque stage so the crossfade
        // out of the previous shot never shows it through this one.
        <AbsoluteFill style={{background: HOST_STAGE}} />
      )}

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

      {/* The presenter panel sits above the wash so it keeps its own lighting:
          centred on stage for `host_full`, inset bottom-left for `host_pip`. */}
      {layout !== 'broll_only' ? (
        <HostPlaceholder variant={layout === 'host_full' ? 'full' : 'pip'} bar={bar} />
      ) : null}

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          // With the presenter in the bottom-left corner the caption slides to
          // the right, so the two lower thirds never sit on top of each other.
          padding: `0 130px ${bar + 62}px ${layout === 'host_pip' ? 640 : 130}px`,
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

/**
 * Dust and fog over the whole film. Everything is driven by the current frame
 * (never by wall-clock CSS animation) so Remotion renders it deterministically
 * and the dust is identical in the preview and the MP4.
 */
const DustOverlay: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        opacity: ATMOSPHERE_OPACITY,
        mixBlendMode: 'screen',
        pointerEvents: 'none',
      }}
    >
      {FOG_BANKS.map((fog, index) => (
        <div
          key={`fog-${index}`}
          style={{
            position: 'absolute',
            left: `${fog.x + Math.sin(frame * fog.speed + fog.phase) * 9}%`,
            top: `${fog.y + Math.cos(frame * fog.speed * 0.8 + fog.phase) * 6}%`,
            width: `${fog.rx * 2}%`,
            height: `${fog.ry * 2}%`,
            transform: 'translate(-50%, -50%)',
            background:
              `radial-gradient(ellipse at center, rgba(${fog.tint}, 0.30) 0%, ` +
              `rgba(${fog.tint}, 0.12) 45%, rgba(${fog.tint}, 0) 72%)`,
            filter: 'blur(24px)',
          }}
        />
      ))}

      {MOTES.map((mote, index) => {
        // Wrap upward: a mote that leaves the top re-enters at the bottom, so
        // the field never thins out or pops during a long shot.
        const top = (((mote.y - frame * mote.speed) % 100) + 100) % 100;
        const left = mote.x + Math.sin(frame * 0.008 + mote.phase) * mote.sway;
        return (
          <div
            key={`mote-${index}`}
            style={{
              position: 'absolute',
              left: `${left}%`,
              top: `${top}%`,
              width: mote.size,
              height: mote.size,
              borderRadius: '50%',
              background:
                'radial-gradient(circle, rgba(255, 246, 224, 0.95) 0%, ' +
                'rgba(255, 246, 224, 0) 70%)',
              opacity: mote.alpha,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * A soft diagonal shaft of light crossing the frame every SWEEP_SECONDS, as if
 * the sun were moving behind the subject. The gradient fades in and out over
 * each pass so the loop never shows a hard edge.
 */
const LightSweep: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const period = Math.max(1, Math.round(fps * SWEEP_SECONDS));
  const progress = (frame % period) / period;
  const left = interpolate(progress, [0, 1], [-65, 165]);
  const intensity = Math.sin(Math.PI * progress);

  return (
    <AbsoluteFill style={{pointerEvents: 'none', mixBlendMode: 'screen'}}>
      <div
        style={{
          position: 'absolute',
          top: '-25%',
          bottom: '-25%',
          left: `${left}%`,
          width: '34%',
          transform: 'rotate(15deg)',
          background:
            'linear-gradient(90deg, rgba(255, 236, 200, 0) 0%, ' +
            'rgba(255, 236, 200, 0.10) 35%, rgba(255, 247, 226, 0.16) 50%, ' +
            'rgba(255, 236, 200, 0.10) 65%, rgba(255, 236, 200, 0) 100%)',
          filter: 'blur(26px)',
          opacity: intensity * 0.9,
        }}
      />
    </AbsoluteFill>
  );
};

export const CinematicDoc: React.FC<CinematicProps> = ({
  title,
  scenes,
  sceneDurationInSeconds,
  overlapInSeconds,
}) => {
  const {fps, height} = useVideoConfig();

  // Scenes may carry their own duration (the generator writes one per scene);
  // otherwise every scene uses the composition default.
  const durations = scenes.map((scene) =>
    Math.max(1, Math.round((scene.durationInSeconds ?? sceneDurationInSeconds) * fps)),
  );
  const overlap = Math.min(
    Math.round(overlapInSeconds * fps),
    Math.min(...durations) - 1,
  );
  const starts: number[] = [];
  let cursor = 0;
  for (const duration of durations) {
    starts.push(cursor);
    cursor += duration - overlap;
  }
  const bar = Math.round(height * LETTERBOX_RATIO);

  return (
    <AbsoluteFill style={{backgroundColor: '#03040a'}}>
      {scenes.map((scene, index) => (
        <Sequence
          key={`${index}-${scene.image}`}
          from={starts[index]}
          durationInFrames={durations[index]}
          name={`Scene ${index + 1}`}
        >
          <CinematicScene
            scene={scene}
            index={index}
            sceneFrames={durations[index]}
            overlap={overlap}
            bar={bar}
          />
        </Sequence>
      ))}
      <DustOverlay />
      <LightSweep />
      <Vignette />
      <Wordmark title={title} bar={bar} />
      <Letterbox bar={bar} />
      <Curtain />
    </AbsoluteFill>
  );
};
