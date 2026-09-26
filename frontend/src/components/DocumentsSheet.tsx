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
import { DocumentItem } from '@/types';
import { Colors, Fonts } from '@/constants/theme';
import { DocumentRow } from './DocumentRow';

interface DocumentsSheetProps {
  visible: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  selectedDocument: DocumentItem | null;
  selectedDocuments?: DocumentItem[];
  onSelectDocument: (doc: DocumentItem | null) => void;
  onToggleSelectDocument?: (doc: DocumentItem) => void;
  onSelectAllDocuments?: () => void;
  onClearDocumentSelection?: () => void;
  onUploadPress: () => void;
  onUploadImagesPress?: () => void;
  isUploading: boolean;
  uploadProgress: number;
  uploadingDocName: string | null;
  onAnalyzeRelatedness?: (docIds?: string[]) => void;
}

const SCREEN_HEIGHT = Dimensions.get('window').height;
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.85, 660);

export function DocumentsSheet({
  visible,
  onClose,
  documents,
  selectedDocument,
  selectedDocuments = [],
  onSelectDocument,
  onToggleSelectDocument,
  onSelectAllDocuments,
  onClearDocumentSelection,
  onUploadPress,
  onUploadImagesPress,
  isUploading,
  uploadProgress,
  uploadingDocName,
  onAnalyzeRelatedness,
}: DocumentsSheetProps) {
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

  const selectedCount = selectedDocuments.length;
  const isMultiSelection = selectedCount > 1;

  const handleDocumentTap = (doc: DocumentItem) => {
    if (onToggleSelectDocument) {
      onToggleSelectDocument(doc);
    } else {
      if (selectedDocument?.id === doc.id) {
        onSelectDocument(null);
      } else {
        onSelectDocument(doc);
      }
    }
  };

  const handleRelatednessClick = () => {
    if (!onAnalyzeRelatedness) return;
    onClose();
    if (selectedCount >= 2) {
      onAnalyzeRelatedness(selectedDocuments.map((d) => d.id));
    } else {
      onAnalyzeRelatedness();
    }
  };

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
              <Ionicons name="folder-outline" size={18} color={Colors.primaryCyan} />
              <Text style={styles.headerTitle}>Knowledge Base</Text>
              <View style={styles.countBadge}>
                <Text style={styles.countText}>{documents.length}</Text>
              </View>
            </View>
            <Pressable
              onPress={onClose}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              style={styles.closeButton}
              accessibilityLabel="Close documents drawer"
            >
              <Ionicons name="close" size={20} color={Colors.textMuted} />
            </Pressable>
          </View>

          <ScrollView
            style={styles.contentScroll}
            contentContainerStyle={styles.contentBody}
            showsVerticalScrollIndicator={false}
          >
            {/* Upload Area: Dual multi-format actions */}
            <View style={styles.uploadCardsContainer}>
              <Pressable
                onPress={onUploadPress}
                disabled={isUploading}
                style={({ pressed }) => [
                  styles.uploadArea,
                  pressed && styles.uploadAreaPressed,
                  isUploading && styles.uploadAreaDisabled,
                ]}
                accessibilityRole="button"
                accessibilityLabel="Upload files"
              >
                <View style={styles.uploadIconContainer}>
                  <Ionicons name="document-attach" size={20} color={Colors.primaryCyan} />
                </View>
                <View style={styles.uploadTextContainer}>
                  <Text style={styles.uploadTitle}>+ Upload Documents</Text>
                  <Text style={styles.uploadSubtitle}>PDF • DOCX • XLSX • TXT • CSV</Text>
                </View>
              </Pressable>

              {onUploadImagesPress && (
                <Pressable
                  onPress={onUploadImagesPress}
                  disabled={isUploading}
                  style={({ pressed }) => [
                    styles.uploadAreaPhoto,
                    pressed && styles.uploadAreaPressed,
                    isUploading && styles.uploadAreaDisabled,
                  ]}
                  accessibilityRole="button"
                  accessibilityLabel="Upload photos with multi-select"
                >
                  <View style={styles.uploadIconContainerPhoto}>
                    <Ionicons name="images" size={20} color="#38BDF8" />
                  </View>
                  <View style={styles.uploadTextContainer}>
                    <Text style={styles.uploadTitlePhoto}>+ Multi-Select Photos / Scans</Text>
                    <Text style={styles.uploadSubtitle}>Select multiple images from gallery</Text>
                  </View>
                </Pressable>
              )}
            </View>

            {/* Check Document Relatedness Action Card */}
            {documents.length >= 2 && onAnalyzeRelatedness && (
              <Pressable
                onPress={handleRelatednessClick}
                style={({ pressed }) => [
                  styles.relatednessCard,
                  selectedCount >= 2 && styles.relatednessCardHighlight,
                  pressed && styles.relatednessCardPressed,
                ]}
              >
                <View style={styles.relatednessLeft}>
                  <View
                    style={[
                      styles.relatednessIconCircle,
                      selectedCount >= 2 && styles.relatednessIconCircleHighlight,
                    ]}
                  >
                    <Ionicons name="git-network-outline" size={17} color={Colors.primaryCyan} />
                  </View>
                  <View style={styles.relatednessTexts}>
                    <Text style={styles.relatednessTitle}>
                      {selectedCount >= 2
                        ? `Check Relatedness of ${selectedCount} Selected Docs`
                        : 'Check Document Relatedness'}
                    </Text>
                    <Text style={styles.relatednessSubtitle}>
                      {selectedCount >= 2
                        ? `Correlate specifically the ${selectedCount} chosen files`
                        : `Select 2+ files below or compare all ${documents.length} files`}
                    </Text>
                  </View>
                </View>
                <Ionicons name="chevron-forward" size={16} color={Colors.primaryCyan} />
              </Pressable>
            )}

            {/* Active upload banner if uploading */}
            {isUploading && (
              <View style={styles.uploadingCard}>
                <View style={styles.uploadingHeader}>
                  <Text style={styles.uploadingName} numberOfLines={1}>
                    {uploadingDocName || 'document.pdf'}
                  </Text>
                  <Text style={styles.uploadingStatus}>
                    {uploadProgress < 40
                      ? 'Uploading...'
                      : uploadProgress < 75
                      ? 'OCR Extraction...'
                      : 'Indexing Chunks...'}
                  </Text>
                </View>

                {/* Progress bar */}
                <View style={styles.progressTrack}>
                  <View
                    style={[
                      styles.progressBar,
                      { width: `${uploadProgress}%` },
                    ]}
                  />
                </View>

                <View style={styles.progressMeta}>
                  <Text style={styles.asciiProgress}>
                    {'█'.repeat(Math.round(uploadProgress / 10))}
                    {'░'.repeat(10 - Math.min(10, Math.round(uploadProgress / 10)))}
                  </Text>
                  <Text style={styles.percentText}>{uploadProgress}%</Text>
                </View>
              </View>
            )}

            {/* Active Context Banner */}
            {selectedCount > 0 && (
              <View style={styles.filterBanner}>
                <View style={styles.filterBannerLeft}>
                  <Ionicons name="layers-outline" size={15} color={Colors.primaryCyan} />
                  <Text style={styles.filterBannerText} numberOfLines={1}>
                    {selectedCount === 1
                      ? `Context: ${selectedDocuments[0]?.name}`
                      : `Active Context: ${selectedCount} Documents Selected`}
                  </Text>
                </View>
                <Pressable
                  onPress={onClearDocumentSelection || (() => onSelectDocument(null))}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.clearFilterText}>Clear Selection</Text>
                </Pressable>
              </View>
            )}

            {/* Document List Header with Multi-Select Controls */}
            <View style={styles.listSection}>
              <View style={styles.corpusHeaderRow}>
                <Text style={styles.sectionHeader}>
                  INDEXED CORPUS ({documents.length})
                </Text>
                <View style={styles.selectionControls}>
                  {onSelectAllDocuments && (
                    <Pressable
                      onPress={onSelectAllDocuments}
                      hitSlop={6}
                      style={({ pressed }) => [styles.ctrlBtn, pressed && styles.pressed]}
                    >
                      <Text style={styles.ctrlText}>Select All</Text>
                    </Pressable>
                  )}
                  {selectedCount > 0 && onClearDocumentSelection && (
                    <>
                      <Text style={styles.ctrlDivider}>•</Text>
                      <Pressable
                        onPress={onClearDocumentSelection}
                        hitSlop={6}
                        style={({ pressed }) => [styles.ctrlBtn, pressed && styles.pressed]}
                      >
                        <Text style={styles.ctrlTextMuted}>Deselect</Text>
                      </Pressable>
                    </>
                  )}
                </View>
              </View>

              {/* Instructions Pill */}
              <View style={styles.multiSelectHint}>
                <Ionicons name="checkbox-outline" size={12} color={Colors.primaryCyan} />
                <Text style={styles.multiSelectHintText}>
                  Tap any document to select multiple files for correlation or chat
                </Text>
              </View>

              {/* Document Rows */}
              {documents.map((doc) => {
                const isSelected = selectedDocuments.length > 0
                  ? selectedDocuments.some((d) => d.id === doc.id)
                  : selectedDocument?.id === doc.id;

                return (
                  <DocumentRow
                    key={doc.id}
                    document={doc}
                    isSelected={isSelected}
                    onSelect={handleDocumentTap}
                  />
                );
              })}
            </View>
          </ScrollView>

          {/* Sticky Bottom Actions Bar when multiple documents are selected */}
          {selectedCount >= 2 && (
            <View style={styles.bottomActionBar}>
              <Pressable
                onPress={handleRelatednessClick}
                style={({ pressed }) => [
                  styles.bottomRelatedBtn,
                  pressed && styles.pressed,
                ]}
              >
                <Ionicons name="git-network" size={15} color="#0B101B" />
                <Text style={styles.bottomRelatedBtnText}>
                  Check Relatedness ({selectedCount})
                </Text>
              </Pressable>

              <Pressable
                onPress={onClose}
                style={({ pressed }) => [
                  styles.bottomChatBtn,
                  pressed && styles.pressed,
                ]}
              >
                <Ionicons name="chatbubbles-outline" size={15} color={Colors.primaryCyan} />
                <Text style={styles.bottomChatBtnText}>Chat with Selected</Text>
              </Pressable>
            </View>
          )}
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
    borderColor: 'rgba(0, 240, 255, 0.2)',
    height: SHEET_HEIGHT,
    paddingTop: 8,
    paddingBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -6 },
    shadowOpacity: 0.45,
    shadowRadius: 20,
    elevation: 24,
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: 6,
  },
  grabHandle: {
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 16,
    color: Colors.textPrimary,
  },
  countBadge: {
    backgroundColor: 'rgba(0, 240, 255, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    borderRadius: 12,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  countText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  contentScroll: {
    flex: 1,
  },
  contentBody: {
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 32,
    gap: 12,
  },
  uploadCardsContainer: {
    gap: 8,
  },
  uploadArea: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(34, 211, 238, 0.05)',
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: 'rgba(34, 211, 238, 0.35)',
    borderRadius: 12,
    padding: 12,
    gap: 12,
  },
  uploadAreaPhoto: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(56, 189, 248, 0.05)',
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: 'rgba(56, 189, 248, 0.35)',
    borderRadius: 12,
    padding: 12,
    gap: 12,
  },
  uploadAreaPressed: {
    opacity: 0.75,
    backgroundColor: 'rgba(34, 211, 238, 0.1)',
  },
  uploadAreaDisabled: {
    opacity: 0.5,
  },
  uploadIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(34, 211, 238, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  uploadIconContainerPhoto: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  uploadTextContainer: {
    flex: 1,
    gap: 2,
  },
  uploadTitle: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
  uploadTitlePhoto: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: '#38BDF8',
  },
  uploadSubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
  },
  relatednessCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(0, 240, 255, 0.05)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.22)',
    borderRadius: 12,
    padding: 12,
  },
  relatednessCardHighlight: {
    backgroundColor: 'rgba(0, 240, 255, 0.1)',
    borderColor: Colors.primaryCyan,
  },
  relatednessCardPressed: {
    backgroundColor: 'rgba(0, 240, 255, 0.16)',
  },
  relatednessLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flex: 1,
  },
  relatednessIconCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  relatednessIconCircleHighlight: {
    backgroundColor: 'rgba(0, 240, 255, 0.25)',
  },
  relatednessTexts: {
    gap: 2,
    flex: 1,
  },
  relatednessTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 13,
    color: Colors.textPrimary,
  },
  relatednessSubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
  },
  uploadingCard: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.25)',
    borderRadius: 10,
    padding: 12,
    gap: 8,
  },
  uploadingHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  uploadingName: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    color: Colors.textPrimary,
    flex: 1,
  },
  uploadingStatus: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.primaryCyan,
  },
  progressTrack: {
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: Colors.primaryCyan,
  },
  progressMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  asciiProgress: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.primaryCyan,
    letterSpacing: 1.5,
  },
  percentText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  filterBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
    borderWidth: 1,
    borderColor: Colors.borderCyan,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  filterBannerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  filterBannerText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    fontWeight: '600',
    flex: 1,
  },
  clearFilterText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
    textDecorationLine: 'underline',
  },
  listSection: {
    gap: 8,
    marginTop: 4,
  },
  corpusHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sectionHeader: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    letterSpacing: 0.8,
  },
  selectionControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  ctrlBtn: {
    paddingVertical: 2,
    paddingHorizontal: 4,
  },
  ctrlText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    fontWeight: '600',
  },
  ctrlTextMuted: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
  },
  ctrlDivider: {
    fontSize: 11,
    color: Colors.textMuted,
  },
  multiSelectHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.04)',
  },
  multiSelectHintText: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
    flex: 1,
  },
  bottomActionBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    backgroundColor: '#0E1524',
  },
  bottomRelatedBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: Colors.primaryCyan,
    paddingVertical: 10,
    borderRadius: 10,
  },
  bottomRelatedBtnText: {
    fontFamily: Fonts.sans,
    fontWeight: '700',
    fontSize: 12,
    color: '#0B101B',
  },
  bottomChatBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: 'rgba(0, 240, 255, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
    paddingVertical: 10,
    borderRadius: 10,
  },
  bottomChatBtnText: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 12,
    color: Colors.primaryCyan,
  },
  pressed: {
    opacity: 0.7,
  },
});
