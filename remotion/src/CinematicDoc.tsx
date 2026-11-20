import React, {useMemo} from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {loadFont as loadCinzel} from '@remotion/google-fonts/Cinzel';
import {loadFont as loadNunito} from '@remotion/google-fonts/Nunito';
import {loadFont as loadOswald} from '@remotion/google-fonts/Oswald';
import type {AudioTrack, CinematicProps, FilmStyle, Grade, Scene, SceneLayout} from './types';
import {buildTimeline} from './timeline';
import {resolveCaptions} from './subtitles';

/**
 * Typography follows the reference film: Cinzel (a Trajan-style capital serif)
 * only for the wordmark and the host-scene identification line, Oswald bold
 * italic caps for subtitles, and a rounded heavy sans for the end card.
 */
const cinzel = loadCinzel('normal', {weights: ['400', '700'], subsets: ['latin']});
const oswald = loadOswald('normal', {weights: ['700'], subsets: ['latin']});
const nunito = loadNunito('normal', {weights: ['800'], subsets: ['latin']});

/** Off-white used by the wordmark and the identification line. */
const INK = '#F4EFE4';
const SHADE = 'rgba(3, 4, 6, ';

/** Cinematic 2.35:1-ish letterbox: ~9.5% of the frame height top and bottom. */
const LETTERBOX_RATIO = 0.095;

/** Some free image hosts bake a watermark into the bottom edge of their
 *  output; drop that strip of the frame entirely. */
const WATERMARK_CROP_PX = 20;

/** Strength of the dust/fog layer in the legacy look. */
const ATMOSPHERE_OPACITY = 0.12;

/** How often the diagonal light ray crosses the frame. */
const SWEEP_SECONDS = 5;

/**
 * How the film is presented. Episodes written before this existed get the full
 * legacy treatment; an episode that wants the reference look passes
 * `"style": {...}` in scenes.json and turns the extras off.
 */
const DEFAULT_STYLE: Required<FilmStyle> = {
  letterbox: true,
  atmosphereOpacity: ATMOSPHERE_OPACITY,
  lightSweep: true,
  vignette: true,
  wordmark: 'all',
  scrim: 0.6,
};

/**
 * Location-coded grades, matched to the reference's measured palette: a cool,
 * dark blue for night interiors and a muted warm amber for daylight scenes.
 * The filter sits on the media; the tint wash goes over the finished shot.
 */
const GRADE: Record<Grade, {filter: string; tint: string}> = {
  cold: {
    // sepia + hue-rotate forces a cool cast even when the source still is
    // warm; the reference's night interiors are blue-dominant, not just darker.
    filter: 'sepia(0.42) hue-rotate(160deg) saturate(1.25) brightness(0.72) contrast(1.05)',
    tint: 'rgba(38, 58, 78, 0.30)',
  },
  warm: {
    filter: 'saturate(0.90) brightness(1.01) contrast(1.02) sepia(0.08)',
    tint: 'rgba(216, 180, 131, 0.20)',
  },
  neutral: {
    filter: 'saturate(0.92) contrast(1.03)',
    tint: 'rgba(0, 0, 0, 0)',
  },
};

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

/** Brass edge for the presenter inset, matching the kickers. */
const HOST_EDGE = 'rgba(214, 189, 140, 0.55)';

/** Opaque base behind a full-frame presenter shot: a cut into an intro must
 *  never show the previous scene through the video. */
const HOST_STAGE =
  'radial-gradient(ellipse at 50% 42%, rgba(58, 72, 88, 0.55) 0%, ' +
  'rgba(9, 13, 19, 0.98) 62%, #03040a 100%)';

/** The virtual presenter. A free Pexels talking-head clip stands in until the
 *  rendered host exists: drop a new file at public/host/presenter.mp4 and
 *  nothing else changes. */
const PRESENTER_SRC = staticFile('host/presenter.mp4');

/**
 * Music bed used when the episode does not name one. Royalty-free (CC0) ambient
 * track, committed at public/audio/bg_music.mp3, so a bare scenes.json still
 * renders with sound.
 */
const DEFAULT_AUDIO: AudioTrack = {
  src: 'audio/bg_music.mp3',
  volume: 0.15,
  loop: true,
};

/**
 * The presenter, framed by the scene layout.
 *
 * `full` fills the frame: the clip is contained over a blurred, pushed-in copy
 * of itself, so a source that does not match the composition ratio is framed
 * in blur rather than in black. `pip` is the rounded bottom-left inset that
 * sits over b-roll. Sizes are 1080p-relative so vertical shorts keep the same
 * proportions.
 *
 * Both are muted: the film carries no audio track yet. Host narration gets a
 * volume curve when the voice track lands.
 */
const Presenter: React.FC<{variant: 'full' | 'pip'; bar: number; filter: string}> = ({
  variant,
  bar,
  filter,
}) => {
  const {width} = useVideoConfig();
  // Design units are 1920x1080; everything below scales with the frame width.
  const s = width / 1920;

  if (variant === 'full') {
    return (
      <>
        <AbsoluteFill style={{background: HOST_STAGE}} />

        {/* Blurred backplate: the same frame pushed in, softened and dimmed,
            so a 4:3 or vertical presenter never leaves hard bars. */}
        <AbsoluteFill>
          <OffthreadVideo
            src={PRESENTER_SRC}
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: 'scale(1.16)',
              filter: `${filter} blur(34px) brightness(0.52) saturate(0.85)`,
            }}
          />
        </AbsoluteFill>

        {/* Foreground presenter: fills the frame, cropped by its own ratio. */}
        <AbsoluteFill>
          <OffthreadVideo
            src={PRESENTER_SRC}
            muted
            style={{width: '100%', height: '100%', objectFit: 'contain', filter}}
          />
        </AbsoluteFill>
      </>
    );
  }

  const pipW = 470 * s;
  const pipH = (pipW * 9) / 16;

  return (
    <div
      style={{
        position: 'absolute',
        left: 100 * s,
        // Clear the lower edge and sit beside, not under, the subtitle.
        bottom: bar + 78 * s,
        width: pipW,
        height: pipH,
        borderRadius: 22 * s,
        overflow: 'hidden',
        background: '#101a24',
        border: `${Math.max(1.5, 3 * s)}px solid ${HOST_EDGE}`,
        boxShadow: `0 ${26 * s}px ${70 * s}px rgba(0, 0, 0, 0.78)`,
      }}
    >
      <OffthreadVideo
        src={PRESENTER_SRC}
        muted
        style={{width: '100%', height: '100%', objectFit: 'cover', filter}}
      />
    </div>
  );
};

type SceneProps = {
  scene: Scene;
  index: number;
  sceneFrames: number;
  /** Frames this scene overlaps its predecessor; 0 means a hard cut. */
  overlapIn: number;
  bar: number;
  /** Strength of the subtitle scrim (0 = outline only, the reference look). */
  scrim: number;
};

/** The lower-third gradient, scaled by the episode's scrim setting. */
const scrimGradient = (scrim: number) => {
  const a = (value: number) => (value * scrim).toFixed(2);
  return (
    `linear-gradient(180deg, ${SHADE}${a(0.6)}) 0%, ${SHADE}${a(0.25)}) 20%, ` +
    `${SHADE}0) 42%, ${SHADE}${a(0.55)}) 66%, ` +
    `${SHADE}${a(0.92)}) 86%, ${SHADE}${a(1)}) 100%)`
  );
};

/**
 * One shot, framed by its `layout`:
 *
 *  - `host_full`  — presenter only: intro and outro, the channel's face
 *  - `host_pip`   — full-bleed b-roll with the presenter inset bottom-left
 *  - `broll_only` — full-bleed b-roll
 *
 * Every shot is graded by its `grade`, cut in on a single frame unless the
 * scene asks for a crossfade, and carries one subtitle chunk at a time in the
 * reference's outlined condensed style.
 */
const CinematicScene: React.FC<SceneProps> = ({
  scene,
  index,
  sceneFrames,
  overlapIn,
  bar,
  scrim,
}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const s = width / 1920;

  const layout: SceneLayout = scene.layout;
  const showsBroll = layout !== 'host_full';
  const grade = GRADE[scene.grade ?? 'neutral'];
  const sceneSeconds = sceneFrames / fps;

  // Camera: a steady push with an alternating lateral drift. Shorter shots get
  // a gentler move so a 2.5s cut does not read as a zoom.
  const scale = interpolate(frame, [0, sceneFrames], [1.05, 1.17], {
    extrapolateRight: 'clamp',
  });
  const drift = index % 2 === 0 ? 1 : -1;
  const panX = interpolate(frame, [0, sceneFrames], [-1.4 * drift, 1.4 * drift], {
    extrapolateRight: 'clamp',
  });
  const panY = interpolate(frame, [0, sceneFrames], [0.8, -0.8], {
    extrapolateRight: 'clamp',
  });

  // 2.5D: a gentle perspective orbit, flat at the cut so edits stay clean.
  const tiltProgress = Math.min(1, Math.max(0, frame / sceneFrames));
  const tiltY = Math.sin(tiltProgress * Math.PI) * 1.8 * drift;
  const tiltX = Math.sin(tiltProgress * Math.PI + 0.6) * 0.9;

  // A cut is fully opaque on its first frame; only a crossfade ramps up.
  const reveal =
    overlapIn <= 0 || index === 0
      ? 1
      : interpolate(frame, [0, overlapIn], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

  // Subtitles: authored chunks when the episode has them, otherwise the caption
  // split to fit the shot. One chunk on screen at a time, swapped hard.
  const cues = useMemo(() => resolveCaptions(scene, sceneSeconds), [scene, sceneSeconds]);
  const cueTime = frame / fps;
  const cue = cues.find((item) => cueTime >= item.from && cueTime < item.to);

  const imageSrc =
    scene.image && (scene.image.startsWith('http') ? scene.image : staticFile(scene.image));

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
                  filter: `${grade.filter} blur(14px) brightness(0.62) saturate(0.9)`,
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
                  filter: grade.filter,
                }}
              />
            </AbsoluteFill>
          </div>
        </>
      ) : (
        // No b-roll behind the presenter: an opaque stage so a cut out of the
        // previous shot never shows it through this one.
        <AbsoluteFill style={{background: HOST_STAGE}} />
      )}

      {/* Full-frame presenter goes in before the scrim, so the gradient that
          keeps the subtitle readable sits on top of the video too. */}
      {layout === 'host_full' ? (
        <Presenter variant="full" bar={bar} filter={grade.filter} />
      ) : null}

      {/* Location tint over the finished shot: cool blue or warm amber, blended
          softly so it colours the image without flattening it. */}
      {grade.tint !== 'rgba(0, 0, 0, 0)' ? (
        <AbsoluteFill
          style={{background: grade.tint, mixBlendMode: 'soft-light', pointerEvents: 'none'}}
        />
      ) : null}

      {/* Subtitle scrim. At 0 this disappears entirely and the outlined type
          carries its own contrast, which is how the reference works. */}
      {scrim > 0 ? (
        <AbsoluteFill style={{background: scrimGradient(scrim)}} />
      ) : null}

      {/* The corner inset sits above the scrim instead: it is small enough that
          the gradient would only crush it, and the subtitle is clear of it. */}
      {layout === 'host_pip' ? (
        <Presenter variant="pip" bar={bar} filter={grade.filter} />
      ) : null}

      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          // With the presenter in the bottom-left corner the subtitle slides to
          // the right, so the two lower thirds never sit on top of each other.
          padding: `0 ${130 * s}px ${bar + 112 * s}px ${
            layout === 'host_pip' ? 640 * s : 130 * s
          }px`,
        }}
      >
        <div style={{textAlign: 'center'}}>
          {/* Channel identification line, host scenes only: the body of the film
              stays as clean as the reference. */}
          {layout === 'host_full' && scene.kicker ? (
            <div
              style={{
                fontFamily: cinzel.fontFamily,
                fontWeight: 400,
                fontSize: 22 * s,
                letterSpacing: 9 * s,
                textTransform: 'uppercase',
                color: 'rgba(214, 189, 140, 0.9)',
                marginBottom: 14 * s,
                textShadow: '0 2px 14px rgba(0, 0, 0, 0.85)',
              }}
            >
              {scene.kicker}
            </div>
          ) : null}

          {cue ? (
            <div
              style={{
                fontFamily: oswald.fontFamily,
                fontWeight: 700,
                fontStyle: 'italic',
                fontSize: 66 * s,
                lineHeight: 1.12,
                letterSpacing: 1 * s,
                textTransform: 'uppercase',
                color: '#FFFFFF',
                WebkitTextStroke: `${Math.max(2, 6 * s)}px #000`,
                paintOrder: 'stroke fill',
                textShadow: `0 ${4 * s}px ${18 * s}px rgba(0, 0, 0, 0.6)`,
              }}
            >
              {cue.text}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Wordmark: React.FC<{
  title: string;
  bar: number;
  mode: 'all' | 'intro' | 'none';
  introFrames: number;
}> = ({title, bar, mode, introFrames}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  if (mode === 'none') {
    return null;
  }

  const opacity =
    mode === 'intro'
      ? interpolate(frame, [0, 30, Math.max(40, introFrames - 30), introFrames], [0, 1, 1, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : interpolate(
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
const DustOverlay: React.FC<{opacity: number}> = ({opacity}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        opacity,
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

/**
 * End card, measured from the reference: near-black with a faint warm cast,
 * one centred line of heavy rounded sans in white, fading up over ~0.6s. The
 * closing Curtain handles the fade to black.
 */
const EndCard: React.FC<{title: string}> = ({title}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();
  const s = width / 1920;
  const opacity = interpolate(frame, [0, 18], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        // The gradient is the parent's background on purpose: an absolutely
        // positioned sibling would paint over the title, not behind it.
        background:
          'radial-gradient(ellipse at 50% 46%, rgba(38, 20, 15, 0.85) 0%, ' +
          'rgba(11, 5, 5, 0.98) 58%, #060303 100%)',
        backgroundColor: '#0b0505',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          opacity,
          fontFamily: nunito.fontFamily,
          fontWeight: 800,
          fontSize: 92 * s,
          lineHeight: 1.12,
          maxWidth: 1400 * s,
          textAlign: 'center',
          color: '#FFFFFF',
          textShadow: `0 ${6 * s}px ${30 * s}px rgba(0, 0, 0, 0.75)`,
        }}
      >
        {title}
      </div>
    </AbsoluteFill>
  );
};

/**
 * The music bed: one track under the whole composition, looping if it is
 * shorter than the film. Muted by default only if the episode sets volume 0.
 */
const MusicBed: React.FC<{track: AudioTrack}> = ({track}) => {
  const {fps} = useVideoConfig();
  const src = track.src.startsWith('http') ? track.src : staticFile(track.src);
  const trimBefore = track.trimBeforeSeconds
    ? Math.round(track.trimBeforeSeconds * fps)
    : 0;
  return (
    <Audio
      src={src}
      volume={track.volume ?? 0.15}
      loop={track.loop ?? true}
      trimBefore={trimBefore}
    />
  );
};

export const CinematicDoc: React.FC<CinematicProps> = ({
  title,
  scenes,
  sceneDurationInSeconds,
  overlapInSeconds,
  style: styleProp,
  outro,
  audio,
}) => {
  const {fps, height} = useVideoConfig();
  const style = {...DEFAULT_STYLE, ...styleProp};

  // A crossfade scene overlaps its predecessor by this many frames; a cut scene
  // uses none, so the timeline is exactly the sum of the shot lengths.
  const crossfadeFrames = Math.max(0, Math.round(overlapInSeconds * fps));
  const timeline = useMemo(
    () => buildTimeline(scenes, sceneDurationInSeconds, fps, crossfadeFrames),
    [scenes, sceneDurationInSeconds, fps, crossfadeFrames],
  );

  const bar = style.letterbox ? Math.round(height * LETTERBOX_RATIO) : 0;
  const outroFrames = outro ? Math.max(1, Math.round((outro.durationInSeconds ?? 3.5) * fps)) : 0;
  const firstSceneFrames = timeline.durations[0] ?? Math.round(fps * 2.5);

  return (
    <AbsoluteFill style={{backgroundColor: '#03040a'}}>
      {/* One track for the whole film, married to the composition timeline so
          it runs through every cut and under the end card. */}
      <MusicBed track={audio ?? DEFAULT_AUDIO} />

      {scenes.map((scene, index) => (
        <Sequence
          key={`${index}-${scene.image}-${scene.layout}`}
          from={timeline.starts[index]}
          durationInFrames={timeline.durations[index]}
          name={`Scene ${index + 1}`}
        >
          <CinematicScene
            scene={scene}
            index={index}
            sceneFrames={timeline.durations[index]}
            overlapIn={timeline.overlaps[index]}
            bar={bar}
            scrim={style.scrim}
          />
        </Sequence>
      ))}

      {outro ? (
        <Sequence
          from={timeline.totalFrames}
          durationInFrames={outroFrames}
          name="Outro"
        >
          <EndCard title={outro.title} />
        </Sequence>
      ) : null}

      {style.atmosphereOpacity > 0 ? <DustOverlay opacity={style.atmosphereOpacity} /> : null}
      {style.lightSweep ? <LightSweep /> : null}
      {style.vignette ? <Vignette /> : null}
      <Wordmark
        title={title}
        bar={bar}
        mode={style.wordmark}
        introFrames={firstSceneFrames}
      />
      {style.letterbox ? <Letterbox bar={bar} /> : null}
      <Curtain />
    </AbsoluteFill>
  );
};
