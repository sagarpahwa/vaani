import { describe, expect, it } from '@jest/globals';

import { countRecorded, lineState, toUtteranceInputs, type Recordings } from './recordings';

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

describe('lineState', () => {
  it('is recording for the active line regardless of prior capture', () => {
    expect(lineState(1, 1, {})).toBe('recording');
    expect(lineState(1, 1, { 1: 'AAA' })).toBe('recording');
  });

  it('is recorded when audio was captured and the line is idle', () => {
    expect(lineState(0, null, { 0: 'AAA' })).toBe('recorded');
  });

  it('is skipped when explicitly present and null', () => {
    expect(lineState(0, null, { 0: null })).toBe('skipped');
  });

  it('is idle when never touched', () => {
    expect(lineState(2, 1, { 0: 'AAA' })).toBe('idle');
    expect(lineState(0, null, {})).toBe('idle');
  });
});
