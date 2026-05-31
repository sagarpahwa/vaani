import { describe, it, expect } from '@jest/globals';

import {
  CANONICAL_CAPABILITIES,
  capabilityDescription,
  capabilityLabel,
  orderedCapabilityScores,
} from './capabilities';

describe('capabilityLabel', () => {
  it('labels known capabilities', () => {
    expect(capabilityLabel('clarity')).toBe('Clarity');
    expect(capabilityLabel('conciseness')).toBe('Conciseness');
  });

  it('title-cases unknown keys as a fallback', () => {
    expect(capabilityLabel('vocal_variety')).toBe('Vocal Variety');
    expect(capabilityLabel('eye-contact')).toBe('Eye Contact');
  });
});

describe('capabilityDescription', () => {
  it('describes known capabilities and returns empty for unknown', () => {
    expect(capabilityDescription('pace').length).toBeGreaterThan(0);
    expect(capabilityDescription('nope')).toBe('');
  });
});

describe('orderedCapabilityScores', () => {
  it('returns canonical capabilities in canonical order', () => {
    const scores = { conciseness: 0.5, clarity: 0.9, pace: 0.7 };
    expect(orderedCapabilityScores(scores).map(([k]) => k)).toEqual([
      'clarity',
      'pace',
      'conciseness',
    ]);
  });

  it('appends unknown keys alphabetically after canonical ones', () => {
    const scores = { gusto: 0.4, clarity: 0.9, alpha: 0.3 };
    expect(orderedCapabilityScores(scores).map(([k]) => k)).toEqual(['clarity', 'alpha', 'gusto']);
  });

  it('keeps every canonical capability available for a full score map', () => {
    const full = Object.fromEntries(CANONICAL_CAPABILITIES.map((c) => [c, 0.8]));
    expect(orderedCapabilityScores(full)).toHaveLength(CANONICAL_CAPABILITIES.length);
  });
});
