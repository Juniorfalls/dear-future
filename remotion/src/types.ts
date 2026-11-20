/**
 * How one shot is framed. The virtual presenter replaces the coloured
 * placeholder box in `host_full` and `host_pip` once the host video exists.
 *
 * - `host_full`  — presenter only, b-roll hidden (openings, chapter cards)
 * - `host_pip`   — b-roll full screen, presenter in a bottom-left PiP
 * - `broll_only` — b-roll full screen, no presenter
 */
export type SceneLayout = 'host_full' | 'host_pip' | 'broll_only';

export const SCENE_LAYOUTS: readonly SceneLayout[] = [
  'host_full',
  'host_pip',
  'broll_only',
];

export type Scene = {
  /**
   * Full-bleed background still (any size, it is cropped to cover). Generated
   * by Pollinations.ai and committed under remotion/public/episodes/. Empty
   * for a `host_full` scene, which never shows b-roll.
   */
  image: string;
  /** Shot framing: presenter full-frame, presenter PiP, or b-roll alone. */
  layout: SceneLayout;
  /** Documentary narration line, burned into the lower third. */
  caption: string;
  /** Optional small line above the caption, e.g. "Chapter One". */
  kicker?: string;
  /** Optional per-scene hold in seconds; falls back to the composition default. */
  durationInSeconds?: number;
};


export type CinematicProps = {
  title: string;
  scenes: Scene[];
  /** How long each scene holds, in seconds. */
  sceneDurationInSeconds: number;
  /** How long the crossfade between two scenes lasts, in seconds. */
  overlapInSeconds: number;
  width: number;
  height: number;
  fps: number;
};
