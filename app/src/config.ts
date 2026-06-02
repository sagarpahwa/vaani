/** Runtime configuration for the coaching app.
 *
 * The API base URL is read from `EXPO_PUBLIC_API_URL` (inlined at build time by
 * babel-preset-expo). When unset, we fall back to a platform-aware localhost:
 * the Android emulator can't reach the host via "localhost" — 10.0.2.2 is its
 * alias for the host loopback — while web/iOS use localhost directly.
 */
import { Platform } from 'react-native';

const DEFAULT_PORT = 8090;

function defaultBaseUrl(): string {
  if (Platform.OS === 'android') return `http://10.0.2.2:${DEFAULT_PORT}`;
  return `http://localhost:${DEFAULT_PORT}`;
}

function stripTrailingSlashes(url: string): string {
  return url.replace(/\/+$/, '');
}

export const API_BASE_URL = stripTrailingSlashes(
  process.env.EXPO_PUBLIC_API_URL || defaultBaseUrl(),
);

/** Demo account seeded in the mock DB (services/api/db/seed_data/users.json).
 *  The POC has no auth; every session is created for this user. */
export const DEMO_USER_ID = 'demo-user';

/** WebSocket origin for live progress events (http→ws, https→wss). */
export function wsBaseUrl(): string {
  return API_BASE_URL.replace(/^http/, 'ws');
}
