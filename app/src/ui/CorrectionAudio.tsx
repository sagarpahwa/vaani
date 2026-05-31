import { type AudioPlayer, type AudioStatus, useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';
import { StyleSheet, View } from 'react-native';

import { audioUrl } from '@/api/client';
import { pauseExclusive, playExclusive } from '@/audio/exclusivePlayback';
import { spacing } from '@/theme';
import { Button } from '@/ui/Button';

interface CorrectionAudioProps {
  userAudioKey?: string | null;
  idealAudioKey?: string | null;
}

/** A/B playback for one correction: the learner's take vs the ideal voice.
 *  Mount only behind `useClientReady` — `useAudioPlayer` touches browser globals
 *  on web and would crash during static export.
 *
 *  Each button toggles play/pause; play() is gated on `isLoaded` so a press
 *  before the source is ready is a no-op rather than a silent, stuck player.
 *  Starting any clip stops whatever was playing — across both buttons here and
 *  every other card — via the shared `exclusivePlayback` registry, so at most
 *  one clip is ever audible. */
export function CorrectionAudio({ userAudioKey, idealAudioKey }: CorrectionAudioProps) {
  const userPlayer = useAudioPlayer(userAudioKey ? audioUrl(userAudioKey) : null);
  const idealPlayer = useAudioPlayer(idealAudioKey ? audioUrl(idealAudioKey) : null);
  const userStatus = useAudioPlayerStatus(userPlayer);
  const idealStatus = useAudioPlayerStatus(idealPlayer);

  if (!userAudioKey && !idealAudioKey) return null;

  const toggle = (player: AudioPlayer, status: AudioStatus) => {
    if (status.playing) {
      pauseExclusive(player);
      return;
    }
    if (!status.isLoaded) return; // source not ready yet — avoid a silent stuck play()
    playExclusive(player); // stops any other clip (this card or another) first
  };

  return (
    <View style={styles.row}>
      {userAudioKey ? (
        <Button
          label={userStatus.playing ? '⏸ Your take' : '▶ Your take'}
          variant="secondary"
          testID="play-user"
          onPress={() => toggle(userPlayer, userStatus)}
        />
      ) : null}
      {idealAudioKey ? (
        <Button
          label={idealStatus.playing ? '⏸ Ideal' : '▶ Ideal'}
          variant="secondary"
          testID="play-ideal"
          onPress={() => toggle(idealPlayer, idealStatus)}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: spacing.sm, flexWrap: 'wrap' },
});
