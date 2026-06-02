import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { capabilityLabel } from '@/coaching/capabilities';
import { colors, radius, spacing } from '@/theme';

interface CorrectionCardProps {
  index: number;
  focusCapability: string;
  originalText: string;
  correctedText: string;
  explanation: string;
  /** Optional playback controls (A/B user-vs-ideal), injected by the screen so
   *  this card stays presentational and SSR-safe. */
  actions?: ReactNode;
}

/** One line-by-line correction: what you said vs. a stronger version, why, and
 *  optional audio controls. */
export function CorrectionCard({
  index,
  focusCapability,
  originalText,
  correctedText,
  explanation,
  actions,
}: CorrectionCardProps) {
  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Text style={styles.num}>Line {index + 1}</Text>
        <Text style={styles.focus}>{capabilityLabel(focusCapability)}</Text>
      </View>

      <View style={styles.block}>
        <Text style={styles.tag}>You said</Text>
        <Text style={styles.original}>{originalText}</Text>
      </View>

      <View style={styles.block}>
        <Text style={styles.tag}>Try</Text>
        <Text style={styles.corrected}>{correctedText}</Text>
      </View>

      {explanation ? <Text style={styles.explanation}>{explanation}</Text> : null}

      {actions ? <View style={styles.actions}>{actions}</View> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.sm,
  },
  head: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  num: { color: colors.accent, fontSize: 13, fontWeight: '700' },
  focus: { color: colors.textMuted, fontSize: 12, fontWeight: '700', textTransform: 'uppercase' },
  block: { gap: 2 },
  tag: { color: colors.textMuted, fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  original: { color: colors.textMuted, fontSize: 15, lineHeight: 21 },
  corrected: { color: colors.text, fontSize: 15, lineHeight: 21, fontWeight: '600' },
  explanation: { color: colors.textMuted, fontSize: 13, lineHeight: 19, fontStyle: 'italic' },
  actions: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center', flexWrap: 'wrap' },
});
