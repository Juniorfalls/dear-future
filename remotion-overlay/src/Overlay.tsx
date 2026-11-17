import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const BLUE = '#58C4DD';
const INK = '#EBEBEB';

/**
 * "Math Explained" lower-third card. Everything outside the rounded card stays
 * fully transparent so the render can be muxed over the Manim video.
 */
export const Overlay: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();

  // Slide in once, then hold: the clip is looped by assemble.py, so a calm hold
  // reads better than a card that keeps popping back in.
  const enter = spring({frame, fps, config: {damping: 200}, durationInFrames: 22});
  const opacity = interpolate(frame, [0, 14], [0, 1], {extrapolateRight: 'clamp'});
  const offsetX = interpolate(enter, [0, 1], [90, 0]);

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div
        style={{
          position: 'absolute',
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          padding: '18px 28px',
          transform: `translateX(${offsetX}px)`,
          opacity,
          backgroundColor: 'rgba(16, 16, 16, 0.92)',
          border: '2px solid rgba(235, 235, 235, 0.16)',
          borderRadius: 20,
          boxShadow: '0 12px 32px rgba(0, 0, 0, 0.45)',
        }}
      >
        <div
          style={{
            width: 10,
            height: 48,
            borderRadius: 5,
            backgroundColor: BLUE,
          }}
        />
        <div
          style={{
            fontFamily: 'sans-serif',
            fontSize: 46,
            fontWeight: 700,
            letterSpacing: 1.5,
            color: INK,
            whiteSpace: 'nowrap',
          }}
        >
          Math Explained
        </div>
      </div>
    </AbsoluteFill>
  );
};
