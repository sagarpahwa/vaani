import { useState } from 'react';

import { speakText, stopSpeech } from '@/audio/speech';
import { Button } from '@/ui/Button';

interface ReadAloudButtonProps {
  text: string;
}

/** Speak the full written feedback aloud. Toggles to "Stop" while speaking and
 *  resets when speech finishes. Render-safe during static export — speech is only
 *  invoked from the press handler, never at render. */
export function ReadAloudButton({ text }: ReadAloudButtonProps) {
  const [speaking, setSpeaking] = useState(false);

  if (!text.trim()) return null;

  const onPress = () => {
    if (speaking) {
      stopSpeech();
      setSpeaking(false);
      return;
    }
    setSpeaking(true);
    speakText(text, { onDone: () => setSpeaking(false), onError: () => setSpeaking(false) });
  };

  return (
    <Button
      label={speaking ? 'Stop reading' : 'Read feedback aloud'}
      variant="secondary"
      testID="read-aloud"
      onPress={onPress}
    />
  );
}
