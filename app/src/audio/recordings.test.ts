import { describe, expect, it } from '@jest/globals';

import { countRecorded, toUtteranceInputs, type Recordings } from './recordings';

describe('toUtteranceInputs', () => {
  it('emits one entry per line, in line order', () => {
    const recordings: Recordings = { 0: 'AAA', 2: 'CCC' };
    expect(toUtteranceInputs(3, recordings)).toEqual([
      { line_index: 0, audio_base64: 'AAA' },
      { line_index: 1, audio_base64: null },
      { line_index: 2, audio_base64: 'CCC' },
    ]);
  });

  it('sends all-null when nothing was recorded (skip-everything path)', () => {
    expect(toUtteranceInputs(2, {})).toEqual([
      { line_index: 0, audio_base64: null },
      { line_index: 1, audio_base64: null },
    ]);
  });

  it('returns an empty payload for a zero-line script', () => {
    expect(toUtteranceInputs(0, {})).toEqual([]);
  });
});

describe('countRecorded', () => {
  it('counts only non-null entries', () => {
    expect(countRecorded({ 0: 'AAA', 1: null, 2: 'CCC' })).toBe(2);
  });

  it('is zero for an empty map', () => {
    expect(countRecorded({})).toBe(0);
  });
});
