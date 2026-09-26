import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { DocumentItem } from '@/types';
import { Colors, Fonts } from '@/constants/theme';
import { StatusBadge } from './StatusBadge';

interface DocumentRowProps {
  document: DocumentItem;
  isSelected?: boolean;
  onSelect: (doc: DocumentItem) => void;
}

export function DocumentRow({
  document,
  isSelected = false,
  onSelect,
}: DocumentRowProps) {
  return (
    <Pressable
      onPress={() => onSelect(document)}
      style={({ pressed }) => [
        styles.container,
        isSelected && styles.selectedContainer,
        pressed && styles.pressedContainer,
      ]}
      accessibilityRole="button"
      accessibilityState={{ selected: isSelected }}
    >
      <View style={styles.contentRow}>
        <View style={styles.indicatorContainer}>
          <Text style={[styles.indicator, isSelected && styles.activeIndicator]}>
            {isSelected ? '▸' : '•'}
          </Text>
        </View>

        <View style={styles.infoContainer}>
          <Text
            style={[styles.name, isSelected && styles.selectedName]}
            numberOfLines={1}
            ellipsizeMode="middle"
          >
            {document.name}
          </Text>

          <View style={styles.metaRow}>
            <StatusBadge status={document.status} size="small" />
            <Text style={styles.pageCount}>{document.pages} pg</Text>
            {document.size && <Text style={styles.sizeText}>• {document.size}</Text>}
          </View>
        </View>
      </View>

      {/* Progress bar if document is currently processing/uploading */}
      {document.progress !== undefined && document.progress < 100 && (
        <View style={styles.progressTrack}>
          <View
            style={[
              styles.progressBar,
              {
                width: `${document.progress}%`,
                backgroundColor:
                  document.status === 'OCR'
                    ? Colors.secondaryPurple
                    : Colors.primaryCyan,
              },
            ]}
          />
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    borderRadius: 8,
    padding: 12,
    marginVertical: 4,
    position: 'relative',
    overflow: 'hidden',
  },
  selectedContainer: {
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
    borderColor: Colors.borderCyan,
  },
  pressedContainer: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  contentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  indicatorContainer: {
    width: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  indicator: {
    fontFamily: Fonts.mono,
    fontSize: 14,
    color: Colors.textMuted,
  },
  activeIndicator: {
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  infoContainer: {
    flex: 1,
    gap: 6,
  },
  name: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    color: Colors.textPrimary,
    fontWeight: '600',
  },
  selectedName: {
    color: Colors.primaryCyan,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pageCount: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
  },
  sizeText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
  },
  progressTrack: {
    marginTop: 8,
    height: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 1,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    borderRadius: 1,
  },
});
