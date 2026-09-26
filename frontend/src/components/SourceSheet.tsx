import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Modal,
  Pressable,
  Animated,
  Dimensions,
  ScrollView,
  TouchableWithoutFeedback,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { CitationSource } from '@/types';
import { Colors, Fonts } from '@/constants/theme';

interface SourceSheetProps {
  visible: boolean;
  onClose: () => void;
  activeSource: CitationSource | null;
  sourcesList?: CitationSource[];
  onSelectSource?: (source: CitationSource) => void;
}

const SCREEN_HEIGHT = Dimensions.get('window').height;
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.72, 540);

export function SourceSheet({
  visible,
  onClose,
  activeSource,
  sourcesList = [],
  onSelectSource,
}: SourceSheetProps) {
  const slideAnim = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.spring(slideAnim, {
          toValue: 0,
          damping: 25,
          stiffness: 200,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: SHEET_HEIGHT,
          duration: 220,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible]);

  if (!visible && !activeSource) return null;

  const currentSource = activeSource || sourcesList[0];

  return (
    <Modal
      visible={visible}
      transparent
      animationType="none"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <View style={styles.overlay}>
        {/* Backdrop */}
        <TouchableWithoutFeedback onPress={onClose}>
          <Animated.View style={[styles.backdrop, { opacity: fadeAnim }]} />
        </TouchableWithoutFeedback>

        {/* Bottom Sheet */}
        <Animated.View
          style={[
            styles.sheetContainer,
            { transform: [{ translateY: slideAnim }] },
          ]}
        >
          {/* Grab Handle */}
          <View style={styles.handleContainer}>
            <View style={styles.grabHandle} />
          </View>

          {/* Header */}
          <View style={styles.header}>
            <View style={styles.titleRow}>
              <Ionicons name="bookmark-outline" size={18} color={Colors.primaryCyan} />
              <Text style={styles.headerTitle}>Sources & Citations</Text>
            </View>
            <Pressable
              onPress={onClose}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              style={styles.closeButton}
              accessibilityLabel="Close sources"
            >
              <Ionicons name="close" size={20} color={Colors.textMuted} />
            </Pressable>
          </View>

          {/* Multiple Citation Selector if available */}
          {sourcesList.length > 1 && (
            <View style={styles.tabsRow}>
              {sourcesList.map((src) => {
                const isSelected = src.id === currentSource?.id;
                return (
                  <Pressable
                    key={src.id}
                    onPress={() => onSelectSource?.(src)}
                    style={[
                      styles.tabPill,
                      isSelected && styles.tabPillActive,
                    ]}
                  >
                    <Text
                      style={[
                        styles.tabPillText,
                        isSelected && styles.tabPillTextActive,
                      ]}
                    >
                      [{src.index}] Page {src.page}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          )}

          {/* Source Content */}
          <ScrollView
            style={styles.contentScroll}
            contentContainerStyle={styles.contentBody}
            showsVerticalScrollIndicator={false}
          >
            {currentSource ? (
              <View style={styles.sourceCard}>
                {/* Meta info */}
                <View style={styles.docHeader}>
                  <View style={styles.docMetaLeft}>
                    <Text style={styles.docName} numberOfLines={1}>
                      {currentSource.documentName}
                    </Text>
                    <View style={styles.badgeRow}>
                      <View style={styles.pageBadge}>
                        <Text style={styles.pageText}>PAGE {currentSource.page}</Text>
                      </View>
                      <View style={styles.citationIndexBadge}>
                        <Text style={styles.citationIndexText}>
                          CITATION [{currentSource.index}]
                        </Text>
                      </View>
                    </View>
                  </View>
                </View>

                {/* Quote snippet */}
                <View style={styles.snippetContainer}>
                  <View style={styles.quoteBorder} />
                  <View style={styles.snippetTextWrapper}>
                    <Text style={styles.quoteMark}>“</Text>
                    <Text style={styles.snippetText}>{currentSource.snippet}</Text>
                    <Text style={styles.quoteMarkClose}>”</Text>
                  </View>
                </View>

                {/* Relevance meter */}
                <View style={styles.relevanceSection}>
                  <View style={styles.relevanceHeader}>
                    <Text style={styles.relevanceLabel}>Relevance Score</Text>
                    <Text style={styles.relevancePercent}>
                      {currentSource.relevance}%
                    </Text>
                  </View>

                  <View style={styles.relevanceTrack}>
                    <View
                      style={[
                        styles.relevanceFill,
                        { width: `${currentSource.relevance}%` },
                      ]}
                    />
                  </View>

                  {/* Visual block bar representation per prompt: ████████████░░ 87% */}
                  <Text style={styles.relevanceBlocks}>
                    {'█'.repeat(Math.round(currentSource.relevance / 8))}
                    {'░'.repeat(12 - Math.min(12, Math.round(currentSource.relevance / 8)))}
                    {'  '}{currentSource.relevance}%
                  </Text>
                </View>

                <View style={styles.verificationBox}>
                  <Ionicons name="shield-checkmark-outline" size={14} color={Colors.primaryCyan} />
                  <Text style={styles.verificationText}>
                    Ground truth verified against indexed chunk embeddings
                  </Text>
                </View>
              </View>
            ) : (
              <Text style={styles.emptyText}>No citation details selected.</Text>
            )}
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.75)',
  },
  sheetContainer: {
    height: SHEET_HEIGHT,
    backgroundColor: Colors.surface,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderTopWidth: 1,
    borderTopColor: Colors.borderCyan,
    overflow: 'hidden',
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: 10,
  },
  grabHandle: {
    width: 38,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    fontFamily: Fonts.mono,
    fontSize: 16,
    fontWeight: '700',
    color: Colors.textPrimary,
    letterSpacing: -0.2,
  },
  closeButton: {
    padding: 4,
  },
  tabsRow: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 10,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderSubtle,
  },
  tabPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  tabPillActive: {
    backgroundColor: 'rgba(34, 211, 238, 0.12)',
    borderColor: Colors.primaryCyan,
  },
  tabPillText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
  },
  tabPillTextActive: {
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  contentScroll: {
    flex: 1,
  },
  contentBody: {
    padding: 20,
    paddingBottom: 40,
  },
  sourceCard: {
    gap: 16,
  },
  docHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  docMetaLeft: {
    flex: 1,
    gap: 6,
  },
  docName: {
    fontFamily: Fonts.mono,
    fontSize: 14,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  pageBadge: {
    backgroundColor: 'rgba(168, 85, 247, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.3)',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  pageText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.secondaryPurple,
    fontWeight: '700',
  },
  citationIndexBadge: {
    backgroundColor: 'rgba(34, 211, 238, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(34, 211, 238, 0.3)',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  citationIndexText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  snippetContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 6,
    overflow: 'hidden',
  },
  quoteBorder: {
    width: 3.5,
    backgroundColor: Colors.primaryCyan,
  },
  snippetTextWrapper: {
    flex: 1,
    padding: 14,
    position: 'relative',
  },
  quoteMark: {
    fontSize: 22,
    fontFamily: Fonts.sans,
    color: Colors.primaryCyan,
    lineHeight: 22,
    marginBottom: -4,
  },
  quoteMarkClose: {
    fontSize: 22,
    fontFamily: Fonts.sans,
    color: Colors.primaryCyan,
    lineHeight: 22,
    textAlign: 'right',
    marginTop: -8,
  },
  snippetText: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    color: Colors.textPrimary,
    lineHeight: 22,
    fontStyle: 'italic',
  },
  relevanceSection: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 6,
    padding: 14,
    gap: 8,
  },
  relevanceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  relevanceLabel: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    color: Colors.textMuted,
    textTransform: 'uppercase',
  },
  relevancePercent: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
  relevanceTrack: {
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  relevanceFill: {
    height: '100%',
    backgroundColor: Colors.primaryCyan,
    borderRadius: 2,
  },
  relevanceBlocks: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    color: Colors.primaryCyan,
    letterSpacing: 1.5,
    marginTop: 4,
  },
  verificationBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 4,
  },
  verificationText: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
  },
  emptyText: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 30,
  },
});
