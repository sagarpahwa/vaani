import { describe, it, expect } from '@jest/globals';

import { API_BASE_URL, wsBaseUrl } from './config';

describe('config', () => {
  it('exposes an http(s) API base URL with no trailing slash', () => {
    expect(API_BASE_URL).toMatch(/^https?:\/\//);
    expect(API_BASE_URL.endsWith('/')).toBe(false);
  });

  it('derives the ws(s) origin by swapping the scheme', () => {
    expect(wsBaseUrl()).toBe(API_BASE_URL.replace(/^http/, 'ws'));
    expect(wsBaseUrl()).toMatch(/^wss?:\/\//);
  });
});
