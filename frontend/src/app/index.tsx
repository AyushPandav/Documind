import React, { useEffect } from 'react';
import { View, StyleSheet, ActivityIndicator } from 'react-native';
import { useRouter } from 'expo-router';
import { useApp } from '@/context/AppContext';
import { Colors } from '@/constants/theme';
import { DocuMindLogo } from '@/components/DocuMindLogo';

export default function IndexScreen() {
  const router = useRouter();
  const { user } = useApp();

  useEffect(() => {
    const timer = setTimeout(() => {
      if (user) {
        router.replace('/app');
      } else {
        router.replace('/auth/login');
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [user, router]);

  return (
    <View style={styles.container}>
      <DocuMindLogo size="large" />
      <ActivityIndicator size="small" color={Colors.primaryCyan} style={styles.loader} />
    </View>
  );
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
