export type Scene = {
  /**
   * Full-bleed background still (any size, it is cropped to cover). Generated
   * by Pollinations.ai and committed under remotion/public/episodes/.
   */
  image: string;
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
