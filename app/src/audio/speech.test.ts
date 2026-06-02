import { beforeEach, describe, expect, it, jest } from '@jest/globals';

import * as Speech from 'expo-speech';

import { speakText, stopSpeech } from './speech';

jest.mock('expo-speech', () => ({
  speak: jest.fn(),
  stop: jest.fn(() => Promise.resolve()),
}));

const speak = Speech.speak as jest.MockedFunction<typeof Speech.speak>;
const stop = Speech.stop as jest.MockedFunction<typeof Speech.stop>;

describe('speakText', () => {
  beforeEach(() => {
    speak.mockClear();
    stop.mockClear();
  });

  it('stops any current speech, then speaks the trimmed text', () => {
    speakText('  hello world  ');
    expect(stop).toHaveBeenCalledTimes(1);
    expect(speak).toHaveBeenCalledTimes(1);
    expect(speak.mock.calls[0][0]).toBe('hello world');
  });

  it('is a no-op for blank text', () => {
    speakText('   ');
    expect(speak).not.toHaveBeenCalled();
  });

  it('routes done, stopped, and error all back to the caller so a toggle can reset', () => {
    const onDone = jest.fn();
    const onError = jest.fn();
    speakText('hi', { onDone, onError });
    const options = speak.mock.calls[0][1]!;
    options.onDone?.();
    options.onStopped?.();
    expect(onDone).toHaveBeenCalledTimes(2);
    options.onError?.(new Error('boom'));
    expect(onError).toHaveBeenCalledTimes(1);
  });
});

describe('stopSpeech', () => {
  it('stops in-progress speech', () => {
    stop.mockClear();
    stopSpeech();
    expect(stop).toHaveBeenCalledTimes(1);
  });
});
