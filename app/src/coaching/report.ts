import type { Correction } from '@/api/types';

/** 1-based line numbers that have a correction, de-duped and sorted ascending.
 *  Used to tell the learner which lines to focus on when re-recording. */
export function flaggedLineNumbers(corrections: Correction[]): number[] {
  const set = new Set<number>();
  for (const c of corrections) set.add(c.line_index + 1);
  return [...set].sort((a, b) => a - b);
}
