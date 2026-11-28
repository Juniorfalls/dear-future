import {Composition} from 'remotion';
import {AnimatedAnimalScene} from './AnimatedAnimalScene';
import {SeriesIntro, SeriesOutro} from './SeriesCard';
import episode from '../public/animal.json';

const FPS = 30;
// The timeline length is data-driven: scripts/generate_voiceover.py rewrites
// `duration` after it measures the Kokoro take, so a longer animal fits.
const durationInFrames = Math.max(30, Math.round((episode as {duration: number}).duration * FPS));

export const RemotionRoot = () => (
  <>
    <Composition
      id="AnimalScene"
      component={AnimatedAnimalScene}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition id="SeriesIntro" component={SeriesIntro} durationInFrames={90} fps={FPS} width={1920} height={1080} />
    <Composition id="SeriesOutro" component={SeriesOutro} durationInFrames={300} fps={FPS} width={1920} height={1080} />
    <Composition
      id="AnimalSceneVertical"
      component={AnimatedAnimalScene}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={1080}
      height={1920}
    />
  </>
);
