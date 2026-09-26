import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { Colors } from '@/constants/theme';

interface GlassCardProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
  borderColor?: string;
  accent?: 'cyan' | 'purple' | 'none';
}

export function GlassCard({
  children,
  style,
  borderColor,
  accent = 'none',
}: GlassCardProps) {
  return (
    <View
      style={[
        styles.card,
        borderColor ? { borderColor } : null,
        accent === 'cyan' && styles.accentCyan,
        accent === 'purple' && styles.accentPurple,
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.surfaceCard,
    borderWidth: 1,
    borderColor: 'rgba(34, 211, 238, 0.15)',
    borderRadius: 8,
    padding: 16,
    position: 'relative',
    overflow: 'hidden',
  },
  accentCyan: {
    borderColor: Colors.borderCyan,
  },
  accentPurple: {
    borderColor: Colors.borderPurple,
  },
});
