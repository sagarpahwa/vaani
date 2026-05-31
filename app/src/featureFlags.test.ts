import { describe, it, expect } from '@jest/globals';

import { toBool } from './featureFlags';

describe('toBool', () => {
  it.each(['1', 'true', 'TRUE', 'yes', 'on', 'On'])('treats %s as true', (raw: string) => {
    expect(toBool(raw, false)).toBe(true);
  });

  it.each(['0', 'false', 'no', 'off', 'nonsense'])('treats %s as false', (raw: string) => {
    expect(toBool(raw, true)).toBe(false);
  });

  it('uses the fallback when the value is missing or empty', () => {
    expect(toBool(undefined, true)).toBe(true);
    expect(toBool(undefined, false)).toBe(false);
    expect(toBool('', true)).toBe(true);
  });
});
