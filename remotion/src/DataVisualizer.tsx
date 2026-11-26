import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import './data.css';
import beat from '../public/beat.json';
import {BeatFrame} from './BeatFrame';
import {Beat1} from './beats/Beat1';
import {Beat2} from './beats/Beat2';
import {Beat3} from './beats/Beat3';
import {Beat4} from './beats/Beat4';
import {Beat5} from './beats/Beat5';

const META = [
  {kicker: 'THE HOOK', title: 'THE 50% TRAP', subtitle: "Why +50% doesn't undo −50%"},
  {kicker: 'THE SHRINKING BASE', title: 'TEN BLOCKS', subtitle: 'The denominator moved under your feet'},
  {kicker: 'THE ASYMMETRY CURVE', title: 'THE RECOVERY LADDER', subtitle: 'Losses and gains are not symmetric'},
  {kicker: 'REAL-WORLD TRAPS', title: 'THE SAME MISTAKE', subtitle: 'Discounts, taxes and rollercoasters'},
  {kicker: 'THE MENTAL RULE', title: 'THE SEESAW', subtitle: 'A small loss, a massive recovery'},
];
const FPS = 30;
const BEATS = beat.beats as unknown as Array<{id: number; start: number; end: number; triggers: Record<string, number>}>;

export const DataVisualizer: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const vertical = height > width;
  const t = frame / FPS;
  const index = Math.max(0, BEATS.findIndex((b) => t >= b.start && t < b.end));
  const b = BEATS[index]!;
  const local = t - b.start;
  const startF = Math.round(b.start * FPS);
  const localFrame = frame - startF;
  const meta = META[index];
  const zoom = interpolate(frame, [0, 5399], [1, 1.025]);

  return (
    <AbsoluteFill className={`stage${vertical ? ' portrait' : ''}`}>
      <Audio src={staticFile('vo_beat.mp3')} />
      <Sequence from={Math.round(BEATS[0].triggers.drop * FPS)} durationInFrames={26}><Audio src={staticFile('sfx/down.wav')} volume={.45} /></Sequence>
      <Sequence from={Math.round(BEATS[0].triggers.gain * FPS)} durationInFrames={28}><Audio src={staticFile('sfx/up.wav')} volume={.4} /></Sequence>
      <Sequence from={Math.round(BEATS[0].triggers.land * FPS)} durationInFrames={20}><Audio src={staticFile('sfx/thud.wav')} volume={.5} /></Sequence>
      <Sequence from={Math.round(BEATS[1].triggers.lose * FPS)} durationInFrames={24}><Audio src={staticFile('sfx/down.wav')} volume={.38} /></Sequence>
      <Sequence from={Math.round(BEATS[4].triggers.t50 * FPS)} durationInFrames={24}><Audio src={staticFile('sfx/up.wav')} volume={.36} /></Sequence>
      <div className="grain" />
      <div className="vignette" />
      <div className="camera" style={{transform: `scale(${zoom})`}}>
        {index === 0 ? (
          <BeatFrame index={1} {...meta} local={local} bare>
            <Beat1 />
          </BeatFrame>
        ) : (
          <BeatFrame index={index + 1} {...meta} local={local}>
            {index === 1 && <Beat2 />}
            {index === 2 && <Beat3 />}
            {index === 3 && <Beat4 />}
            {index === 4 && <Beat5 />}
          </BeatFrame>
        )}
      </div>
    </AbsoluteFill>
  );
};
