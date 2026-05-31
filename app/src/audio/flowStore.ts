import type { UtteranceInput } from '@/api/types';

/** Whether a pending submission is a session's first attempt or a retry. */
export type SubmissionKind = 'submit' | 'retry';

export interface PendingSubmission {
  kind: SubmissionKind;
  inputs: UtteranceInput[];
}

/** In-memory handoff for recorded audio between the record screen and the
 *  processing screen. Base64 audio can't ride in URL params, so the record
 *  screen stashes the payload here and navigates with only the sessionId; the
 *  processing screen reads it and submits. Not persisted — a hard reload of
 *  /processing finds nothing (processing.tsx recovers by re-fetching). */
const pending = new Map<string, PendingSubmission>();

export function stashSubmission(sessionId: string, submission: PendingSubmission): void {
  pending.set(sessionId, submission);
}

/** Read the pending submission without removing it (safe under React Strict
 *  Mode's double-invoked effects, which would otherwise consume it twice). */
export function peekSubmission(sessionId: string): PendingSubmission | null {
  return pending.get(sessionId) ?? null;
}

/** Discard a session's pending submission once it has been accepted. */
export function dropSubmission(sessionId: string): void {
  pending.delete(sessionId);
}

/** Clear every pending submission (test isolation). */
export function clearSubmissions(): void {
  pending.clear();
}
