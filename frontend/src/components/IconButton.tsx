import React, { ReactNode } from 'react';
import { Pressable, StyleSheet, ViewStyle, StyleProp, View } from 'react-native';
import { Colors } from '@/constants/theme';

interface IconButtonProps {
  onPress: () => void;
  icon: ReactNode;
  active?: boolean;
  style?: StyleProp<ViewStyle>;
  badgeCount?: number;
  accessibilityLabel: string;
  size?: 'small' | 'medium';
}

export function IconButton({
  onPress,
  icon,
  active = false,
  style,
  badgeCount,
  accessibilityLabel,
  size = 'small',
}: IconButtonProps) {
  const isMedium = size === 'medium';

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        isMedium && styles.buttonMedium,
        active && styles.activeButton,
        pressed && styles.pressedButton,
        style,
      ]}
      hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
    >
      {icon}
      {badgeCount !== undefined && badgeCount > 0 && (
        <View style={[styles.badgeDot, isMedium && styles.badgeDotMedium]} />
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  buttonMedium: {
    width: 42,
    height: 42,
    borderRadius: 8,
  },
  activeButton: {
    backgroundColor: 'rgba(34, 211, 238, 0.12)',
    borderColor: Colors.primaryCyan,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 5,
  },
  pressedButton: {
    backgroundColor: 'rgba(34, 211, 238, 0.18)',
    borderColor: Colors.primaryCyan,
  },
  badgeDot: {
    position: 'absolute',
    top: 5,
    right: 5,
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.primaryCyan,
  },
  badgeDotMedium: {
    top: 6,
    right: 6,
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
});
