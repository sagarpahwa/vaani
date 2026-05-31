import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage, sessionEventsUrl } from '@/api/client';
import { dropSubmission, peekSubmission } from '@/audio/flowStore';
import { STAGES, STAGE_INTERVAL_MS, stageLabel } from '@/coaching/stages';
import { isEnabled } from '@/featureFlags';
import { colors, radius, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Button } from '@/ui/Button';
import { Screen } from '@/ui/Screen';

export default function ProcessingScreen() {
  const router = useRouter();
  const { sessionId } = useLocalSearchParams<{ sessionId?: string }>();
  const [shownStage, setShownStage] = useState(0);
  const [submitDone, setSubmitDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startedRef = useRef(false);

  // Pace the stage timeline locally and run the real submit (or recover on a
  // hard reload). Submit success is the source of truth; the timeline only
  // gives the work a visible shape.
  useEffect(() => {
    if (!sessionId) return;

    const intervalId = setInterval(() => {
      setShownStage((s) => (s >= STAGES.length ? s : s + 1));
    }, STAGE_INTERVAL_MS);

    if (!startedRef.current) {
      startedRef.current = true;
      const submission = peekSubmission(sessionId);
      if (submission) {
        const call = submission.kind === 'retry' ? api.retrySession : api.submitUtterances;
        call(sessionId, submission.inputs)
          .then(() => {
            dropSubmission(sessionId);
            setSubmitDone(true);
          })
          .catch((e) => setError(errorMessage(e)));
      } else {
        // Nothing stashed (reload / deep link): only navigate on if already done.
        api
          .getSession(sessionId)
          .then((s) => {
            if (s.feedback || s.overall_score != null) setSubmitDone(true);
            else setError('Your recording is no longer available. Please record again.');
          })
          .catch((e) => setError(errorMessage(e)));
      }
    }

    return () => clearInterval(intervalId);
  }, [sessionId]);

  // Move on only once the work finished AND the full timeline has been shown.
  useEffect(() => {
    if (error || !submitDone || shownStage < STAGES.length) return;
    router.replace({ pathname: '/feedback', params: { sessionId } });
  }, [error, submitDone, shownStage, sessionId, router]);

  // Live progress is additive: it surfaces a server-side failure event. The
  // synchronous POC backend does the work in the submit call, so the local
  // timeline drives pacing; this seam stays real for when processing goes async.
  useEffect(() => {
    if (!sessionId || !isEnabled('liveProgress')) return;
    let ws: WebSocket | undefined;
    try {
      ws = new WebSocket(sessionEventsUrl(sessionId));
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(String(ev.data));
          if (msg?.stage === 'error') setError(msg.message ?? 'Processing failed on the server.');
        } catch {
          // ignore malformed frames
        }
      };
    } catch {
      // WebSocket unavailable — the local timeline still drives the UI
    }
    return () => ws?.close();
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
        <Button label="Start over" variant="secondary" onPress={() => router.replace('/')} />
      </Screen>
    );
  }

  const active = Math.min(shownStage, STAGES.length - 1);

  return (
    <Screen>
      <Text style={styles.title}>Coaching your delivery…</Text>

      <View style={styles.stages}>
        {STAGES.map((stage, i) => {
          const done = i < shownStage;
          const isActive = i === active && shownStage < STAGES.length;
          return (
            <View key={stage} style={styles.stageRow}>
              <View style={styles.marker}>
                {isActive ? (
                  <ActivityIndicator color={colors.accent} size="small" />
                ) : (
                  <View style={[styles.dot, done ? styles.dotDone : styles.dotPending]} />
                )}
              </View>
              <Text
                style={[
                  styles.stageLabel,
                  done && styles.stageLabelDone,
                  isActive && styles.stageLabelActive,
                ]}
              >
                {stageLabel(stage)}
              </Text>
            </View>
          );
        })}
      </View>

      {isEnabled('liveProgress') ? <Text style={styles.live}>Live progress enabled</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontSize: 22, fontWeight: '800' },
  stages: {
    gap: spacing.md,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.md,
    padding: spacing.lg,
  },
  stageRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  marker: { width: 20, height: 20, alignItems: 'center', justifyContent: 'center' },
  dot: { width: 10, height: 10, borderRadius: 5 },
  dotDone: { backgroundColor: colors.good },
  dotPending: { backgroundColor: colors.surfaceAlt, borderColor: colors.border, borderWidth: 1 },
  stageLabel: { color: colors.textMuted, fontSize: 15, flex: 1 },
  stageLabelDone: { color: colors.text },
  stageLabelActive: { color: colors.text, fontWeight: '700' },
  live: { color: colors.textMuted, fontSize: 12, textAlign: 'center' },
});
