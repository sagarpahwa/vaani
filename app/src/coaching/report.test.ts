import { describe, expect, it } from '@jest/globals';

import type { Correction } from '@/api/types';

import { flaggedLineNumbers } from './report';

function correction(line_index: number): Correction {
  return {
    line_index,
    focus_capability: 'pace',
    original_text: 'o',
    corrected_text: 'c',
    explanation: 'e',
  };
}

describe('flaggedLineNumbers', () => {
  it('is empty when there are no corrections', () => {
    expect(flaggedLineNumbers([])).toEqual([]);
  });

  it('returns de-duped, sorted, 1-based line numbers', () => {
    expect(flaggedLineNumbers([correction(2), correction(0), correction(2)])).toEqual([1, 3]);
  });
});
