import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import type { SessionDetail } from '@/api/types';
import { capabilityLabel, orderedCapabilityScores } from '@/coaching/capabilities';
import { toPercent } from '@/coaching/format';
import { colors, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { ScoreBar } from '@/ui/ScoreBar';
import { Screen } from '@/ui/Screen';

export default function FeedbackScreen() {
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

  const capabilities = orderedCapabilityScores(session.capability_scores);

  return (
    <Screen>
      <View style={styles.overall}>
        <Text style={styles.overallLabel}>Overall</Text>
        <Text style={styles.overallScore}>{toPercent(session.overall_score)}</Text>
      </View>

      {session.feedback?.summary ? <Text style={styles.summary}>{session.feedback.summary}</Text> : null}

      {capabilities.length > 0 ? (
        <View style={styles.scores}>
          {capabilities.map(([key, score]) => (
            <ScoreBar key={key} label={capabilityLabel(key)} score={score} />
          ))}
        </View>
      ) : (
        <Banner tone="info" message="No capability scores were returned for this session." />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  loader: { marginTop: spacing.lg },
  overall: { alignItems: 'center', gap: spacing.xs },
  overallLabel: { color: colors.textMuted, fontSize: 14, fontWeight: '700', textTransform: 'uppercase' },
  overallScore: { color: colors.text, fontSize: 56, fontWeight: '800' },
  summary: { color: colors.text, fontSize: 16, lineHeight: 24 },
  scores: { gap: spacing.md },
});
