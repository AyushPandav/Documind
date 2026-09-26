import React, { useRef } from 'react';
import { Text, StyleSheet, Pressable, Animated } from 'react-native';
import { Colors, Fonts } from '@/constants/theme';

interface CitationChipProps {
  index: number;
  onPress: () => void;
  active?: boolean;
}

export function CitationChip({ index, onPress, active = false }: CitationChipProps) {
  const scaleAnim = useRef(new Animated.Value(1)).current;

  const handlePressIn = () => {
    Animated.spring(scaleAnim, {
      toValue: 0.9,
      useNativeDriver: true,
      speed: 50,
      bounciness: 4,
    }).start();
  };

  const handlePressOut = () => {
    Animated.spring(scaleAnim, {
      toValue: 1,
      useNativeDriver: true,
      speed: 40,
      bounciness: 8,
    }).start();
  };

  return (
    <Animated.View style={[{ transform: [{ scale: scaleAnim }] }, styles.wrapper]}>
      <Pressable
        onPress={onPress}
        onPressIn={handlePressIn}
        onPressOut={handlePressOut}
        style={({ pressed }) => [
          styles.container,
          active && styles.activeContainer,
          pressed && styles.pressedContainer,
        ]}
        hitSlop={{ top: 8, bottom: 8, left: 6, right: 6 }}
        accessibilityRole="button"
        accessibilityLabel={`Source citation ${index}`}
      >
        <Text style={[styles.text, active && styles.activeText]}>[{index}]</Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginHorizontal: 2,
    justifyContent: 'center',
  },
  container: {
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 4,
    backgroundColor: 'rgba(34, 211, 238, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(34, 211, 238, 0.35)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  activeContainer: {
    backgroundColor: Colors.primaryCyan,
    borderColor: Colors.primaryCyan,
  },
  pressedContainer: {
    backgroundColor: 'rgba(34, 211, 238, 0.25)',
    borderColor: Colors.primaryCyan,
  },
  text: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
  activeText: {
    color: '#0A0A0F',
  },
});
