import {
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
} from 'expo-audio';
import { useCallback, useState } from 'react';

import { bytesToBase64 } from './base64';
import { readBytes } from './readBytes';

export type RecorderError = null | 'denied' | 'unavailable' | 'failed';

export interface RecorderControls {
  isRecording: boolean;
  durationMs: number;
  error: RecorderError;
  /** Begin capturing; sets `error` instead of throwing on permission/availability problems. */
  start: () => Promise<void>;
  /** Stop and resolve to the captured audio as base64, or null when unavailable. */
  stop: () => Promise<string | null>;
}

/** Cross-platform single-clip recorder. expo-audio drives capture on both web
 *  (MediaRecorder) and native; only the URI→bytes step is platform-split
 *  (see readBytes). Callers must gate the component behind useClientReady so the
 *  underlying hooks never run during static web export. */
export function useRecorder(): RecorderControls {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const state = useAudioRecorderState(recorder);
  const [error, setError] = useState<RecorderError>(null);

  const start = useCallback(async () => {
    setError(null);
    try {
      const permission = await requestRecordingPermissionsAsync();
      if (!permission.granted) {
        setError('denied');
        return;
      }
      try {
        await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      } catch {
        // best-effort: web has no audio-session mode to set
      }
      await recorder.prepareToRecordAsync();
      recorder.record();
    } catch {
      setError('unavailable');
    }
  }, [recorder]);

  const stop = useCallback(async (): Promise<string | null> => {
    try {
      await recorder.stop();
      const { uri } = recorder;
      if (!uri) return null;
      return bytesToBase64(await readBytes(uri));
    } catch {
      setError('failed');
      return null;
    }
  }, [recorder]);

  return { isRecording: state.isRecording, durationMs: state.durationMillis, error, start, stop };
}
