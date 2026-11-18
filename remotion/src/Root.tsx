import React from 'react';
import {CalculateMetadataFunction, Composition} from 'remotion';
import {CinematicDoc} from './CinematicDoc';
import type {CinematicProps} from './types';
import scenesData from '../data/scenes.json';

export const defaultProps: CinematicProps = {
  title: scenesData.title,
  scenes: scenesData.scenes,
  sceneDurationInSeconds: 6,
  overlapInSeconds: 1,
  fps: 30,
  width: 1920,
  height: 1080,
};

export const calculateMetadata: CalculateMetadataFunction<CinematicProps> = ({props}) => {
  const fps = props.fps ?? defaultProps.fps;
  const sceneFrames = Math.max(1, Math.round((props.sceneDurationInSeconds ?? 6) * fps));
  const overlap = Math.min(
    sceneFrames - 1,
    Math.round((props.overlapInSeconds ?? 1) * fps),
  );
  const step = sceneFrames - overlap;
  const count = Math.max(1, props.scenes.length);

  return {
    durationInFrames: Math.max(sceneFrames, (count - 1) * step + sceneFrames),
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
