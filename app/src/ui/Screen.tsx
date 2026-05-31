import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { maxContentWidth, spacing } from '@/theme';

/** Centered, max-width scroll container shared by every screen. */
export function Screen({ children }: { children: ReactNode }) {
  return (
    <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
      <View style={styles.content}>{children}</View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flexGrow: 1, alignItems: 'center', padding: spacing.lg },
  content: { width: '100%', maxWidth: maxContentWidth, gap: spacing.md },
});
