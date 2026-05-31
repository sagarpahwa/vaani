import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { api, errorMessage } from '@/api/client';
import type { PersonaDetail, PersonaSummary } from '@/api/types';
import { DEMO_USER_ID } from '@/config';
import { colors, radius, spacing } from '@/theme';
import { Banner } from '@/ui/Banner';
import { Button } from '@/ui/Button';
import { Screen } from '@/ui/Screen';

/** Two-letter monogram from a display name ("Steve Jobs" → "SJ"). Exported for tests. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function PersonasScreen() {
  const router = useRouter();
  const [personas, setPersonas] = useState<PersonaSummary[] | null>(null);
  const [selected, setSelected] = useState<PersonaDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .listPersonas()
      .then((p) => active && setPersonas(p))
      .catch((e) => active && setError(errorMessage(e)));
    return () => {
      active = false;
    };
  }, []);

  async function openPersona(personaId: string) {
    setError(null);
    try {
      setSelected(await api.getPersona(personaId));
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
        mode: 'persona',
        persona_id: selected.persona_id,
      });
      router.push({ pathname: '/record', params: { sessionId: session.session_id } });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  if (selected) {
    const band = selected.rubric?.target_pace_sps;
    return (
      <Screen>
        {error ? <Banner tone="error" message={error} /> : null}
        <Text style={styles.detailName}>{selected.name}</Text>
        {selected.role || selected.archetype ? (
          <Text style={styles.detailMeta}>
            {[selected.role, selected.archetype].filter(Boolean).join('  ·  ')}
          </Text>
        ) : null}

        {selected.goal_line ? (
          <View style={styles.goalCard}>
            <Text style={styles.goalLabel}>THE LINE TO LAND</Text>
            <Text style={styles.goalLine}>“{selected.goal_line}”</Text>
          </View>
        ) : null}

        {selected.signature_qualities.length > 0 ? (
          <View style={styles.chips}>
            {selected.signature_qualities.map((q) => (
              <View key={q} style={styles.chip}>
                <Text style={styles.chipText}>{q}</Text>
              </View>
            ))}
          </View>
        ) : null}

        {band && band.length === 2 ? (
          <Text style={styles.styleLine}>
            Speaking style: {band[0]}–{band[1]} syll/s
            {selected.rubric?.expressiveness ? `  ·  ${selected.rubric.expressiveness}` : ''}
            {selected.rubric?.pause_style ? `  ·  ${selected.rubric.pause_style} pauses` : ''}
          </Text>
        ) : null}

        <Text style={styles.sectionLabel}>The speech · {selected.lines.length} lines</Text>
        <View style={styles.lines}>
          {selected.lines.map((line) => (
            <View key={line.line_index} style={styles.line}>
              <Text style={styles.lineNum}>{line.line_index + 1}</Text>
              <Text style={styles.lineText}>{line.text}</Text>
            </View>
          ))}
        </View>

        {selected.reference?.title || selected.reference?.video_url ? (
          <Text style={styles.reference}>
            Inspired by: {selected.reference?.title ?? selected.reference?.video_url}
          </Text>
        ) : null}

        <View style={styles.actions}>
          <Button
            label={`Speak as ${selected.name}`}
            onPress={start}
            loading={busy}
            testID="start-persona"
          />
          <Button
            label="Back to speakers"
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
      <Text style={styles.title}>Pick a great speaker</Text>
      <Text style={styles.body}>
        Record their ~1-minute speech in your own voice — then hear how close you came to their
        delivery.
      </Text>
      {error ? <Banner tone="error" message={error} /> : null}

      {personas === null && !error ? (
        <ActivityIndicator color={colors.accent} style={styles.loader} />
      ) : null}

      <View style={styles.grid}>
        {personas?.map((p) => (
          <Pressable
            key={p.persona_id}
            accessibilityRole="button"
            accessibilityLabel={p.name}
            onPress={() => openPersona(p.persona_id)}
            style={({ pressed }) => [styles.tile, pressed && styles.pressed]}
          >
            <View style={styles.monogram}>
              <Text style={styles.monogramText}>{initials(p.name)}</Text>
            </View>
            <Text style={styles.tileName} numberOfLines={1}>
              {p.name}
            </Text>
            {p.role ? (
              <Text style={styles.tileRole} numberOfLines={1}>
                {p.role}
              </Text>
            ) : null}
          </Pressable>
        ))}
      </View>

      {personas?.length === 0 ? (
        <Banner tone="info" message="No personas seeded yet. Run make poc-db-setup." />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.textMuted, fontSize: 15, lineHeight: 21 },
  loader: { marginTop: spacing.lg },

  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  tile: {
    width: 104,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.sm,
    alignItems: 'center',
    gap: spacing.xs,
  },
  pressed: { opacity: 0.8 },
  monogram: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.surfaceAlt,
    borderWidth: 1,
    borderColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  monogramText: { color: colors.accent, fontSize: 20, fontWeight: '800' },
  tileName: { color: colors.text, fontSize: 13, fontWeight: '700', textAlign: 'center' },
  tileRole: { color: colors.textMuted, fontSize: 11, textAlign: 'center' },

  detailName: { color: colors.text, fontSize: 26, fontWeight: '800' },
  detailMeta: { color: colors.textMuted, fontSize: 14 },
  goalCard: {
    backgroundColor: colors.surfaceAlt,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.md,
    gap: spacing.xs,
  },
  goalLabel: {
    color: colors.accent,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 1,
  },
  goalLine: { color: colors.text, fontSize: 17, fontWeight: '600', lineHeight: 24 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  chip: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.sm,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.sm,
  },
  chipText: { color: colors.textMuted, fontSize: 12, fontWeight: '600' },
  styleLine: { color: colors.textMuted, fontSize: 13 },
  sectionLabel: {
    color: colors.textMuted,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing.sm,
  },
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
  reference: { color: colors.textMuted, fontSize: 13, fontStyle: 'italic' },
  actions: { gap: spacing.sm, marginTop: spacing.md },
});
