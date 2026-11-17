import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

const BLUE = '#58C4DD';
const INK = '#F5F5F5';

/**
 * "Dear Future" brand pill. Elegant and minimal: a translucent dark pill, wide
 * letter spacing, a soft drop shadow and one thin blue accent. Everything
 * outside the pill stays fully transparent so it can be muxed over any video.
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
          gap: 18,
          padding: '20px 34px 20px 26px',
          transform: `translateX(${offsetX}px)`,
          opacity,
          backgroundColor: 'rgba(10, 10, 10, 0.82)',
          border: '1px solid rgba(245, 245, 245, 0.18)',
          borderRadius: 999,
          backdropFilter: 'blur(2px)',
          boxShadow: '0 10px 28px rgba(0, 0, 0, 0.35)',
        }}
      >
        <div
          style={{
            width: 5,
            height: 34,
            borderRadius: 999,
            backgroundColor: BLUE,
            boxShadow: '0 0 10px rgba(88, 196, 221, 0.35)',
          }}
        />
        <div
          style={{
            fontFamily:
              '"Helvetica Neue", "Segoe UI", "DejaVu Sans", Arial, sans-serif',
            fontSize: 44,
            fontWeight: 400,
            letterSpacing: 2.5,
            color: INK,
            whiteSpace: 'nowrap',
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.75)',
          }}
        >
          Dear Future
        </div>
      </div>
    </AbsoluteFill>
  );
};
