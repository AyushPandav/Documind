import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { DocumentStatus } from '@/types';
import { Colors, Fonts } from '@/constants/theme';

interface StatusBadgeProps {
  status: DocumentStatus;
  size?: 'small' | 'medium';
}

export function StatusBadge({ status, size = 'small' }: StatusBadgeProps) {
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (status === 'OCR' || status === 'PROCESSING') {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 0.4,
            duration: 700,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 700,
            useNativeDriver: true,
          }),
        ])
      );
      animation.start();
      return () => animation.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [status]);

  const getBadgeStyle = () => {
    switch (status) {
      case 'QUEUED':
        return {
          bg: 'rgba(139, 139, 149, 0.1)',
          border: 'rgba(139, 139, 149, 0.3)',
          color: Colors.statusQueued,
        };
      case 'OCR':
        return {
          bg: 'rgba(168, 85, 247, 0.12)',
          border: 'rgba(168, 85, 247, 0.35)',
          color: Colors.statusOcr,
        };
      case 'PROCESSING':
        return {
          bg: 'rgba(34, 211, 238, 0.12)',
          border: 'rgba(34, 211, 238, 0.35)',
          color: Colors.statusProcessing,
        };
      case 'INDEXED':
      default:
        return {
          bg: 'rgba(34, 211, 238, 0.15)',
          border: Colors.primaryCyan,
          color: Colors.primaryCyan,
        };
    }
  };

  const current = getBadgeStyle();
  const isSmall = size === 'small';

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: current.bg,
          borderColor: current.border,
          paddingVertical: isSmall ? 2 : 4,
          paddingHorizontal: isSmall ? 6 : 8,
        },
      ]}
    >
      <Animated.Text
        style={[
          styles.text,
          {
            color: current.color,
            fontSize: isSmall ? 10 : 11,
            opacity: status === 'OCR' || status === 'PROCESSING' ? pulseAnim : 1,
          },
        ]}
      >
        {status}
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1,
    borderRadius: 4,
    alignSelf: 'flex-start',
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontFamily: Fonts.mono,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
});
