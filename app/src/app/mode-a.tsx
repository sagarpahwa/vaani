import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import type { ScriptDetail, ScriptSummary } from '@/api/types';
import {
  buildGoalSignature,
  DEFAULT_GOAL_FORM,
  occasionFromProfile,
  type GoalForm,
} from '@/coaching/goal';
import { DEMO_USER_ID } from '@/config';
import { colors, radius, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Button } from '@/ui/Button';
import { GoalSignatureForm } from '@/ui/GoalSignatureForm';
import { Screen } from '@/ui/Screen';

export default function ModeAScreen() {
  const router = useRouter();
  const [scripts, setScripts] = useState<ScriptSummary[] | null>(null);
  const [selected, setSelected] = useState<ScriptDetail | null>(null);
  const [goal, setGoal] = useState<GoalForm>(DEFAULT_GOAL_FORM);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .listScripts()
      .then((s) => active && setScripts(s))
      .catch((e) => active && setError(errorMessage(e)));
    return () => {
      active = false;
    };
  }, []);

  async function openScript(scriptId: string) {
    setError(null);
    try {
      const detail = await api.getScript(scriptId);
      setSelected(detail);
      setGoal({ ...DEFAULT_GOAL_FORM, occasion: occasionFromProfile(detail.goal_profile) });
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function start() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.createSession({
        user_id: DEMO_USER_ID,
        mode: 'guided',
        script_id: selected.script_id,
        goal_signature: buildGoalSignature(goal),
      });
      router.push({ pathname: '/record', params: { sessionId: session.session_id } });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (selected) {
    return (
      <Screen>
        {error ? <Banner tone="error" message={error} /> : null}
        <Text style={styles.title}>{selected.title}</Text>
        {selected.description ? <Text style={styles.body}>{selected.description}</Text> : null}

        <View style={styles.lines}>
          {selected.lines.map((line) => (
            <View key={line.line_index} style={styles.line}>
              <Text style={styles.lineNum}>{line.line_index + 1}</Text>
              <Text style={styles.lineText}>{line.text}</Text>
            </View>
          ))}
        </View>

        <Text style={styles.sectionLabel}>Tune your goal</Text>
        <GoalSignatureForm value={goal} onChange={setGoal} />

        <View style={styles.actions}>
          <Button label="Start practice" onPress={start} loading={busy} testID="start-practice" />
          <Button
            label="Back to scripts"
            variant="ghost"
            onPress={() => setSelected(null)}
            disabled={busy}
          />
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <Text style={styles.title}>Pick a script</Text>
      <Text style={styles.body}>Choose a curated speech to rehearse line by line.</Text>
      {error ? <Banner tone="error" message={error} /> : null}

      {scripts === null && !error ? (
        <ActivityIndicator color={colors.accent} style={styles.loader} />
      ) : null}

      <View style={styles.list}>
        {scripts?.map((script) => (
          <Pressable
            key={script.script_id}
            accessibilityRole="button"
            onPress={() => openScript(script.script_id)}
            style={({ pressed }) => [styles.scriptRow, pressed && styles.pressed]}
          >
            <Text style={styles.scriptTitle}>{script.title}</Text>
            <Text style={styles.scriptMeta}>
              {[script.difficulty, `${script.line_count} lines`, script.language]
                .filter(Boolean)
                .join('  ·  ')}
            </Text>
          </Pressable>
        ))}
      </View>

      {scripts?.length === 0 ? (
        <Banner tone="info" message="No scripts seeded yet. Run make poc-db-setup." />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.textMuted, fontSize: 15, lineHeight: 21 },
  loader: { marginTop: spacing.lg },
  list: { gap: spacing.sm },
  scriptRow: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  pressed: { opacity: 0.8 },
  scriptTitle: { color: colors.text, fontSize: 18, fontWeight: '700' },
  scriptMeta: { color: colors.textMuted, fontSize: 13 },
  lines: { gap: spacing.sm },
  line: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  lineNum: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: '700',
    minWidth: 20,
    textAlign: 'right',
    marginTop: 2,
  },
  lineText: { color: colors.text, fontSize: 15, lineHeight: 22, flex: 1 },
  sectionLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
  actions: { gap: spacing.sm, marginTop: spacing.md },
});
