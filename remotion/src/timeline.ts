import type {Scene} from './types';

export type Timeline = {
  /** Length of each scene in frames. */
  durations: number[];
  /** First frame of each scene. */
  starts: number[];
  /** Frames each scene overlaps its predecessor (0 for a hard cut). */
  overlaps: number[];
  /** Frame where the last scene ends. */
  totalFrames: number;
};

export const sceneFrames = (
  scene: Scene,
  fallbackSeconds: number,
  fps: number,
): number => Math.max(1, Math.round((scene.durationInSeconds ?? fallbackSeconds) * fps));

/**
 * Lay the scenes on the timeline.
 *
 * A `crossfade` scene starts early so it can fade in over the tail of the
 * previous shot. A `cut` scene — the default, and what the reference film uses
 * exclusively — starts on the frame after the previous one ends, so no two
 * scenes are ever visible at once.
 */
export const buildTimeline = (
  scenes: Scene[],
  fallbackSeconds: number,
  fps: number,
  crossfadeFrames: number,
): Timeline => {
  const durations = scenes.map((scene) => sceneFrames(scene, fallbackSeconds, fps));

  const overlaps = scenes.map((scene, index) => {
    if (index === 0 || scene.transition !== 'crossfade') {
      return 0;
    }
    // Never let a fade eat a whole neighbouring shot.
    return Math.max(
      0,
      Math.min(crossfadeFrames, durations[index] - 1, durations[index - 1] - 1),
    );
  });

  const starts: number[] = [];
  let totalFrames = 0;
  durations.forEach((duration, index) => {
    const start = index === 0 ? 0 : starts[index - 1] + durations[index - 1] - overlaps[index];
    starts.push(start);
    totalFrames = Math.max(totalFrames, start + duration);
  });

  return {durations, starts, overlaps, totalFrames};
};
