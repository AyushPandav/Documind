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
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { DocumentRelatednessResult } from '@/services/api';
import { Colors, Fonts } from '@/constants/theme';

interface RelatednessSheetProps {
  visible: boolean;
  onClose: () => void;
  result: DocumentRelatednessResult | null;
  loading: boolean;
  onRefresh?: () => void;
  onSelectQueryContext?: (queryPrompt: string) => void;
}

const SCREEN_HEIGHT = Dimensions.get('window').height;
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.85, 680);

export function RelatednessSheet({
  visible,
  onClose,
  result,
  loading,
  onRefresh,
  onSelectQueryContext,
}: RelatednessSheetProps) {
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

  if (!visible) return null;

  const isRelated = result?.is_related ?? false;
  const score = result?.similarity_percentage ?? 0;
  const label = result?.relationship_label || 'Analysis in Progress';

  const badgeColor =
    score >= 70
      ? Colors.primaryCyan
      : score >= 45
      ? '#38BDF8'
      : score >= 25
      ? '#F59E0B'
      : '#94A3B8';

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

        {/* Sheet */}
        <Animated.View
          style={[
            styles.sheetContainer,
            { transform: [{ translateY: slideAnim }] },
          ]}
        >
          {/* Grab Handle */}
          <View style={styles.handleContainer}>
            <View style={styles.handle} />
          </View>

          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <View style={styles.iconCircle}>
                <Ionicons name="git-network" size={18} color={Colors.primaryCyan} />
              </View>
              <View>
                <Text style={styles.headerTitle}>Cross-Document Relatedness</Text>
                <Text style={styles.headerSubtitle}>
                  Dense Semantic • Lexical • CLIP Visual Correlation
                </Text>
              </View>
            </View>

            <View style={styles.headerActions}>
              {onRefresh && (
                <Pressable
                  onPress={onRefresh}
                  disabled={loading}
                  style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
                  hitSlop={6}
                >
                  <Ionicons
                    name="refresh-outline"
                    size={18}
                    color={loading ? Colors.textMuted : Colors.primaryCyan}
                  />
                </Pressable>
              )}
              <Pressable
                onPress={onClose}
                style={({ pressed }) => [styles.actionBtn, pressed && styles.pressed]}
                hitSlop={6}
              >
                <Ionicons name="close" size={20} color={Colors.textSecondary} />
              </Pressable>
            </View>
          </View>

          {/* Body */}
          <ScrollView
            style={styles.scrollList}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {loading ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={Colors.primaryCyan} />
                <Text style={styles.loadingTitle}>Analyzing Document Correlation</Text>
                <Text style={styles.loadingSubtitle}>
                  Comparing 384-d semantic embeddings, CLIP vision features, and topic fingerprints...
                </Text>
              </View>
            ) : !result ? (
              <View style={styles.emptyContainer}>
                <Ionicons name="document-text-outline" size={40} color={Colors.textMuted} />
                <Text style={styles.emptyTitle}>No Correlation Data</Text>
                <Text style={styles.emptySubtitle}>
                  Upload two or more documents to analyze their cross-document relationship.
                </Text>
              </View>
            ) : (
              <>
                {/* 1. Overall Verdict Banner */}
                <View style={[styles.verdictCard, { borderColor: `${badgeColor}55` }]}>
                  <View style={styles.verdictTopRow}>
                    <View style={styles.verdictLabelRow}>
                      <View style={[styles.statusDot, { backgroundColor: badgeColor }]} />
                      <Text style={[styles.verdictLabel, { color: badgeColor }]}>
                        {label}
                      </Text>
                    </View>
                    <View style={styles.scoreContainer}>
                      <Text style={[styles.scoreNumber, { color: badgeColor }]}>
                        {score}%
                      </Text>
                      <Text style={styles.scoreText}>similarity</Text>
                    </View>
                  </View>

                  {/* Progress Bar */}
                  <View style={styles.progressBarTrack}>
                    <View
                      style={[
                        styles.progressBarFill,
                        {
                          width: `${Math.max(5, Math.min(100, score))}%`,
                          backgroundColor: badgeColor,
                        },
                      ]}
                    />
                  </View>

                  {/* AI Synthesis Narrative */}
                  <View style={styles.narrativeBox}>
                    <View style={styles.narrativeHeaderRow}>
                      <Ionicons name="sparkles" size={13} color={Colors.primaryCyan} />
                      <Text style={styles.narrativeHeader}>AI Cross-Document Synthesis</Text>
                    </View>
                    <Text style={styles.narrativeText}>
                      {result.relationship_explanation}
                    </Text>
                  </View>
                </View>

                {/* 2. Shared Themes */}
                {result.shared_themes && result.shared_themes.length > 0 && (
                  <View style={styles.sectionContainer}>
                    <Text style={styles.sectionTitle}>SHARED THEMES & CONCEPTS</Text>
                    <View style={styles.tagsRow}>
                      {result.shared_themes.map((theme, idx) => (
                        <View key={idx} style={styles.themeTag}>
                          <Ionicons name="pricetag-outline" size={10} color={Colors.primaryCyan} />
                          <Text style={styles.themeTagText}>{theme}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}

                {/* 3. Pairwise Comparison Breakdown */}
                {result.pairwise_similarity && result.pairwise_similarity.length > 0 && (
                  <View style={styles.sectionContainer}>
                    <Text style={styles.sectionTitle}>
                      PAIRWISE CORRELATION ({result.pairwise_similarity.length} PAIRS)
                    </Text>
                    {result.pairwise_similarity.map((pair, idx) => {
                      const pairScore = pair.similarity_percentage;
                      const pairColor =
                        pairScore >= 70
                          ? Colors.primaryCyan
                          : pairScore >= 45
                          ? '#38BDF8'
                          : pairScore >= 25
                          ? '#F59E0B'
                          : '#94A3B8';

                      return (
                        <View key={idx} style={styles.pairCard}>
                          <View style={styles.pairHeaderRow}>
                            <View style={styles.pairNamesContainer}>
                              <Text style={styles.pairDocName} numberOfLines={1}>
                                {pair.doc_a}
                              </Text>
                              <Ionicons name="swap-horizontal" size={12} color={Colors.textMuted} />
                              <Text style={styles.pairDocName} numberOfLines={1}>
                                {pair.doc_b}
                              </Text>
                            </View>
                            <View style={[styles.pairBadge, { borderColor: `${pairColor}66` }]}>
                              <Text style={[styles.pairBadgeText, { color: pairColor }]}>
                                {pair.relationship} • {pairScore}%
                              </Text>
                            </View>
                          </View>

                          {/* Mini Progress */}
                          <View style={styles.miniTrack}>
                            <View
                              style={[
                                styles.miniFill,
                                { width: `${pairScore}%`, backgroundColor: pairColor },
                              ]}
                            />
                          </View>

                          {/* Metric stats */}
                          <View style={styles.metricStatsRow}>
                            <Text style={styles.metricStatText}>
                              Semantic: {Math.round(pair.semantic_score * 100)}%
                            </Text>
                            <Text style={styles.metricStatDivider}>•</Text>
                            <Text style={styles.metricStatText}>
                              Keywords: {Math.round(pair.lexical_score * 100)}%
                            </Text>
                            {pair.visual_score !== null && pair.visual_score !== undefined && (
                              <>
                                <Text style={styles.metricStatDivider}>•</Text>
                                <Text style={styles.metricStatText}>
                                  CLIP Visual: {Math.round(pair.visual_score * 100)}%
                                </Text>
                              </>
                            )}
                          </View>

                          {/* Shared keywords */}
                          {pair.shared_keywords && pair.shared_keywords.length > 0 && (
                            <View style={styles.sharedKwRow}>
                              <Text style={styles.sharedKwLabel}>Common:</Text>
                              <Text style={styles.sharedKwText} numberOfLines={1}>
                                {pair.shared_keywords.join(', ')}
                              </Text>
                            </View>
                          )}
                        </View>
                      );
                    })}
                  </View>
                )}

                {/* 4. Per-Document Summaries */}
                {result.doc_summaries && Object.keys(result.doc_summaries).length > 0 && (
                  <View style={styles.sectionContainer}>
                    <Text style={styles.sectionTitle}>DOCUMENT EXECUTIVE SUMMARIES</Text>
                    {Object.entries(result.doc_summaries).map(([name, summary], idx) => (
                      <View key={idx} style={styles.summaryCard}>
                        <View style={styles.summaryTitleRow}>
                          <Ionicons name="document-text" size={14} color={Colors.primaryCyan} />
                          <Text style={styles.summaryDocName} numberOfLines={1}>
                            {name}
                          </Text>
                        </View>
                        <Text style={styles.summaryBodyText}>{summary}</Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* 5. Recommendation Action */}
                <View style={styles.recommendationCard}>
                  <Ionicons name="information-circle-outline" size={16} color={Colors.primaryCyan} />
                  <Text style={styles.recommendationText}>
                    {result.recommendation}
                  </Text>
                </View>

                {onSelectQueryContext && isRelated && (
                  <Pressable
                    onPress={() => {
                      onSelectQueryContext('Compare the policies and key findings across these related documents:');
                      onClose();
                    }}
                    style={({ pressed }) => [
                      styles.queryAllBtn,
                      pressed && styles.queryAllBtnPressed,
                    ]}
                  >
                    <Ionicons name="chatbubbles" size={16} color="#0B101B" />
                    <Text style={styles.queryAllBtnText}>Query Across Related Documents</Text>
                  </Pressable>
                )}
              </>
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
    ...StyleSheet.absoluteFill,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
  },
  sheetContainer: {
    backgroundColor: '#0E1524',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.18)',
    height: SHEET_HEIGHT,
    paddingTop: 10,
    paddingBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -6 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
    elevation: 24,
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: 6,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.06)',
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 15,
    color: Colors.textPrimary,
  },
  headerSubtitle: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 2,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  actionBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
  scrollList: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 24,
    gap: 16,
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    gap: 12,
  },
  loadingTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 16,
    color: Colors.textPrimary,
    marginTop: 4,
  },
  loadingSubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    maxWidth: 280,
    lineHeight: 18,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 50,
    gap: 8,
  },
  emptyTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 15,
    color: Colors.textSecondary,
  },
  emptySubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    maxWidth: 260,
  },
  verdictCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    gap: 12,
  },
  verdictTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  verdictLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  verdictLabel: {
    fontFamily: Fonts.sans,
    fontWeight: '700',
    fontSize: 16,
  },
  scoreContainer: {
    alignItems: 'flex-end',
  },
  scoreNumber: {
    fontFamily: Fonts.mono,
    fontWeight: '700',
    fontSize: 20,
  },
  scoreText: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    color: Colors.textMuted,
    textTransform: 'uppercase',
  },
  progressBarTrack: {
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
  },
  narrativeBox: {
    backgroundColor: 'rgba(0, 0, 0, 0.25)',
    borderRadius: 10,
    padding: 12,
    gap: 6,
  },
  narrativeHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  narrativeHeader: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
    color: Colors.primaryCyan,
    letterSpacing: 0.3,
  },
  narrativeText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    color: Colors.textPrimary,
    lineHeight: 19,
  },
  sectionContainer: {
    gap: 8,
  },
  sectionTitle: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textMuted,
    letterSpacing: 0.8,
  },
  tagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  themeTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.25)',
    borderRadius: 12,
    paddingHorizontal: 9,
    paddingVertical: 4,
  },
  themeTagText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
  },
  pairCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 12,
    padding: 12,
    gap: 8,
  },
  pairHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  pairNamesContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flex: 1,
  },
  pairDocName: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 13,
    color: Colors.textPrimary,
    flexShrink: 1,
  },
  pairBadge: {
    borderWidth: 1,
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  pairBadgeText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '600',
  },
  miniTrack: {
    height: 4,
    borderRadius: 2,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    overflow: 'hidden',
  },
  miniFill: {
    height: '100%',
    borderRadius: 2,
  },
  metricStatsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metricStatText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
  },
  metricStatDivider: {
    fontSize: 10,
    color: Colors.textMuted,
  },
  sharedKwRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  sharedKwLabel: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
  },
  sharedKwText: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textSecondary,
    flex: 1,
  },
  summaryCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 10,
    padding: 10,
    gap: 4,
  },
  summaryTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  summaryDocName: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 12,
    color: Colors.primaryCyan,
  },
  summaryBodyText: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textSecondary,
    lineHeight: 17,
  },
  recommendationCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: 'rgba(0, 240, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.2)',
    borderRadius: 10,
    padding: 10,
  },
  recommendationText: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textPrimary,
    flex: 1,
    lineHeight: 17,
  },
  queryAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: Colors.primaryCyan,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 4,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  queryAllBtnPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.99 }],
  },
  queryAllBtnText: {
    fontFamily: Fonts.sans,
    fontWeight: '700',
    fontSize: 13,
    color: '#0B101B',
  },
});
