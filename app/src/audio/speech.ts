import * as Speech from 'expo-speech';

interface SpeakHandlers {
  onDone?: () => void;
  onError?: () => void;
}

/** Speak text aloud (expo-speech: Web Speech API on web, native TTS on device),
 *  replacing any in-progress speech. No-op on blank text. The handlers fire when
 *  speech ends — done, stopped, or errored — so a toggle can reset itself. */
export function speakText(text: string, handlers?: SpeakHandlers): void {
  const trimmed = text.trim();
  if (!trimmed) return;
  void Speech.stop();
  Speech.speak(trimmed, {
    onDone: handlers?.onDone,
    onStopped: handlers?.onDone,
    onError: handlers?.onError ?? handlers?.onDone,
  });
}

/** Stop any in-progress speech. */
export function stopSpeech(): void {
  void Speech.stop();
}
