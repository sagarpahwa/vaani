import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { colors } from '@/theme';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerStyle: { backgroundColor: colors.bg },
          headerTintColor: colors.text,
          headerTitleStyle: { fontWeight: '700' },
          contentStyle: { backgroundColor: colors.bg },
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Vaani' }} />
        <Stack.Screen name="mode-a" options={{ title: 'Guided Practice' }} />
        <Stack.Screen name="mode-b" options={{ title: 'Your Own Script' }} />
        <Stack.Screen name="record" options={{ title: 'Rehearse' }} />
        <Stack.Screen name="processing" options={{ title: 'Processing' }} />
        <Stack.Screen name="feedback" options={{ title: 'Coaching' }} />
      </Stack>
    </>
  );
}
