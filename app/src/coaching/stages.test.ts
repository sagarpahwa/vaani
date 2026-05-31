import { describe, expect, it } from '@jest/globals';

import { STAGES, stageLabel } from './stages';

describe('STAGES', () => {
  it('mirrors the backend timeline exactly (services/api/routes/events.py)', () => {
    expect([...STAGES]).toEqual([
      'received',
      'transcribing',
      'analyzing',
      'scoring',
      'generating_feedback',
    ]);
  });
});

describe('stageLabel', () => {
  it('maps known stages to friendly copy', () => {
    expect(stageLabel('transcribing')).toBe('Transcribing your speech');
    expect(stageLabel('generating_feedback')).toBe('Writing your coaching');
  });

  it('falls back to the raw key for unknown stages', () => {
    expect(stageLabel('done')).toBe('done');
    expect(stageLabel('error')).toBe('error');
  });
});
