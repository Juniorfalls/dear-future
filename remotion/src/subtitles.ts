import type {Scene, Subtitle} from './types';

/** Longest a single subtitle chunk stays on screen. The reference swaps every
 *  ~0.5-2s, and anything slower reads as a paragraph rather than a subtitle. */
const MAX_CHUNK_SECONDS = 1.6;
/** Shortest a chunk can stay on screen and still be read. */
const MIN_CHUNK_SECONDS = 0.7;
/** Words per chunk before another chunk is forced in. */
const MAX_WORDS_PER_CHUNK = 6;

/**
 * Split one narration line into the short, punchy chunks the reference film
 * uses. Episodes that supply their own `captions` skip this entirely — it is the
 * fallback that keeps older scene files looking like the new style.
 *
 * Words are distributed evenly across the number of chunks the scene's duration
 * and word count call for, so a 2.5s shot of a 12-word line becomes two roughly
 * six-word cues rather than one line of text held for the whole shot.
 */
export const chunkCaption = (caption: string, durationInSeconds: number): Subtitle[] => {
  const text = caption.trim().replace(/\s+/g, ' ');
  if (!text) {
    return [];
  }

  const words = text.split(' ');
  const duration = Math.max(0.5, durationInSeconds);
  const chunksForTime = Math.round(duration / MAX_CHUNK_SECONDS);
  const chunksForWords = Math.ceil(words.length / MAX_WORDS_PER_CHUNK);
  const targetChunks = Math.max(1, chunksForTime, chunksForWords);

  const chunks: string[] = [];
  let cursor = 0;
  for (let index = 0; index < targetChunks; index += 1) {
    const chunksLeft = targetChunks - index;
    const wordsLeft = words.length - cursor;
    const take = Math.max(1, Math.round(wordsLeft / chunksLeft));
    chunks.push(words.slice(cursor, cursor + take).join(' '));
    cursor += take;
  }

  // Equal slices, never below the readable minimum. A very fast line simply
  // finishes early and leaves the frame clean, rather than flashing.
  const slice = Math.min(duration, Math.max(MIN_CHUNK_SECONDS, durationInSeconds / chunks.length));
  return chunks
    .map((chunk, index) => ({
      text: chunk,
      from: Number((index * slice).toFixed(2)),
      to: Number(Math.min(durationInSeconds, (index + 1) * slice).toFixed(2)),
    }))
    .filter((cue) => cue.to > cue.from);
};

/**
 * The cues for a scene: the authored ones when present, otherwise the caption
 * split to fit the scene duration.
 */
export const resolveCaptions = (scene: Scene, durationInSeconds: number): Subtitle[] =>
  scene.captions && scene.captions.length > 0
    ? scene.captions
    : chunkCaption(scene.caption, durationInSeconds);

/**
 * Accept the loose shapes that can reach us from JSON (Python writes numbers,
 * a hand-edited file might write strings) and drop anything unusable.
 */
export const normalizeCaptions = (value: unknown): Subtitle[] | undefined => {
  if (!Array.isArray(value)) {
    return undefined;
  }

  const cues: Subtitle[] = [];
  for (const raw of value) {
    if (!raw || typeof raw !== 'object') continue;
    const cue = raw as Record<string, unknown>;
    if (typeof cue.text !== 'string' || !cue.text.trim()) continue;
    const from = Number(cue.from);
    const to = Number(cue.to);
    if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) continue;
    cues.push({text: cue.text.trim(), from: Math.max(0, from), to});
  }

  return cues.length > 0 ? cues.sort((a, b) => a.from - b.from) : undefined;
};
