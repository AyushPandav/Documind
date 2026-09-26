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
  onSelectDocument: (doc: DocumentItem | null) => void;
  onUploadPress: () => void;
  isUploading: boolean;
  uploadProgress: number;
  uploadingDocName: string | null;
}

const SCREEN_HEIGHT = Dimensions.get('window').height;
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.78, 620);

export function DocumentsSheet({
  visible,
  onClose,
  documents,
  selectedDocument,
  onSelectDocument,
  onUploadPress,
  isUploading,
  uploadProgress,
  uploadingDocName,
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
            {/* Mobile upload drop area with dashed border */}
            <Pressable
              onPress={onUploadPress}
              disabled={isUploading}
              style={({ pressed }) => [
                styles.uploadArea,
                pressed && styles.uploadAreaPressed,
                isUploading && styles.uploadAreaDisabled,
              ]}
              accessibilityRole="button"
              accessibilityLabel="Tap to upload document"
            >
              <View style={styles.uploadIconContainer}>
                <Ionicons name="arrow-up" size={22} color={Colors.primaryCyan} />
              </View>
              <Text style={styles.uploadTitle}>+ Upload Document</Text>
              <Text style={styles.uploadSubtitle}>PDF • PNG • JPG</Text>
            </Pressable>

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

                {/* Simulated text bar per prompt: ████████████░░░░ 72% */}
                <View style={styles.progressMeta}>
                  <Text style={styles.asciiProgress}>
                    {'█'.repeat(Math.round(uploadProgress / 10))}
                    {'░'.repeat(10 - Math.min(10, Math.round(uploadProgress / 10)))}
                  </Text>
                  <Text style={styles.percentText}>{uploadProgress}%</Text>
                </View>
              </View>
            )}

            {/* Active filter helper if document selected */}
            {selectedDocument && (
              <View style={styles.filterBanner}>
                <Text style={styles.filterBannerText} numberOfLines={1}>
                  Active Context: {selectedDocument.name}
                </Text>
                <Pressable
                  onPress={() => onSelectDocument(null)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.clearFilterText}>Clear Filter</Text>
                </Pressable>
              </View>
            )}

            {/* Document List */}
            <View style={styles.listSection}>
              <Text style={styles.sectionHeader}>INDEXED CORPUS</Text>
              {documents.map((doc) => (
                <DocumentRow
                  key={doc.id}
                  document={doc}
                  isSelected={selectedDocument?.id === doc.id}
                  onSelect={(d) => {
                    // Toggle selection
                    if (selectedDocument?.id === d.id) {
                      onSelectDocument(null);
                    } else {
                      onSelectDocument(d);
                    }
                  }}
                />
              ))}
            </View>
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
  countBadge: {
    backgroundColor: 'rgba(34, 211, 238, 0.12)',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(34, 211, 238, 0.3)',
  },
  countText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    fontWeight: '700',
  },
  closeButton: {
    padding: 4,
  },
  contentScroll: {
    flex: 1,
  },
  contentBody: {
    padding: 20,
    paddingBottom: 40,
    gap: 16,
  },
  uploadArea: {
    borderWidth: 1.5,
    borderColor: Colors.borderCyan,
    borderStyle: 'dashed',
    borderRadius: 8,
    backgroundColor: 'rgba(34, 211, 238, 0.03)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
    gap: 6,
  },
  uploadAreaPressed: {
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
  },
  uploadAreaDisabled: {
    opacity: 0.5,
  },
  uploadIconContainer: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(34, 211, 238, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  uploadTitle: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
  uploadSubtitle: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    letterSpacing: 0.5,
  },
  uploadingCard: {
    backgroundColor: 'rgba(34, 211, 238, 0.05)',
    borderWidth: 1,
    borderColor: Colors.borderCyan,
    borderRadius: 8,
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
    fontWeight: '600',
    color: Colors.textPrimary,
    flex: 1,
    marginRight: 8,
  },
  uploadingStatus: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
  },
  progressTrack: {
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 1.5,
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
    fontSize: 11,
    color: Colors.primaryCyan,
    letterSpacing: 1.5,
  },
  percentText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
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
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  filterBannerText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    flex: 1,
    marginRight: 8,
  },
  clearFilterText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    textDecorationLine: 'underline',
  },
  listSection: {
    gap: 8,
  },
  sectionHeader: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    letterSpacing: 0.8,
  },
});
