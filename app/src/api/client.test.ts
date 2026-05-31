import { afterEach, describe, it, expect, jest } from '@jest/globals';

import { API_BASE_URL } from '../config';
import { api, ApiError, audioUrl, sessionEventsUrl } from './client';

type FetchArgs = [string, RequestInit];

function mockFetch(body: unknown, ok = true, status = 200) {
  const fetchMock = jest.fn<(...args: unknown[]) => Promise<unknown>>().mockResolvedValue({
    ok,
    status,
    statusText: ok ? 'OK' : 'Error',
    json: async () => body,
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

afterEach(() => {
  jest.restoreAllMocks();
});

describe('api client requests', () => {
  it('GETs /scripts and returns the parsed body', async () => {
    const f = mockFetch([{ script_id: 's1', title: 'Intro', line_count: 3 }]);
    const out = await api.listScripts();
    expect(f.mock.calls[0][0]).toBe(`${API_BASE_URL}/scripts`);
    expect(out[0].script_id).toBe('s1');
  });

  it('POSTs createSession with a JSON body and content-type', async () => {
    const f = mockFetch({ session_id: 'x' });
    await api.createSession({ user_id: 'u', mode: 'guided', script_id: 's1' });
    const [url, init] = f.mock.calls[0] as FetchArgs;
    expect(url).toBe(`${API_BASE_URL}/sessions`);
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({
      user_id: 'u',
      mode: 'guided',
      script_id: 's1',
    });
  });

  it('wraps utterances in the expected envelope', async () => {
    const f = mockFetch({ session_id: 'x', status: 'scored' });
    await api.submitUtterances('sid', [{ line_index: 0, audio_base64: 'AA==' }]);
    const [url, init] = f.mock.calls[0] as FetchArgs;
    expect(url).toBe(`${API_BASE_URL}/sessions/sid/utterances`);
    expect(JSON.parse(init.body as string)).toEqual({
      utterances: [{ line_index: 0, audio_base64: 'AA==' }],
    });
  });

  it('encodes path parameters', async () => {
    const f = mockFetch({});
    await api.getScript('a/b id');
    expect(f.mock.calls[0][0]).toBe(`${API_BASE_URL}/scripts/a%2Fb%20id`);
  });

  it('raises ApiError carrying status and backend detail on failure', async () => {
    mockFetch({ detail: 'session not found' }, false, 404);
    await expect(api.getSession('nope')).rejects.toEqual(
      expect.objectContaining({ name: 'ApiError', status: 404, message: 'session not found' }),
    );
  });

  it('ApiError is an Error subclass', () => {
    expect(new ApiError(500, 'boom')).toBeInstanceOf(Error);
  });
});

describe('url helpers', () => {
  it('audioUrl encodes segments but preserves slashes', () => {
    expect(audioUrl('sessions/abc/utterances/0.wav')).toBe(
      `${API_BASE_URL}/audio/sessions/abc/utterances/0.wav`,
    );
  });

  it('sessionEventsUrl uses the ws scheme', () => {
    expect(sessionEventsUrl('sid')).toBe(
      `${API_BASE_URL.replace(/^http/, 'ws')}/sessions/sid/events`,
    );
  });
});
