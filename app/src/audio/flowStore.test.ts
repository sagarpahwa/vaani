import { afterEach, describe, expect, it } from '@jest/globals';

import {
  clearSubmissions,
  dropSubmission,
  peekSubmission,
  stashSubmission,
} from './flowStore';

afterEach(() => clearSubmissions());

describe('flowStore', () => {
  it('returns null for an unknown session', () => {
    expect(peekSubmission('nope')).toBeNull();
  });

  it('stashes and peeks without consuming (safe for double-invoked effects)', () => {
    stashSubmission('s1', { kind: 'submit', inputs: [{ line_index: 0, audio_base64: 'A' }] });
    expect(peekSubmission('s1')).toEqual({
      kind: 'submit',
      inputs: [{ line_index: 0, audio_base64: 'A' }],
    });
    // A second peek still finds it — peeking does not remove.
    expect(peekSubmission('s1')).not.toBeNull();
  });

  it('drops a submission once accepted', () => {
    stashSubmission('s2', { kind: 'retry', inputs: [] });
    dropSubmission('s2');
    expect(peekSubmission('s2')).toBeNull();
  });

  it('keys submissions by session id', () => {
    stashSubmission('a', { kind: 'submit', inputs: [] });
    stashSubmission('b', { kind: 'retry', inputs: [] });
    expect(peekSubmission('a')?.kind).toBe('submit');
    expect(peekSubmission('b')?.kind).toBe('retry');
  });
});
