import React from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { Redirect, useRootNavigationState } from 'expo-router';
import { useApp } from '@/context/AppContext';
import { Colors } from '@/constants/theme';
import { DocuMindLogo } from '@/components/DocuMindLogo';

export default function IndexScreen() {
  const rootNavigationState = useRootNavigationState();
  const { user } = useApp();

  // Wait until Expo Root Navigator is fully mounted before redirecting
  if (!rootNavigationState?.key) {
    return (
      <View style={styles.container}>
        <DocuMindLogo size="large" />
        <ActivityIndicator size="small" color={Colors.primaryCyan} style={styles.loader} />
      </View>
    );
  }

  if (user) {
    return <Redirect href="/app" />;
  }

  return <Redirect href="/auth/login" />;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loader: {
    marginTop: 24,
  },
});
