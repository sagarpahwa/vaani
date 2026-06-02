import { describe, it, expect } from '@jest/globals';

import { colors } from '@/theme';

import {
  clamp01,
  deltaBand,
  deltaColor,
  formatClock,
  initials,
  scoreBand,
  scoreColor,
  severityColor,
  signedPercent,
  toPercent,
} from './format';

describe('clamp01', () => {
  it('clamps into [0,1] and maps NaN to 0', () => {
    expect(clamp01(-0.5)).toBe(0);
    expect(clamp01(1.5)).toBe(1);
    expect(clamp01(0.42)).toBe(0.42);
    expect(clamp01(NaN)).toBe(0);
  });
});

describe('toPercent', () => {
  it('renders a 0–1 score as a whole percent', () => {
    expect(toPercent(0.844)).toBe('84%');
    expect(toPercent(0)).toBe('0%');
    expect(toPercent(1)).toBe('100%');
    expect(toPercent(1.4)).toBe('100%');
  });

  it('renders an em dash when the score is absent', () => {
    expect(toPercent(null)).toBe('—');
    expect(toPercent(undefined)).toBe('—');
    expect(toPercent(NaN)).toBe('—');
  });
});

describe('scoreBand / scoreColor', () => {
  it('buckets by threshold', () => {
    expect(scoreBand(0.9)).toBe('good');
    expect(scoreBand(0.75)).toBe('good');
    expect(scoreBand(0.6)).toBe('warn');
    expect(scoreBand(0.3)).toBe('bad');
    expect(scoreBand(null)).toBe('bad');
  });

  it('maps bands to theme colors', () => {
    expect(scoreColor(0.9)).toBe(colors.good);
    expect(scoreColor(0.6)).toBe(colors.warn);
    expect(scoreColor(0.1)).toBe(colors.bad);
  });
});

describe('signedPercent / deltaBand', () => {
  it('signs and rounds the delta', () => {
    expect(signedPercent(0.05)).toBe('+5%');
    expect(signedPercent(-0.03)).toBe('-3%');
    expect(signedPercent(0)).toBe('±0%');
    expect(signedPercent(0.004)).toBe('±0%'); // rounds to zero
    expect(signedPercent(null)).toBe('—');
  });

  it('bands the delta by sign', () => {
    expect(deltaBand(0.05)).toBe('good');
    expect(deltaBand(-0.05)).toBe('bad');
    expect(deltaBand(0.004)).toBe('warn');
    expect(deltaColor(0.05)).toBe(colors.good);
    expect(deltaColor(-0.05)).toBe(colors.bad);
    expect(deltaColor(0)).toBe(colors.textMuted);
  });
});

describe('formatClock', () => {
  it('formats milliseconds as m:ss', () => {
    expect(formatClock(0)).toBe('0:00');
    expect(formatClock(5000)).toBe('0:05');
    expect(formatClock(65000)).toBe('1:05');
    expect(formatClock(600000)).toBe('10:00');
  });

  it('floors partial seconds and treats nullish/negative as zero', () => {
    expect(formatClock(1999)).toBe('0:01');
    expect(formatClock(null)).toBe('0:00');
    expect(formatClock(-500)).toBe('0:00');
  });
});

describe('initials', () => {
  it('takes first + last initial for a multi-word name', () => {
    expect(initials('Steve Jobs')).toBe('SJ');
    expect(initials('Jensen Huang')).toBe('JH');
    expect(initials('Martin Luther King')).toBe('MK'); // first + last, not middle
  });

  it('takes the first two letters of a single-word name', () => {
    expect(initials('Oprah')).toBe('OP');
    expect(initials('x')).toBe('X'); // shorter than two letters
  });

  it('is whitespace-tolerant and falls back to ? when empty', () => {
    expect(initials('  Steve   Jobs  ')).toBe('SJ');
    expect(initials('')).toBe('?');
    expect(initials('   ')).toBe('?');
  });
});

describe('severityColor', () => {
  it('maps severities case-insensitively with a muted fallback', () => {
    expect(severityColor('high')).toBe(colors.bad);
    expect(severityColor('MEDIUM')).toBe(colors.warn);
    expect(severityColor('low')).toBe(colors.textMuted);
    expect(severityColor('whatever')).toBe(colors.textMuted);
  });
});
