import React from 'react';
import {Composition} from 'remotion';
import {Overlay} from './Overlay';

// 600x190 is rendered transparent and scaled down by assemble.py to ~26% of the
// video width, so it stays crisp on 1080p renders and readable on 480p ones.
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Overlay"
      component={Overlay}
      durationInFrames={180}
      fps={30}
      width={600}
      height={190}
    />
  );
};
