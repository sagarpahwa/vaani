import { StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '@/theme';

type BannerTone = 'error' | 'info';

export function Banner({ tone = 'info', message }: { tone?: BannerTone; message: string }) {
  return (
    <View style={[styles.banner, tone === 'error' ? styles.error : styles.info]}>
      <Text style={styles.text}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { padding: spacing.md, borderRadius: radius.md, borderWidth: 1 },
  error: { backgroundColor: '#3B1D1D', borderColor: colors.bad },
  info: { backgroundColor: colors.surfaceAlt, borderColor: colors.border },
  text: { color: colors.text, fontSize: 14, lineHeight: 20 },
});
