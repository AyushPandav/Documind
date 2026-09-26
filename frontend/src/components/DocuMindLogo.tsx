import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Fonts } from '@/constants/theme';

interface DocuMindLogoProps {
  size?: 'compact' | 'large';
}

export function DocuMindLogo({ size = 'compact' }: DocuMindLogoProps) {
  const isLarge = size === 'large';
  const iconSize = isLarge ? 36 : 22;

  return (
    <View style={[styles.container, isLarge && styles.largeContainer]}>
      <View style={styles.brandRow}>
        {/* Document outline icon with scan-line & circuit node detail */}
        <View style={[styles.docIcon, { width: iconSize, height: iconSize * 1.25 }]}>
          <View style={styles.docFold} />
          <View style={styles.scanLine} />
          <View style={styles.circuitNode} />
          <View style={styles.circuitTrack} />
        </View>

        <View style={styles.textContainer}>
          <Text style={[styles.wordmark, isLarge && styles.largeWordmark]}>
            <Text style={styles.docuText}>Docu</Text>
            <Text style={styles.mindText}>Mind</Text>
          </Text>
        </View>
      </View>

      {isLarge && (
        <Text style={styles.tagline}>Document Intelligence, Cited.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'flex-start',
    justifyContent: 'center',
  },
  largeContainer: {
    alignItems: 'center',
    marginVertical: 16,
  },
  brandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  docIcon: {
    borderWidth: 1.5,
    borderColor: Colors.primaryCyan,
    borderRadius: 3,
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
    position: 'relative',
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  docFold: {
    position: 'absolute',
    top: 0,
    right: 0,
    width: 6,
    height: 6,
    borderBottomWidth: 1.5,
    borderLeftWidth: 1.5,
    borderColor: Colors.primaryCyan,
    backgroundColor: Colors.background,
  },
  scanLine: {
    position: 'absolute',
    width: '70%',
    height: 1.5,
    backgroundColor: Colors.primaryCyan,
    top: '38%',
    opacity: 0.9,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 2,
  },
  circuitTrack: {
    position: 'absolute',
    width: '50%',
    height: 1,
    backgroundColor: 'rgba(34, 211, 238, 0.5)',
    bottom: '28%',
  },
  circuitNode: {
    position: 'absolute',
    width: 3.5,
    height: 3.5,
    borderRadius: 2,
    backgroundColor: Colors.secondaryPurple,
    bottom: '24%',
    right: '25%',
  },
  textContainer: {
    justifyContent: 'center',
  },
  wordmark: {
    fontSize: 18,
    fontFamily: Fonts.mono,
    letterSpacing: -0.3,
    fontWeight: '700',
  },
  largeWordmark: {
    fontSize: 28,
    letterSpacing: -0.5,
  },
  docuText: {
    color: Colors.textPrimary,
  },
  mindText: {
    color: Colors.primaryCyan,
  },
  tagline: {
    marginTop: 6,
    fontSize: 12,
    fontFamily: Fonts.mono,
    color: Colors.textMuted,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
});
