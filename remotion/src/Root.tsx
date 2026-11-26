import {Composition} from 'remotion';
import {DataVisualizer} from './DataVisualizer';

export const RemotionRoot = () => (
  <Composition
    id="DataVisualizer"
    component={DataVisualizer}
    durationInFrames={750}
    fps={30}
    width={1920}
    height={1080}
  />
);
