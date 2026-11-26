import {Composition} from 'remotion';
import {DataVisualizer} from './DataVisualizer';

export const RemotionRoot = () => (
  <>
    <Composition id="DataVisualizer" component={DataVisualizer} durationInFrames={5400} fps={30} width={1920} height={1080} />
    <Composition id="DataVisualizerVertical" component={DataVisualizer} durationInFrames={5400} fps={30} width={1080} height={1920} />
  </>
);
