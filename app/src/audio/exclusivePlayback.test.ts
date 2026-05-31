import { beforeEach, describe, expect, it, jest } from '@jest/globals';

import { pauseExclusive, playExclusive, resetActivePlayer } from './exclusivePlayback';

function fakePlayer() {
  return {
    play: jest.fn<() => void>(),
    pause: jest.fn<() => void>(),
    seekTo: jest.fn<(seconds: number) => void>(),
  };
}

describe('exclusive playback', () => {
  beforeEach(() => resetActivePlayer());

  it('plays from the start when nothing else is active', () => {
    const a = fakePlayer();
    playExclusive(a);
    expect(a.seekTo).toHaveBeenCalledWith(0);
    expect(a.play).toHaveBeenCalledTimes(1);
    expect(a.pause).not.toHaveBeenCalled();
  });

  it('pauses the previously-active clip before starting another (even across cards)', () => {
    const card1 = fakePlayer();
    const card2 = fakePlayer();
    playExclusive(card1);
    playExclusive(card2); // a different card's player
    expect(card1.pause).toHaveBeenCalledTimes(1);
    expect(card2.play).toHaveBeenCalledTimes(1);
  });

  it('does not pause the player it is about to (re)start', () => {
    const a = fakePlayer();
    playExclusive(a);
    playExclusive(a); // same player again
    expect(a.pause).not.toHaveBeenCalled();
    expect(a.play).toHaveBeenCalledTimes(2);
  });

  it('releases the slot on pause so a later play stops nothing stale', () => {
    const a = fakePlayer();
    const b = fakePlayer();
    playExclusive(a);
    pauseExclusive(a); // clears the active slot
    expect(a.pause).toHaveBeenCalledTimes(1);
    playExclusive(b);
    expect(a.pause).toHaveBeenCalledTimes(1); // not paused again — it wasn't active
    expect(b.play).toHaveBeenCalledTimes(1);
  });
});
