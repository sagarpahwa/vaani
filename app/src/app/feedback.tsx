import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import type { SessionDetail } from '@/api/types';
import { capabilityLabel, orderedCapabilityScores } from '@/coaching/capabilities';
import { deltaColor, severityColor, signedPercent, toPercent } from '@/coaching/format';
import { colors, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Button } from '@/ui/Button';
import { Card } from '@/ui/Card';
import { CorrectionCard } from '@/ui/CorrectionCard';
import { ScoreBar } from '@/ui/ScoreBar';
import { Screen } from '@/ui/Screen';

export default function FeedbackScreen() {
  const router = useRouter();
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
  const delta = session.delta ?? null;
  const overallDelta = delta?.overall;
  const feedback = session.feedback ?? null;
  const corrections = session.corrections ?? [];

  return (
    <Screen>
      <View style={styles.overall}>
        <Text style={styles.overallLabel}>Overall</Text>
        <Text style={styles.overallScore}>{toPercent(session.overall_score)}</Text>
        {overallDelta !== undefined ? (
          <Text style={[styles.overallDelta, { color: deltaColor(overallDelta) }]}>
            {signedPercent(overallDelta)} vs last attempt
          </Text>
        ) : null}
      </View>

      {feedback?.summary ? <Text style={styles.summary}>{feedback.summary}</Text> : null}

      {capabilities.length > 0 ? (
        <View style={styles.scores}>
          {capabilities.map(([key, score]) => {
            const d = delta?.[key];
            return (
              <ScoreBar
                key={key}
                label={capabilityLabel(key)}
                score={score}
                deltaText={d !== undefined ? signedPercent(d) : undefined}
                deltaColor={d !== undefined ? deltaColor(d) : undefined}
              />
            );
          })}
        </View>
      ) : (
        <Banner tone="info" message="No capability scores were returned for this session." />
      )}

      {feedback && feedback.strengths.length > 0 ? (
        <Card title="What worked">
          <View style={styles.list}>
            {feedback.strengths.map((s, i) => (
              <View key={i} style={styles.listRow}>
                <View style={[styles.dot, { backgroundColor: colors.good }]} />
                <Text style={styles.listText}>{s}</Text>
              </View>
            ))}
          </View>
        </Card>
      ) : null}

      {feedback && feedback.improvements.length > 0 ? (
        <Card title="Focus next">
          <View style={styles.list}>
            {feedback.improvements.map((imp, i) => (
              <View key={i} style={styles.listRow}>
                <View style={[styles.dot, { backgroundColor: severityColor(imp.severity) }]} />
                <Text style={styles.listText}>
                  <Text style={styles.impCap}>{capabilityLabel(imp.capability)}: </Text>
                  {imp.message}
                </Text>
              </View>
            ))}
          </View>
        </Card>
      ) : null}

      {corrections.length > 0 ? (
        <View style={styles.corrections}>
          <Text style={styles.sectionTitle}>Line by line</Text>
          {corrections.map((c, i) => (
            <CorrectionCard
              key={i}
              index={c.line_index}
              focusCapability={c.focus_capability}
              originalText={c.original_text}
              correctedText={c.corrected_text}
              explanation={c.explanation}
            />
          ))}
        </View>
      ) : null}

      <Button
        label="Practice again"
        testID="practice-again"
        onPress={() => router.push({ pathname: '/record', params: { sessionId, retry: '1' } })}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loader: { marginTop: spacing.lg },
  overall: { alignItems: 'center', gap: spacing.xs },
  overallLabel: { color: colors.textMuted, fontSize: 14, fontWeight: '700', textTransform: 'uppercase' },
  overallScore: { color: colors.text, fontSize: 56, fontWeight: '800' },
  overallDelta: { fontSize: 14, fontWeight: '700' },
  summary: { color: colors.text, fontSize: 16, lineHeight: 24 },
  scores: { gap: spacing.md },
  list: { gap: spacing.sm },
  listRow: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  dot: { width: 8, height: 8, borderRadius: 4, marginTop: 7 },
  listText: { color: colors.text, fontSize: 15, lineHeight: 22, flex: 1 },
  impCap: { fontWeight: '700' },
  corrections: { gap: spacing.sm },
  sectionTitle: { color: colors.text, fontSize: 18, fontWeight: '700' },
});
