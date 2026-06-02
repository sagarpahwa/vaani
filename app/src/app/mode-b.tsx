import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import { buildGoalSignature, DEFAULT_GOAL_FORM, type GoalForm } from '@/coaching/goal';
import { DEMO_USER_ID } from '@/config';
import { colors, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Button } from '@/ui/Button';
import { Field } from '@/ui/Field';
import { GoalSignatureForm } from '@/ui/GoalSignatureForm';
import { Screen } from '@/ui/Screen';

const PLACEHOLDER =
  'Paste your speech, toast, or pitch here. Each sentence becomes a line you can rehearse.';

export default function ModeBScreen() {
  const router = useRouter();
  const [scriptText, setScriptText] = useState('');
  const [goal, setGoal] = useState<GoalForm>(DEFAULT_GOAL_FORM);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canStart = scriptText.trim().length > 0;

  async function start() {
    if (!canStart) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.createSession({
        user_id: DEMO_USER_ID,
        mode: 'user_script',
        script_text: scriptText.trim(),
        goal_signature: buildGoalSignature(goal),
      });
      router.push({ pathname: '/record', params: { sessionId: session.session_id } });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen>
      <Text style={styles.title}>Your own script</Text>
      <Text style={styles.body}>
        Paste what you want to say, set your goal, and we&apos;ll coach you line by line.
      </Text>
      {error ? <Banner tone="error" message={error} /> : null}

      <Field
        label="Script"
        value={scriptText}
        onChangeText={setScriptText}
        placeholder={PLACEHOLDER}
        multiline
        testID="script-input"
      />

      <Text style={styles.sectionLabel}>Tune your goal</Text>
      <GoalSignatureForm value={goal} onChange={setGoal} />

      <View style={styles.actions}>
        <Button
          label="Start practice"
          onPress={start}
          loading={busy}
          disabled={!canStart}
          testID="start-practice"
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.textMuted, fontSize: 15, lineHeight: 21 },
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
