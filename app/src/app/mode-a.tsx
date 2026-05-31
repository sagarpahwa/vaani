import { StyleSheet, Text, View } from 'react-native';

import { colors, maxContentWidth, spacing } from '@/theme';

export default function ModeAScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Guided Practice</Text>
        <Text style={styles.body}>
          The script picker, line-by-line recording, and coaching report land here in the
          next milestone.
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', padding: spacing.lg },
  content: { width: '100%', maxWidth: maxContentWidth, gap: spacing.sm },
  title: { color: colors.text, fontSize: 24, fontWeight: '800' },
  body: { color: colors.textMuted, fontSize: 16, lineHeight: 22 },
});
