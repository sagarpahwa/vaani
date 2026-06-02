/** App-wide single-clip playback.
 *
 *  Every correction card mounts its own `useAudioPlayer` pair, so nothing in
 *  expo-audio stops card 1's "Your take" when card 2's "Ideal" starts — they
 *  play mixed together. This module is the one shared registry they all route
 *  through: starting any clip first pauses whatever was playing *anywhere*, so
 *  at most one clip is ever audible.
 */

/** The slice of expo-audio's `AudioPlayer` exclusive playback actually uses. */
export interface PlayablePlayer {
  play: () => void;
  pause: () => void;
  seekTo: (seconds: number) => void | Promise<void>;
}

let active: PlayablePlayer | null = null;

/** Start `player` from the top, after stopping whatever was playing anywhere. */
export function playExclusive(player: PlayablePlayer): void {
  if (active && active !== player) {
    // The active player may belong to an unmounted card and already be
    // released (navigate away → back); pausing it then throws. Don't let a
    // stale reference block the new clip from starting.
    try {
      active.pause();
    } catch {
      /* released player — nothing to stop */
    }
  }
  active = player;
  void player.seekTo(0);
  player.play();
}

/** Pause `player`; if it held the app-wide slot, release it. */
export function pauseExclusive(player: PlayablePlayer): void {
  player.pause();
  if (active === player) active = null;
}

/** Test seam: forget the active player without pausing it. */
export function resetActivePlayer(): void {
  active = null;
}
