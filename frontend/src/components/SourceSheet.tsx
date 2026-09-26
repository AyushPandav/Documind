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
  Linking,
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
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.75, 560);

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

  const sourceType = currentSource?.sourceType || 'document';
  const isWeb = sourceType === 'web' || sourceType === 'search';
  const isLive = sourceType === 'live_api';

  const sourceBadgeColor = isLive ? '#10B981' : isWeb ? '#38BDF8' : Colors.primaryCyan;
  const sourceBadgeLabel = isLive
    ? '🕐 Current Data'
    : isWeb
    ? '🌐 Live Web'
    : '📄 Internal Document';

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
              <Ionicons name="shield-checkmark-outline" size={18} color={Colors.primaryCyan} />
              <Text style={styles.headerTitle}>Evidence & Citations</Text>
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
            <View style={styles.tabsWrapper}>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.tabsScrollContent}
                nestedScrollEnabled={true}
              >
                {sourcesList.map((src) => {
                  const isSelected = src.id === currentSource?.id;
                  const itemIsLive = src.sourceType === 'live_api';
                  const itemIsWeb = src.sourceType === 'web' || src.sourceType === 'search';
                  const icon = itemIsLive ? 'time-outline' : itemIsWeb ? 'globe-outline' : 'document-text-outline';
                  const tabLabel = itemIsLive
                    ? `[${src.index}] Live API`
                    : itemIsWeb
                    ? `[${src.index}] Web`
                    : `[${src.index}] Page ${src.page}`;

                  return (
                    <Pressable
                      key={src.id}
                      onPress={() => onSelectSource?.(src)}
                      style={[
                        styles.tabPill,
                        isSelected && styles.tabPillActive,
                      ]}
                      hitSlop={{ top: 6, bottom: 6, left: 4, right: 4 }}
                    >
                      <Ionicons
                        name={icon as any}
                        size={12}
                        color={isSelected ? Colors.primaryCyan : Colors.textMuted}
                        style={{ marginRight: 4 }}
                      />
                      <Text
                        style={[
                          styles.tabPillText,
                          isSelected && styles.tabPillTextActive,
                        ]}
                      >
                        {tabLabel}
                      </Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
            </View>
          )}

          {/* Source Content */}
          <ScrollView
            style={styles.contentScroll}
            contentContainerStyle={styles.contentBody}
            showsVerticalScrollIndicator={true}
            nestedScrollEnabled={true}
          >
            {currentSource ? (
              <View style={styles.sourceCard}>
                {/* Meta info */}
                <View style={styles.docHeader}>
                  <View style={styles.docMetaLeft}>
                    <Text style={styles.docName} numberOfLines={2}>
                      {decodeURIComponent(currentSource.documentName)}
                    </Text>

                    <View style={styles.badgeRow}>
                      {/* Main source type badge */}
                      <View
                        style={[
                          styles.typeBadge,
                          {
                            borderColor: `${sourceBadgeColor}66`,
                            backgroundColor: `${sourceBadgeColor}15`,
                          },
                        ]}
                      >
                        <Text style={[styles.typeBadgeText, { color: sourceBadgeColor }]}>
                          {sourceBadgeLabel}
                        </Text>
                      </View>

                      {sourceType === 'document' && (
                        <View style={styles.pageBadge}>
                          <Text style={styles.pageText}>PAGE {currentSource.page}</Text>
                        </View>
                      )}

                      <View style={styles.citationIndexBadge}>
                        <Text style={styles.citationIndexText}>
                          CITATION [{currentSource.index}]
                        </Text>
                      </View>
                    </View>

                    {/* URL link for web source */}
                    {currentSource.url && (
                      <Pressable
                        onPress={() => currentSource.url && Linking.openURL(currentSource.url)}
                        style={styles.urlRow}
                      >
                        <Ionicons name="link-outline" size={13} color="#38BDF8" />
                        <Text style={styles.urlText} numberOfLines={1}>
                          {currentSource.url}
                        </Text>
                      </Pressable>
                    )}

                    {/* Timestamp */}
                    {currentSource.retrievedAt && (
                      <View style={styles.timeRow}>
                        <Ionicons name="time-outline" size={12} color={Colors.textMuted} />
                        <Text style={styles.timeText}>
                          Retrieved: {currentSource.retrievedAt.slice(0, 19).replace('T', ' ')} UTC
                        </Text>
                      </View>
                    )}
                  </View>
                </View>

                {/* Quote snippet */}
                <View style={styles.snippetContainer}>
                  <View style={[styles.quoteBorder, { backgroundColor: sourceBadgeColor }]} />
                  <View style={styles.snippetTextWrapper}>
                    <Text style={[styles.quoteMark, { color: `${sourceBadgeColor}88` }]}>“</Text>
                    <Text style={styles.snippetText}>{currentSource.snippet}</Text>
                    <Text style={[styles.quoteMarkClose, { color: `${sourceBadgeColor}88` }]}>”</Text>
                  </View>
                </View>

                {/* Relevance meter */}
                <View style={styles.relevanceSection}>
                  <View style={styles.relevanceHeader}>
                    <Text style={styles.relevanceLabel}>Relevance & Confidence</Text>
                    <Text style={[styles.relevancePercent, { color: sourceBadgeColor }]}>
                      {currentSource.relevance}%
                    </Text>
                  </View>

                  <View style={styles.relevanceTrack}>
                    <View
                      style={[
                        styles.relevanceFill,
                        {
                          width: `${currentSource.relevance}%`,
                          backgroundColor: sourceBadgeColor,
                        },
                      ]}
                    />
                  </View>

                  <Text style={styles.relevanceBlocks}>
                    {'█'.repeat(Math.round(currentSource.relevance / 8))}
                    {'░'.repeat(12 - Math.min(12, Math.round(currentSource.relevance / 8)))}
                    {'  '}{currentSource.relevance}%
                  </Text>
                </View>

                {/* Ground Truth Verification Box */}
                <View style={styles.verificationBox}>
                  <Ionicons name="shield-checkmark-outline" size={14} color={sourceBadgeColor} />
                  <Text style={styles.verificationText}>
                    {sourceType === 'document'
                      ? 'Ground truth verified against indexed chunk embeddings'
                      : isWeb
                      ? 'Live external evidence retrieved via real-time DuckDuckGo engine'
                      : 'Live data verified from real-time API services'}
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
    backgroundColor: 'rgba(0, 0, 0, 0.72)',
  },
  sheetContainer: {
    backgroundColor: '#0F0F1A',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    maxHeight: SHEET_HEIGHT,
    paddingBottom: 24,
  },
  handleContainer: {
    alignItems: 'center',
    paddingTop: 10,
    paddingBottom: 4,
  },
  grabHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.07)',
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    fontFamily: Fonts.sans,
    fontSize: 15,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  closeButton: {
    padding: 4,
  },
  tabsWrapper: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  tabsScrollContent: {
    flexDirection: 'row',
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  tabPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  tabPillActive: {
    backgroundColor: 'rgba(34, 211, 238, 0.15)',
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
    maxHeight: SHEET_HEIGHT - 120,
  },
  contentBody: {
    padding: 16,
  },
  sourceCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    padding: 14,
    gap: 12,
  },
  docHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
  },
  docMetaLeft: {
    flex: 1,
    gap: 6,
  },
  docName: {
    fontFamily: Fonts.sans,
    fontSize: 15,
    fontWeight: '700',
    color: Colors.textPrimary,
  },
  badgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
  },
  typeBadge: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
  },
  typeBadgeText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
  },
  pageBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  pageText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textSecondary,
    fontWeight: '600',
  },
  citationIndexBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(168, 85, 247, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.4)',
  },
  citationIndexText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.secondaryPurple,
    fontWeight: '700',
  },
  urlRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  urlText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: '#38BDF8',
    textDecorationLine: 'underline',
    flex: 1,
  },
  timeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  timeText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
  },
  snippetContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(0, 0, 0, 0.25)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
    overflow: 'hidden',
  },
  quoteBorder: {
    width: 3,
  },
  snippetTextWrapper: {
    flex: 1,
    padding: 10,
  },
  quoteMark: {
    fontFamily: Fonts.sans,
    fontSize: 22,
    lineHeight: 22,
  },
  snippetText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    lineHeight: 20,
    color: Colors.textSecondary,
    marginVertical: 2,
  },
  quoteMarkClose: {
    fontFamily: Fonts.sans,
    fontSize: 22,
    lineHeight: 22,
    alignSelf: 'flex-end',
  },
  relevanceSection: {
    gap: 6,
  },
  relevanceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  relevanceLabel: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
  },
  relevancePercent: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    fontWeight: '700',
  },
  relevanceTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    overflow: 'hidden',
  },
  relevanceFill: {
    height: '100%',
    borderRadius: 3,
  },
  relevanceBlocks: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
  },
  verificationBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 6,
    padding: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  verificationText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textSecondary,
    flex: 1,
  },
  emptyText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    color: Colors.textMuted,
    textAlign: 'center',
    paddingVertical: 20,
  },
});
