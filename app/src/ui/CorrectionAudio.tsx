import { useAudioPlayer } from 'expo-audio';
import { StyleSheet, View } from 'react-native';

import { audioUrl } from '@/api/client';
import { spacing } from '@/theme';
import { Button } from '@/ui/Button';

interface CorrectionAudioProps {
  userAudioKey?: string | null;
  idealAudioKey?: string | null;
}

/** A/B playback for one correction: the learner's take vs the ideal voice.
 *  Mount only behind `useClientReady` — `useAudioPlayer` touches browser globals
 *  on web and would crash during static export. */
export function CorrectionAudio({ userAudioKey, idealAudioKey }: CorrectionAudioProps) {
  const userPlayer = useAudioPlayer(userAudioKey ? audioUrl(userAudioKey) : null);
  const idealPlayer = useAudioPlayer(idealAudioKey ? audioUrl(idealAudioKey) : null);

  if (!userAudioKey && !idealAudioKey) return null;

  return (
    <View style={styles.row}>
      {userAudioKey ? (
        <Button
          label="▶ Your take"
          variant="secondary"
          testID="play-user"
          onPress={() => {
            void userPlayer.seekTo(0);
            userPlayer.play();
          }}
        />
      ) : null}
      {idealAudioKey ? (
        <Button
          label="▶ Ideal"
          variant="secondary"
          testID="play-ideal"
          onPress={() => {
            void idealPlayer.seekTo(0);
            idealPlayer.play();
          }}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
});
