import { useSyncExternalStore } from 'react';

const noopSubscribe = () => () => {};

/** False during static web export (Node) and the first client render; true once
 *  hydrated on the client. Gate browser-only APIs (MediaRecorder, getUserMedia)
 *  behind this so they're never touched during server rendering. */
export function useClientReady(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}
