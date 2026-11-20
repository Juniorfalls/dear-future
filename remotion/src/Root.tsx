import React from 'react';
import {CalculateMetadataFunction, Composition, staticFile} from 'remotion';
import {getAudioDuration} from '@remotion/media-utils';
import {CinematicDoc} from './CinematicDoc';
import type {
  AudioTrack,
  CinematicProps,
  FilmStyle,
  Grade,
  Outro,
  Scene,
  SceneLayout,
  SceneTransition,
} from './types';
import {GRADES, SCENE_LAYOUTS} from './types';
import {normalizeCaptions} from './subtitles';
import {buildTimeline} from './timeline';
import scenesData from '../data/scenes.json';

/** Shot length used when neither the scene nor the episode sets one. */
const DEFAULT_SCENE_SECONDS = 2.5;

/**
 * Silence kept after the last word of a line, matched to TAIL_PADDING in
 * generate_voice.py. The shot must outlast the voice; the cut should still feel
 * quick.
 */
const VOICE_TAIL_SECONDS = 0.5;

type RawScene = {
  video_url?: string;
  image_url?: string;
  image?: string;
  text?: string;
  caption?: string;
  layout?: string;
  transition?: string;
  grade?: string;
  captions?: unknown;
  kicker?: string;
  durationInSeconds?: number;
  voice?: {src?: string; durationInSeconds?: number; volume?: number};
};

const episode = scenesData as {
  title?: string;
  sceneDurationInSeconds?: number;
  style?: FilmStyle;
  outro?: {title?: string; durationInSeconds?: number};
  audio?: AudioTrack;
  scenes: RawScene[];
};

/**
 * scenes.json is written by fetch_media.py in the {video_url, image_url, text,
 * layout, transition, grade, captions} schema; older hand-written files use
 * {image, caption} and no video. Normalise here so the Studio preview matches
 * what render.js feeds the composition.
 */
const scenes: Scene[] = episode.scenes.map((scene) => {
  const layout = SCENE_LAYOUTS.includes(scene.layout as SceneLayout)
    ? (scene.layout as SceneLayout)
    : 'broll_only';
  const grade = GRADES.includes(scene.grade as Grade) ? (scene.grade as Grade) : undefined;
  const transition: SceneTransition =
    scene.transition === 'crossfade' ? 'crossfade' : 'cut';
  const voice =
    scene.voice && typeof scene.voice.src === 'string' && scene.voice.src
      ? {
          src: scene.voice.src,
          durationInSeconds: scene.voice.durationInSeconds,
          volume:
            typeof scene.voice.volume === 'number'
              ? Math.min(1, Math.max(0, scene.voice.volume))
              : undefined,
        }
      : undefined;

  return {
    video_url: scene.video_url,
    image: scene.image_url ?? scene.image ?? '',
    layout,
    caption: (scene.text ?? scene.caption ?? '') as string,
    captions: normalizeCaptions(scene.captions),
    transition,
    grade,
    kicker: scene.kicker,
    durationInSeconds: scene.durationInSeconds,
    voice,
  };
});

const outro: Outro | undefined =
  episode.outro && typeof episode.outro.title === 'string'
    ? {
        title: episode.outro.title,
        durationInSeconds:
          typeof episode.outro.durationInSeconds === 'number'
            ? episode.outro.durationInSeconds
            : undefined,
      }
    : undefined;

/** Only a real file name is accepted, so a typo cannot silence the film. */
const audio: AudioTrack | undefined =
  episode.audio && typeof episode.audio.src === 'string' && episode.audio.src
    ? {
        src: episode.audio.src,
        volume:
          typeof episode.audio.volume === 'number'
            ? Math.min(1, Math.max(0, episode.audio.volume))
            : undefined,
        loop: typeof episode.audio.loop === 'boolean' ? episode.audio.loop : undefined,
        trimBeforeSeconds:
          typeof episode.audio.trimBeforeSeconds === 'number'
            ? Math.max(0, episode.audio.trimBeforeSeconds)
            : undefined,
      }
    : undefined;

export const defaultProps: CinematicProps = {
  title: episode.title ?? 'Before You',
  scenes,
  sceneDurationInSeconds: episode.sceneDurationInSeconds ?? DEFAULT_SCENE_SECONDS,
  overlapInSeconds: 0.8,
  fps: 30,
  width: 1920,
  height: 1080,
  style: episode.style ?? {},
  outro,
  audio,
};

export const calculateMetadata: CalculateMetadataFunction<CinematicProps> = async ({
  props,
}) => {
  const fps = props.fps ?? defaultProps.fps;
  const crossfadeFrames = Math.max(0, Math.round((props.overlapInSeconds ?? 0.8) * fps));

  // Narration drives the cut. The wav is measured here rather than trusted from
  // JSON, so replacing a voice file re-times the film on the next render; a
  // missing or unreadable file falls back to the duration the generator wrote.
  const scenes = await Promise.all(
    props.scenes.map(async (scene) => {
      if (!scene.voice?.src) {
        return scene;
      }
      try {
        const src = scene.voice.src.startsWith('http')
          ? scene.voice.src
          : staticFile(scene.voice.src);
        const seconds = await getAudioDuration(src);
        return {
          ...scene,
          durationInSeconds: Number((seconds + VOICE_TAIL_SECONDS).toFixed(3)),
        };
      } catch {
        return scene;
      }
    }),
  );

  const timeline = buildTimeline(
    scenes,
    props.sceneDurationInSeconds ?? DEFAULT_SCENE_SECONDS,
    fps,
    crossfadeFrames,
  );
  const outroFrames = props.outro
    ? Math.max(1, Math.round((props.outro.durationInSeconds ?? 3.5) * fps))
    : 0;

  return {
    durationInFrames: Math.max(1, timeline.totalFrames + outroFrames),
    fps,
    width: props.width ?? defaultProps.width,
    height: props.height ?? defaultProps.height,
    // Hand the re-measured durations to the component so the sequences and the
    // composition length always agree.
    props: {...props, scenes},
  };
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="CinematicDoc"
    component={CinematicDoc}
    durationInFrames={180}
    fps={defaultProps.fps}
    width={defaultProps.width}
    height={defaultProps.height}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
