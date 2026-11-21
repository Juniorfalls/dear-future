import type {
  AudioTrack,
  CinematicProps,
  FilmStyle,
  Grade,
  Outro,
  Scene,
  Subtitle,
} from './types';
import {GRADES} from './types';
import {normalizeCaptions} from './subtitles';

type RawObject = Record<string, unknown>;

const DEFAULT_SCENE_SECONDS = 2.5;

const asObject = (value: unknown): RawObject =>
  value && typeof value === 'object' ? (value as RawObject) : {};
const asString = (value: unknown): string => (typeof value === 'string' ? value : '');
const asNumber = (value: unknown): number | undefined =>
  typeof value === 'number' && Number.isFinite(value) ? value : undefined;
const asArray = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const ratioSize = (ratio: string | undefined): {width: number; height: number} => {
  if (ratio === '9:16') return {width: 1080, height: 1920};
  if (ratio === '1:1') return {width: 1080, height: 1080};
  if (ratio === '4:5') return {width: 1080, height: 1350};
  return {width: 1920, height: 1080};
};

const normalizeAudio = (value: unknown): AudioTrack | undefined => {
  const audio = asObject(value);
  const src = asString(audio.src);
  if (!src) return undefined;
  return {
    src,
    volume: asNumber(audio.volume),
    loop: typeof audio.loop === 'boolean' ? audio.loop : undefined,
    trimBeforeSeconds: asNumber(audio.trimBeforeSeconds),
  };
};

const normalizeOutro = (value: unknown): Outro | undefined => {
  const outro = asObject(value);
  const title = asString(outro.title);
  if (!title) return undefined;
  return {title, durationInSeconds: asNumber(outro.durationInSeconds)};
};

const oneCuePerShot = (text: string, seconds: number): Subtitle[] | undefined => {
  if (!text.trim()) return undefined;
  // The storyboard plans one subtitle per panel. Hold it for the shot instead
  // of re-chunking it into the documentary's rapid cue style.
  return [{text, from: 0.2, to: Math.max(0.7, seconds - 0.2)}];
};

/**
 * The original scenes.json shape (12th Street documentary). Layout keys are now
 * ignored: the engine is full-screen media only.
 */
export const normalizeDocumentary = (raw: unknown): CinematicProps => {
  const data = asObject(raw);
  const scenes: Scene[] = asArray(data.scenes).map((rawScene) => {
    const scene = asObject(rawScene);
    const voice = asObject(scene.voice);
    const voiceSrc = asString(voice.src);
    return {
      image: asString(scene.image_url) || asString(scene.image),
      caption: asString(scene.text) || asString(scene.caption),
      captions: normalizeCaptions(scene.captions),
      transition: scene.transition === 'crossfade' ? 'crossfade' : 'cut',
      grade: GRADES.includes(scene.grade as Grade) ? (scene.grade as Grade) : undefined,
      durationInSeconds: asNumber(scene.durationInSeconds),
      voice: voiceSrc
        ? {
            src: voiceSrc,
            durationInSeconds: asNumber(voice.durationInSeconds),
            volume: asNumber(voice.volume),
          }
        : undefined,
    };
  });

  return {
    title: asString(data.title) || '12th Street',
    scenes,
    sceneDurationInSeconds: asNumber(data.sceneDurationInSeconds) ?? DEFAULT_SCENE_SECONDS,
    overlapInSeconds: asNumber(data.overlapInSeconds) ?? 0.8,
    fps: asNumber(data.fps) ?? 30,
    width: asNumber(data.width) ?? 1920,
    height: asNumber(data.height) ?? 1080,
    style: asObject(data.style) as FilmStyle,
    outro: normalizeOutro(data.outro),
    audio: normalizeAudio(data.audio),
  };
};

/**
 * series.json + episode.json (the ai-anime-series shape, adapted for horror)
 * -> CinematicDoc props.
 *
 * Every shot in episode.parts[].shots becomes one full-screen scene. A shot can
 * carry `video` (a clip already generated in Colab) and/or `image` (a still).
 * Without either, the composition holds on a dark stage and shows the subtitle,
 * which keeps the timing reviewable before any GPU work is done.
 */
export const normalizeHorror = (seriesRaw: unknown, episodeRaw: unknown): CinematicProps => {
  const series = asObject(seriesRaw);
  const episode = asObject(episodeRaw);
  const shots = asArray(episode.parts).flatMap((part) => asArray(asObject(part).shots));

  const ratio = asString(series.ratio) || '16:9';
  const size = ratioSize(ratio);
  const total = shots.reduce<number>(
    (sum, rawShot) => sum + (asNumber(asObject(rawShot).dur) ?? 0),
    0,
  );
  const fallbackSeconds = shots.length > 0 ? total / shots.length : DEFAULT_SCENE_SECONDS;

  const scenes: Scene[] = shots.map((rawShot) => {
    const shot = asObject(rawShot);
    const seconds = asNumber(shot.dur) ?? fallbackSeconds;
    const caption = asString(shot.caption) || asString(shot.text);
    const video = asString(shot.video);
    return {
      image: asString(shot.image) || asString(shot.panel_image),
      video: video ? {src: video} : undefined,
      caption,
      captions: normalizeCaptions(shot.captions) ?? oneCuePerShot(caption, seconds),
      transition: 'cut',
      grade: GRADES.includes(shot.grade as Grade) ? (shot.grade as Grade) : 'dread',
      durationInSeconds: seconds,
    };
  });

  const defaultStyle: FilmStyle = {
    letterbox: true,
    atmosphereOpacity: 0.08,
    lightSweep: false,
    vignette: true,
    wordmark: 'intro',
    scrim: 0.3,
  };

  return {
    title:
      asString(series.title) || asString(episode.title) || 'The Hollow Hour',
    scenes,
    sceneDurationInSeconds: total > 0 ? total / scenes.length : DEFAULT_SCENE_SECONDS,
    overlapInSeconds: 0.4,
    fps: asNumber(series.fps) ?? 30,
    width: asNumber(episode.width) ?? size.width,
    height: asNumber(episode.height) ?? size.height,
    style: {...defaultStyle, ...asObject(series.film_style)},
    outro: normalizeOutro(episode.outro),
    audio: normalizeAudio(series.audio ?? episode.audio),
  };
};
