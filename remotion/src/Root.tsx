import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {CinematicDoc} from './CinematicDoc';
import type {
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

type RawScene = {
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
};

const episode = scenesData as {
  title?: string;
  sceneDurationInSeconds?: number;
  style?: FilmStyle;
  outro?: {title?: string; durationInSeconds?: number};
  scenes: RawScene[];
};

/**
 * scenes.json is written by generate_video.py in the {image_url, text, layout,
 * transition, grade, captions} schema; older hand-written files use {image,
 * caption} and none of the newer keys. Normalise here so the Studio preview
 * matches what render.js feeds the composition.
 */
const scenes: Scene[] = episode.scenes.map((scene) => {
  const layout = SCENE_LAYOUTS.includes(scene.layout as SceneLayout)
    ? (scene.layout as SceneLayout)
    : 'broll_only';
  const grade = GRADES.includes(scene.grade as Grade) ? (scene.grade as Grade) : undefined;
  const transition: SceneTransition =
    scene.transition === 'crossfade' ? 'crossfade' : 'cut';

  return {
    image: scene.image_url ?? scene.image ?? '',
    layout,
    caption: (scene.text ?? scene.caption ?? '') as string,
    captions: normalizeCaptions(scene.captions),
    transition,
    grade,
    kicker: scene.kicker,
    durationInSeconds: scene.durationInSeconds,
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

export const defaultProps: CinematicProps = {
  title: episode.title ?? '12th Street',
  scenes,
  sceneDurationInSeconds: episode.sceneDurationInSeconds ?? DEFAULT_SCENE_SECONDS,
  overlapInSeconds: 0.8,
  fps: 30,
  width: 1920,
  height: 1080,
  style: episode.style ?? {},
  outro,
};

export const calculateMetadata: CalculateMetadataFunction<CinematicProps> = ({props}) => {
  const fps = props.fps ?? defaultProps.fps;
  const crossfadeFrames = Math.max(0, Math.round((props.overlapInSeconds ?? 0.8) * fps));
  const timeline = buildTimeline(
    props.scenes,
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
