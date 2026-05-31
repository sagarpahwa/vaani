import { StyleSheet, Text, View } from 'react-native';

import { clamp01, scoreColor, toPercent } from '@/coaching/format';
import { colors, radius, spacing } from '@/theme';

interface ScoreBarProps {
  label: string;
  score: number | null | undefined;
  /** Optional signed delta string (e.g. "+5%") rendered beside the percent. */
  deltaText?: string;
  deltaColor?: string;
}

export function ScoreBar({ label, score, deltaText, deltaColor }: ScoreBarProps) {
  const pct = clamp01(score ?? 0) * 100;
  return (
    <View style={styles.row} accessibilityRole="text" accessibilityLabel={`${label} ${toPercent(score)}`}>
      <View style={styles.header}>
        <Text style={styles.label}>{label}</Text>
        <View style={styles.values}>
          {deltaText ? <Text style={[styles.delta, { color: deltaColor }]}>{deltaText}</Text> : null}
          <Text style={styles.pct}>{toPercent(score)}</Text>
        </View>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct}%`, backgroundColor: scoreColor(score) }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { gap: spacing.xs },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  label: { color: colors.text, fontSize: 14, fontWeight: '600' },
  values: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  delta: { fontSize: 13, fontWeight: '700' },
  pct: { color: colors.textMuted, fontSize: 14, fontWeight: '700', minWidth: 44, textAlign: 'right' },
  track: {
    height: 8,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.sm,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: radius.sm },
});
