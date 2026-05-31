import { StyleSheet, Text, View } from 'react-native';

import type { AcousticProfile } from '@/api/types';
import { toPercent } from '@/coaching/format';
import { colors, radius, spacing } from '@/theme';

interface PersonaReadoutProps {
  personaName: string;
  styleMatch: number | null | undefined;
  acoustic: AcousticProfile | null | undefined;
  /** The speaker's target pace band [low, high] in syllables/sec, when known. */
  targetBand?: number[] | null;
}

/** Persona-path headline: "how much you sounded like the speaker" (style_match)
 *  plus the acoustic readout the score is built from — measured pace against the
 *  speaker's target band, pause count, and line coverage. */
export function PersonaReadout({
  personaName,
  styleMatch,
  acoustic,
  targetBand,
}: PersonaReadoutProps) {
  const band = targetBand && targetBand.length === 2 ? targetBand : null;
  const pace = acoustic ? acoustic.speech_rate_sps : null;
  const inBand = band && pace !== null ? pace >= band[0] && pace <= band[1] : null;
  const paceTone = inBand === null ? colors.textMuted : inBand ? colors.good : colors.warn;

  return (
    <View
      style={styles.card}
      accessibilityRole="text"
      accessibilityLabel={`Sounded like ${personaName}: ${toPercent(styleMatch)}`}
    >
      <Text style={styles.kicker}>SOUNDED LIKE {personaName.toUpperCase()}</Text>
      <Text style={styles.match}>{toPercent(styleMatch)}</Text>

      {acoustic ? (
        <View style={styles.metrics}>
          <View style={styles.metric}>
            <Text style={styles.metricLabel}>Your pace</Text>
            <Text style={[styles.metricValue, { color: paceTone }]}>
              {pace !== null ? `${pace.toFixed(1)} syll/s` : '—'}
            </Text>
            {band ? (
              <Text style={styles.metricHint}>
                target {band[0]}–{band[1]}
                {inBand ? ' ✓' : ''}
              </Text>
            ) : null}
          </View>

          <View style={styles.metric}>
            <Text style={styles.metricLabel}>Pauses</Text>
            <Text style={styles.metricValue}>{acoustic.pause_count}</Text>
          </View>

          <View style={styles.metric}>
            <Text style={styles.metricLabel}>Lines</Text>
            <Text style={styles.metricValue}>
              {acoustic.lines_recorded}/{acoustic.lines_expected}
            </Text>
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.accent,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    alignItems: 'center',
    gap: spacing.xs,
  },
  kicker: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1.5,
  },
  match: { color: colors.text, fontSize: 44, fontWeight: '800' },
  metrics: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignSelf: 'stretch',
    marginTop: spacing.sm,
    gap: spacing.md,
  },
  metric: { alignItems: 'center', gap: 2 },
  metricLabel: {
    color: colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  metricValue: { color: colors.text, fontSize: 18, fontWeight: '700' },
  metricHint: { color: colors.textMuted, fontSize: 11 },
});
