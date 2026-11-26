import {Composition} from 'remotion';
import {MathClassroom} from './MathClassroom';

export const RemotionRoot = () => (
  <Composition
    id="MathClassroom"
    component={MathClassroom}
    durationInFrames={450}
    fps={30}
    width={1920}
    height={1080}
  />
);
