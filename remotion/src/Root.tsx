import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {CinematicDoc} from './CinematicDoc';
import type {CinematicProps, Scene} from './types';
import scenesData from '../data/scenes.json';

/**
 * scenes.json is written by generate_video.py in the {image_url, text} schema;
 * older hand-written files use {image, caption}. Normalise both here so the
 * Studio preview matches what render.js feeds the composition.
 */
const rawScenes = scenesData.scenes as Array<{
  image_url?: string;
  image?: string;
  text?: string;
  caption?: string;
  kicker?: string;
  durationInSeconds?: number;
}>;

const scenes: Scene[] = rawScenes.map((scene) => ({
  image: (scene.image_url ?? scene.image) as string,
  caption: (scene.text ?? scene.caption) as string,
  kicker: scene.kicker,
  durationInSeconds: scene.durationInSeconds,
}));

export const defaultProps: CinematicProps = {
  title: scenesData.title,
  scenes,
  sceneDurationInSeconds: 6,
  overlapInSeconds: 1,
  fps: 30,
  width: 1920,
  height: 1080,
};

export const calculateMetadata: CalculateMetadataFunction<CinematicProps> = ({props}) => {
  const fps = props.fps ?? defaultProps.fps;
  const durations = props.scenes.map((scene) =>
    Math.max(1, Math.round((scene.durationInSeconds ?? props.sceneDurationInSeconds ?? 6) * fps)),
  );
  const overlap = Math.min(
    Math.round((props.overlapInSeconds ?? 1) * fps),
    Math.min(...durations) - 1,
  );
  const total = durations.reduce((sum, duration) => sum + duration, 0) - overlap * (durations.length - 1);

  return {
    durationInFrames: Math.max(durations[0], total),
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
