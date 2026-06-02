/** Minimal feature-flag + remote-config shell.
 *
 * POC flags are read from static `EXPO_PUBLIC_FLAG_*` env vars (inlined at build
 * time by babel-preset-expo — access must be static for the inlining to work).
 * This is the seam where a real remote-config provider (LaunchDarkly, GrowthBook,
 * etc.) would plug in later; the rest of the app only depends on `isEnabled`.
 */

export function toBool(raw: string | undefined, fallback: boolean): boolean {
  if (raw == null || raw === '') return fallback;
  const v = raw.toLowerCase();
  return v === '1' || v === 'true' || v === 'yes' || v === 'on';
}

export const flags = {
  /** Mode B: user-provided script coaching. */
  modeB: toBool(process.env.EXPO_PUBLIC_FLAG_MODE_B, true),
  /** Live WebSocket progress timeline during processing. */
  liveProgress: toBool(process.env.EXPO_PUBLIC_FLAG_LIVE_PROGRESS, true),
  /** Read-aloud of full feedback via expo-speech. */
  readAloud: toBool(process.env.EXPO_PUBLIC_FLAG_READ_ALOUD, true),
} as const;

export type FeatureFlag = keyof typeof flags;

export function isEnabled(flag: FeatureFlag): boolean {
  return flags[flag];
}
