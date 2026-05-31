/** Typed HTTP client for the coaching backend.
 *
 * Thin wrapper over `fetch` (available on web, native, and in jest-expo). Every
 * call returns the parsed JSON body or throws `ApiError` carrying the HTTP
 * status and the backend's `detail` message.
 */
import { API_BASE_URL, wsBaseUrl } from '../config';
import type {
  CreateSessionRequest,
  PersonaDetail,
  PersonaSummary,
  ScriptDetail,
  ScriptSummary,
  SessionDetail,
  UtteranceInput,
} from './types';

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body && typeof body.detail === 'string') detail = body.detail;
    } catch {
      // non-JSON error body — keep the status-text fallback
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  listScripts: (): Promise<ScriptSummary[]> => request('/scripts'),

  getScript: (scriptId: string): Promise<ScriptDetail> =>
    request(`/scripts/${encodeURIComponent(scriptId)}`),

  listPersonas: (): Promise<PersonaSummary[]> => request('/personas'),

  getPersona: (personaId: string): Promise<PersonaDetail> =>
    request(`/personas/${encodeURIComponent(personaId)}`),

  createSession: (body: CreateSessionRequest): Promise<SessionDetail> =>
    request('/sessions', { method: 'POST', body: JSON.stringify(body) }),

  getSession: (sessionId: string): Promise<SessionDetail> =>
    request(`/sessions/${encodeURIComponent(sessionId)}`),

  submitUtterances: (
    sessionId: string,
    utterances: UtteranceInput[],
  ): Promise<SessionDetail> =>
    request(`/sessions/${encodeURIComponent(sessionId)}/utterances`, {
      method: 'POST',
      body: JSON.stringify({ utterances }),
    }),

  retrySession: (
    sessionId: string,
    utterances: UtteranceInput[],
  ): Promise<SessionDetail> =>
    request(`/sessions/${encodeURIComponent(sessionId)}/retry`, {
      method: 'POST',
      body: JSON.stringify({ utterances }),
    }),
};

/** Turn any thrown value into a user-facing message. `ApiError.message` already
 *  carries the backend `detail`; a bare `TypeError` from `fetch` means the
 *  server was unreachable. */
export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof TypeError) return 'Cannot reach the coaching server (is it running on :8090?).';
  if (e instanceof Error) return e.message;
  return 'Something went wrong.';
}

/** Absolute URL for a stored audio artifact (object-store key). */
export function audioUrl(key: string): string {
  const encoded = key.split('/').map(encodeURIComponent).join('/');
  return `${API_BASE_URL}/audio/${encoded}`;
}

/** WebSocket URL for a session's live progress timeline. */
export function sessionEventsUrl(sessionId: string): string {
  return `${wsBaseUrl()}/sessions/${encodeURIComponent(sessionId)}/events`;
}
