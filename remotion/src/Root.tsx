import {Composition} from 'remotion';
import {AnimalDocumentary} from './AnimalDocumentary';
import episode from '../public/animal.json';

const FPS = 30;
// The timeline length is data-driven: scripts/generate_voiceover.py rewrites
// `duration` after it measures the Kokoro take, so a longer animal fits.
const durationInFrames = Math.max(30, Math.round((episode as {duration: number}).duration * FPS));

export const RemotionRoot = () => (
  <>
    <Composition
      id="AnimalDocLandscape"
      component={AnimalDocumentary}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={1920}
      height={1080}
    />
    <Composition
      id="AnimalDocVertical"
      component={AnimalDocumentary}
      durationInFrames={durationInFrames}
      fps={FPS}
      width={1080}
      height={1920}
    />
  </>
);
