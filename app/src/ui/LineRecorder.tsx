import { StyleSheet, Text, View } from 'react-native';

import type { LineState } from '@/audio/recordings';
import { formatClock } from '@/coaching/format';
import { colors, radius, spacing } from '@/theme';

import { Button } from './Button';

interface LineRecorderProps {
  index: number;
  text: string;
  state: LineState;
  durationMs?: number;
  /** Disable controls while another line is mid-recording. */
  disabled?: boolean;
  onRecord: () => void;
  onStop: () => void;
  onSkip: () => void;
}

const STATUS: Record<LineState, { label: string; color: string }> = {
  idle: { label: 'Not recorded', color: colors.textMuted },
  recording: { label: 'Recording…', color: colors.bad },
  recorded: { label: 'Recorded', color: colors.good },
  skipped: { label: 'Skipped', color: colors.textMuted },
};

export function LineRecorder({
  index,
  text,
  state,
  durationMs,
  disabled = false,
  onRecord,
  onStop,
  onSkip,
}: LineRecorderProps) {
  const status = STATUS[state];
  const recording = state === 'recording';
  return (
    <View style={[styles.row, recording && styles.rowActive]}>
      <View style={styles.head}>
        <Text style={styles.num}>{index + 1}</Text>
        <Text style={styles.text}>{text}</Text>
      </View>

      <View style={styles.footer}>
        <Text style={[styles.status, { color: status.color }]}>
          {recording ? `${status.label} ${formatClock(durationMs)}` : status.label}
        </Text>

        <View style={styles.actions}>
          {recording ? (
            <Button label="Stop" variant="secondary" onPress={onStop} testID={`stop-${index}`} />
          ) : (
            <>
              <Button
                label={state === 'recorded' ? 'Re-record' : 'Record'}
                variant={state === 'recorded' ? 'ghost' : 'primary'}
                onPress={onRecord}
                disabled={disabled}
                testID={`record-${index}`}
              />
              {state !== 'skipped' && state !== 'recorded' ? (
                <Button
                  label="Skip"
                  variant="ghost"
                  onPress={onSkip}
                  disabled={disabled}
                  testID={`skip-${index}`}
                />
              ) : null}
            </>
          )}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
    gap: spacing.sm,
  },
  rowActive: { borderColor: colors.bad },
  head: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  num: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '700',
    minWidth: 20,
    textAlign: 'right',
    marginTop: 2,
  },
  text: { color: colors.text, fontSize: 15, lineHeight: 22, flex: 1 },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.sm,
    flexWrap: 'wrap',
  },
  status: { fontSize: 13, fontWeight: '700' },
  actions: { flexDirection: 'row', gap: spacing.sm, alignItems: 'center' },
});
