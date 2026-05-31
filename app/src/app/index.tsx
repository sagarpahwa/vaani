import { Link } from 'expo-router';
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { API_BASE_URL } from '@/config';
import { flags } from '@/featureFlags';
import { colors, maxContentWidth, radius, spacing } from '@/theme';

export default function HomeScreen() {
  return (
    <ScrollView contentContainerStyle={styles.scroll}>
      <View style={styles.content}>
        <Text style={styles.kicker}>PUBLIC SPEAKING COACH</Text>
        <Text style={styles.title}>Practice. Get coached. Improve.</Text>
        <Text style={styles.subtitle}>
          Record yourself, get goal-aware feedback, and hear an ideal read-aloud of every
          line you can sharpen.
        </Text>

        <View style={styles.cards}>
          <Link href="/mode-a" asChild>
            <Pressable style={styles.card} accessibilityRole="button">
              <Text style={styles.cardTitle}>Guided Practice</Text>
              <Text style={styles.cardBody}>
                Pick a curated script and rehearse it line by line.
              </Text>
            </Pressable>
          </Link>

          {flags.modeB && (
            <Link href="/mode-b" asChild>
              <Pressable style={styles.card} accessibilityRole="button">
                <Text style={styles.cardTitle}>Your Own Script</Text>
                <Text style={styles.cardBody}>
                  Paste a speech, toast, or pitch and practice it.
                </Text>
              </Pressable>
            </Link>
          )}
        </View>

        <View style={styles.status}>
          <Text style={styles.statusLabel}>Connected to</Text>
          <Text style={styles.statusValue}>{API_BASE_URL}</Text>
          <Text style={styles.statusMeta}>
            platform: {Platform.OS} · modeB: {String(flags.modeB)} · live:{' '}
            {String(flags.liveProgress)} · read-aloud: {String(flags.readAloud)}
          </Text>
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: {
    flexGrow: 1,
    alignItems: 'center',
    padding: spacing.lg,
  },
  content: {
    width: '100%',
    maxWidth: maxContentWidth,
    gap: spacing.md,
  },
  kicker: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.5,
  },
  title: {
    color: colors.text,
    fontSize: 30,
    fontWeight: '800',
  },
  subtitle: {
    color: colors.textMuted,
    fontSize: 16,
    lineHeight: 22,
  },
  cards: {
    gap: spacing.md,
    marginTop: spacing.sm,
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderWidth: 1,
    borderRadius: radius.lg,
    padding: spacing.lg,
    gap: spacing.xs,
  },
  cardTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: '700',
  },
  cardBody: {
    color: colors.textMuted,
    fontSize: 14,
  },
  status: {
    marginTop: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surfaceAlt,
    gap: 2,
  },
  statusLabel: {
    color: colors.textMuted,
    fontSize: 11,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  statusValue: {
    color: colors.text,
    fontSize: 14,
    fontWeight: '600',
  },
  statusMeta: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: spacing.xs,
  },
});
