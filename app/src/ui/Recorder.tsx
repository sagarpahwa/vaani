import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { UtteranceInput } from '@/api/types';
import { lineState, toUtteranceInputs, type Recordings } from '@/audio/recordings';
import type { RecorderError } from '@/audio/useRecorder';
import { useRecorder } from '@/audio/useRecorder';
import { colors, spacing } from '@/theme';

import { Banner } from './Banner';
import { Button } from './Button';
import { LineRecorder } from './LineRecorder';

interface RecorderProps {
  lines: string[];
  /** Hand the captured payload (one entry per line, skipped lines null) to the
   *  caller, which stashes it and routes to the processing screen. */
  onSubmit: (inputs: UtteranceInput[]) => void;
}

/** Microphone-dependent guidance for a recorder error, or null when fine. */
function micNotice(error: RecorderError): string | null {
  switch (error) {
    case 'denied':
      return 'Microphone access was denied — you can still skip lines and get coached from the script text.';
    case 'unavailable':
      return 'No microphone is available — you can still skip lines and get coached from the script text.';
    case 'failed':
      return 'That take could not be saved. Try recording again, or skip the line.';
    default:
      return null;
  }
}

/** Smart recording surface: one row per line, capture via expo-audio, then
 *  submit every line (recorded or skipped) for coaching. Must be mounted only
 *  on the client (gate with useClientReady) since it touches audio hooks. */
export function Recorder({ lines, onSubmit }: RecorderProps) {
  const recorder = useRecorder();
  const [recordings, setRecordings] = useState<Recordings>({});
  const [activeLine, setActiveLine] = useState<number | null>(null);

  async function handleRecord(index: number) {
    const started = await recorder.start();
    if (started) setActiveLine(index);
  }

  async function handleStop(index: number) {
    const base64 = await recorder.stop();
    setRecordings((prev) => ({ ...prev, [index]: base64 }));
    setActiveLine(null);
  }

  function handleSkip(index: number) {
    setRecordings((prev) => ({ ...prev, [index]: null }));
  }

  function handleSubmit() {
    onSubmit(toUtteranceInputs(lines.length, recordings));
  }

  const notice = micNotice(recorder.error);
  const busy = activeLine !== null;

  return (
    <View style={styles.container}>
      <Text style={styles.hint}>
        Record each line, or skip it to be coached from the script text. You can re-record any line
        before getting feedback.
      </Text>

      {notice ? <Banner tone={recorder.error === 'failed' ? 'error' : 'info'} message={notice} /> : null}

      <View style={styles.lines}>
        {lines.map((text, index) => (
          <LineRecorder
            key={index}
            index={index}
            text={text}
            state={lineState(index, activeLine, recordings)}
            durationMs={activeLine === index ? recorder.durationMs : undefined}
            disabled={busy && activeLine !== index}
            onRecord={() => handleRecord(index)}
            onStop={() => handleStop(index)}
            onSkip={() => handleSkip(index)}
          />
        ))}
      </View>

      <Button label="Get feedback" onPress={handleSubmit} disabled={busy} testID="get-feedback" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.md },
  hint: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
  lines: { gap: spacing.sm },
});
