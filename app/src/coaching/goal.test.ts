import { describe, it, expect } from '@jest/globals';

import {
  buildGoalSignature,
  DEFAULT_GOAL_FORM,
  OCCASIONS,
  occasionFromProfile,
  type GoalForm,
} from './goal';

describe('buildGoalSignature', () => {
  it('maps the default form to a complete signature', () => {
    const gs = buildGoalSignature(DEFAULT_GOAL_FORM);
    expect(gs.objective).toBe(DEFAULT_GOAL_FORM.objective);
    expect(gs.occasion).toBe(DEFAULT_GOAL_FORM.occasion);
    expect(gs.language).toBe('en');
    expect(gs.duration_seconds).toBeNull();
  });

  it('trims fields and drops empty ones', () => {
    const form: GoalForm = {
      objective: '  persuade  ',
      occasion: '',
      audience: '',
      style: '',
      language: '',
      durationSeconds: 120,
    };
    const gs = buildGoalSignature(form);
    expect(gs.objective).toBe('persuade');
    expect(gs.occasion).toBeUndefined();
    expect(gs.audience).toBeUndefined();
    expect(gs.language).toBe('en'); // empty language defaults
    expect(gs.duration_seconds).toBe(120);
  });
});

describe('occasionFromProfile', () => {
  it('matches a profile occasion to a known option', () => {
    expect(occasionFromProfile({ occasion: 'A formal Investor meeting' })).toBe('investor pitch');
  });

  it('falls back to the default when missing or unmatched', () => {
    expect(occasionFromProfile(null)).toBe(DEFAULT_GOAL_FORM.occasion);
    expect(occasionFromProfile({ occasion: 42 as unknown as string })).toBe(
      DEFAULT_GOAL_FORM.occasion,
    );
    expect(occasionFromProfile({ something: 'else' })).toBe(DEFAULT_GOAL_FORM.occasion);
  });
});

describe('goal options ↔ backend boost keywords', () => {
  // These values must contain the keywords the backend _BOOST_RULES match,
  // otherwise the goal would not re-weight the rubric.
  it('includes the canonical occasion keywords', () => {
    const values = OCCASIONS.map((o) => o.value).join(' ');
    for (const kw of ['investor', 'wedding', 'toast', 'interview', 'lecture', 'keynote', 'standup']) {
      expect(values).toContain(kw);
    }
  });
});
