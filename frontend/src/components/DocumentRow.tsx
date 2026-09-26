import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { DocumentItem } from '@/types';
import { Colors, Fonts } from '@/constants/theme';
import { StatusBadge } from './StatusBadge';

interface DocumentRowProps {
  document: DocumentItem;
  isSelected?: boolean;
  onSelect: (doc: DocumentItem) => void;
}

const formatDocName = (name?: string) => {
  if (!name) return '';
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
};

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
      accessibilityRole="checkbox"
      accessibilityState={{ selected: isSelected }}
    >
      <View style={styles.contentRow}>
        {/* Multi-select Checkbox */}
        <View style={[styles.checkbox, isSelected && styles.checkboxSelected]}>
          {isSelected ? (
            <Ionicons name="checkmark" size={13} color="#0B101B" />
          ) : null}
        </View>

        <View style={styles.infoContainer}>
          <Text
            style={[styles.name, isSelected && styles.selectedName]}
            numberOfLines={1}
            ellipsizeMode="middle"
          >
            {formatDocName(document.name)}
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
    borderRadius: 10,
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
    gap: 12,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.25)',
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxSelected: {
    backgroundColor: Colors.primaryCyan,
    borderColor: Colors.primaryCyan,
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
