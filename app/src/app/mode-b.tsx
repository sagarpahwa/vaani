import { StyleSheet, Text, View } from 'react-native';

import { colors, maxContentWidth, spacing } from '@/theme';

export default function ModeBScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.title}>Your Own Script</Text>
        <Text style={styles.body}>
          Paste-your-script intake, recording, and coaching report land here in the next
          milestone.
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
