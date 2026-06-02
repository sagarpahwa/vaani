import type { UtteranceInput } from '@/api/types';

/** Per-line captured audio: a base64 string, or `null` for a line the user
 *  skipped or couldn't record. The backend treats a null payload by deriving
 *  the transcript from the expected text, so a skipped line still gets coached. */
export type Recordings = Record<number, string | null>;

/** Build the submit payload: exactly one entry per script line (0..lineCount-1).
 *  Lines with no captured audio are sent as null (skipped). */
export function toUtteranceInputs(lineCount: number, recordings: Recordings): UtteranceInput[] {
  const inputs: UtteranceInput[] = [];
  for (let i = 0; i < lineCount; i += 1) {
    inputs.push({ line_index: i, audio_base64: recordings[i] ?? null });
  }
  return inputs;
}

/** Count lines that have a real (non-null) recording. */
export function countRecorded(recordings: Recordings): number {
  return Object.values(recordings).filter((v) => typeof v === 'string').length;
}

/** Display state of a single line in the recorder UI. */
export type LineState = 'idle' | 'recording' | 'recorded' | 'skipped';

/** Derive a line's display state from which line is mid-recording and what's
 *  been captured. A line is `skipped` only once explicitly skipped (present and
 *  null); a line never touched is `idle`. */
export function lineState(
  index: number,
  activeLine: number | null,
  recordings: Recordings,
): LineState {
  if (activeLine === index) return 'recording';
  if (typeof recordings[index] === 'string') return 'recorded';
  if (index in recordings) return 'skipped';
  return 'idle';
}
