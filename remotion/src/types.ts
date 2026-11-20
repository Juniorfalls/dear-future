/**
 * How one shot is framed. The presenter clip in public/host/presenter.mp4 fills
 * the frame in `host_full` and sits in a rounded corner inset in `host_pip`.
 *
 * - `host_full`  — presenter only, b-roll hidden (intros and outros)
 * - `host_pip`   — b-roll full screen, presenter in a bottom-left PiP
 * - `broll_only` — b-roll full screen, no presenter
 */
export type SceneLayout = 'host_full' | 'host_pip' | 'broll_only';

export const SCENE_LAYOUTS: readonly SceneLayout[] = [
  'host_full',
  'host_pip',
  'broll_only',
];

/**
 * How a scene enters. `cut` (the default) replaces the previous shot on a single
 * frame, which is what the reference film does; `crossfade` fades in over the
 * tail of the previous shot.
 */
export type SceneTransition = 'cut' | 'crossfade';

/**
 * Location-coded colour grade, measured from the reference film: `cold` for the
 * night interiors (cool blue, low luminance), `warm` for everything lit by day
 * (muted amber), `neutral` for the rest.
 */
export type Grade = 'cold' | 'warm' | 'neutral';

export const GRADES: readonly Grade[] = ['cold', 'warm', 'neutral'];

/** One burned-in subtitle chunk, timed relative to the start of its scene. */
export type Subtitle = {
  text: string;
  /** Seconds from the start of the scene. */
  from: number;
  /** Seconds from the start of the scene. */
  to: number;
};

/** Narration for one scene, spoken by generate_voice.py. */
export type Voice = {
  /** File under remotion/public/ or a full URL. */
  src: string;
  /** Length of the spoken line only, without the shot's tail padding. */
  durationInSeconds?: number;
  /** 0-1; defaults to 1 so the line sits above the music bed. */
  volume?: number;
};

export type Scene = {
  /**
   * Full-bleed background video (stock footage, gameplay, trailers). A path
   * relative to remotion/public or a full URL. Rendered with OffthreadVideo.
   * When set, `image` becomes the floating subject overlay instead of b-roll.
   */
  video_url?: string;
  /**
   * Background still for legacy episodes, or the subject overlay when
   * `video_url` is present. Generated stills live under remotion/public.
   * Empty for a `host_full` scene, which never shows b-roll.
   */
  image: string;
  /** Shot framing: presenter full-frame, presenter PiP, or b-roll alone. */
  layout: SceneLayout;
  /**
   * Full narration line for the scene. Chunked automatically when `captions` is
   * absent, so older episode files still render.
   */
  caption: string;
  /** Explicit subtitle chunks; overrides the automatic chunking of `caption`. */
  captions?: Subtitle[];
  /** Transition into this scene. Defaults to a hard cut. */
  transition?: SceneTransition;
  /** Colour grade for this shot. Defaults to `neutral`. */
  grade?: Grade;
  /** Optional small line above the subtitle, e.g. "Chapter One". */
  kicker?: string;
  /** Optional per-scene hold in seconds; falls back to the composition default. */
  durationInSeconds?: number;
  /**
   * Narration for this shot. When present the shot is sized to the spoken line
   * plus a short tail (calculateMetadata re-measures the wav), and the file is
   * played at the start of the shot.
   */
  voice?: Voice;
};

/**
 * Film-wide presentation switches, so one episode can follow the reference's
 * clean look while an older episode keeps the letterbox and dust.
 */
export type FilmStyle = {
  /** Black cinematic bars top and bottom. */
  letterbox?: boolean;
  /** Strength of the dust/fog layer (0 disables it). */
  atmosphereOpacity?: number;
  /** The diagonal light shaft that crosses the frame every few seconds. */
  lightSweep?: boolean;
  /** Radial vignette over the whole film. */
  vignette?: boolean;
  /**
   * `all` keeps the title top-left for the whole film, `intro` only for the
   * opening scene, `none` hides it.
   */
  wordmark?: 'all' | 'intro' | 'none';
  /**
   * Strength of the dark gradient behind the subtitles (0 = outline only, the
   * reference look; 1 = a near-solid black lower third).
   */
  scrim?: number;
};

/** Title card after the last scene. */
export type Outro = {
  title: string;
  /** How long the card holds, in seconds. */
  durationInSeconds?: number;
};

/**
 * The music bed. It plays under the whole film, from the first frame to the
 * last, so the reference's “no silence” quality holds across cuts and the end
 * card.
 */
export type AudioTrack = {
  /** File under remotion/public/ (e.g. "audio/bg_music.mp3") or a full URL. */
  src: string;
  /** 0-1. Kept low so a future voice-over can sit on top. */
  volume?: number;
  /** Repeat the track when it is shorter than the film. */
  loop?: boolean;
  /** Seconds into the track to start, e.g. to skip an intro. */
  trimBeforeSeconds?: number;
};

export type CinematicProps = {
  title: string;
  scenes: Scene[];
  /** How long each scene holds, in seconds. */
  sceneDurationInSeconds: number;
  /** How long a `crossfade` transition lasts, in seconds. */
  overlapInSeconds: number;
  width: number;
  height: number;
  fps: number;
  style?: FilmStyle;
  outro?: Outro;
  /** Music bed; falls back to the bundled track at 0.15 when omitted. */
  audio?: AudioTrack;
};
