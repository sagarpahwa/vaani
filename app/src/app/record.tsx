import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import type { SessionDetail } from '@/api/types';
import { colors, radius, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Screen } from '@/ui/Screen';

export default function RecordScreen() {
  const { sessionId } = useLocalSearchParams<{ sessionId?: string }>();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let active = true;
    api
      .getSession(sessionId)
      .then((s) => active && setSession(s))
      .catch((e) => active && setError(errorMessage(e)));
    return () => {
      active = false;
    };
  }, [sessionId]);

  if (!sessionId) {
    return (
      <Screen>
        <Banner tone="error" message="No session was provided." />
      </Screen>
    );
  }

  if (error) {
    return (
      <Screen>
        <Banner tone="error" message={error} />
      </Screen>
    );
  }

  if (!session) {
    return (
      <Screen>
        <ActivityIndicator color={colors.accent} style={styles.loader} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Text style={styles.title}>Rehearse your lines</Text>
      <Text style={styles.body}>
        {session.expected_units.length} line{session.expected_units.length === 1 ? '' : 's'} to
        practice. Recording controls arrive next.
      </Text>

      <View style={styles.lines}>
        {session.expected_units.map((text, index) => (
          <View key={index} style={styles.line}>
            <Text style={styles.lineNum}>{index + 1}</Text>
            <Text style={styles.lineText}>{text}</Text>
          </View>
        ))}
      </View>

      <Banner tone="info" message={`Session ${session.session_id.slice(0, 8)} · ${session.mode}`} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loader: { marginTop: spacing.lg },
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.textMuted, fontSize: 15, lineHeight: 21 },
  lines: { gap: spacing.sm },
  line: {
    flexDirection: 'row',
    gap: spacing.sm,
    alignItems: 'flex-start',
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.md,
  },
  lineNum: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '700',
    minWidth: 20,
    textAlign: 'right',
    marginTop: 2,
  },
  lineText: { color: colors.text, fontSize: 15, lineHeight: 22, flex: 1 },
});
