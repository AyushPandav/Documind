import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useApp } from '@/context/AppContext';
import { Colors, Fonts } from '@/constants/theme';
import { DocuMindLogo } from '@/components/DocuMindLogo';
import { IconButton } from '@/components/IconButton';
import { ChatMessageItem } from '@/components/ChatMessage';
import { LoadingDots } from '@/components/LoadingDots';
import { ChatInput } from '@/components/ChatInput';
import { SourceSheet } from '@/components/SourceSheet';
import { DocumentsSheet } from '@/components/DocumentsSheet';
import { CitationSource } from '@/types';

export default function MainAppScreen() {
  const router = useRouter();
  const flatListRef = useRef<FlatList>(null);

  const {
    user,
    logout,
    documents,
    selectedDocument,
    setSelectedDocument,
    isUploading,
    uploadProgress,
    uploadingDocName,
    pickAndUploadDocument,
    messages,
    isGenerating,
    sendMessage,
    isDocumentsSheetOpen,
    setIsDocumentsSheetOpen,
    activeCitationSource,
    activeCitationList,
    isSourceSheetOpen,
    openSourceSheet,
    closeSourceSheet,
  } = useApp();

  // Scroll to bottom when messages update or generating
  useEffect(() => {
    const timer = setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 100);
    return () => clearTimeout(timer);
  }, [messages, isGenerating]);

  const handleLogout = () => {
    logout();
    router.replace('/auth/login');
  };

  const handleCitationPress = (
    citation: CitationSource,
    allCitations?: CitationSource[]
  ) => {
    openSourceSheet(citation, allCitations);
  };

  const samplePrompts = [
    "What is the company's refund policy?",
    'How many days of leave are employees entitled to?',
    'What are the requirements mentioned in the document?',
  ];

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
      {/* 7. Main App Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <DocuMindLogo size="compact" />
        </View>

        <View style={styles.headerRight}>
          {/* Documents Drawer Button */}
          <IconButton
            onPress={() => setIsDocumentsSheetOpen(true)}
            active={isDocumentsSheetOpen || !!selectedDocument}
            badgeCount={documents.length}
            icon={
              <Ionicons
                name="folder-outline"
                size={18}
                color={
                  isDocumentsSheetOpen || !!selectedDocument
                    ? Colors.primaryCyan
                    : Colors.textPrimary
                }
              />
            }
            accessibilityLabel="Open documents drawer"
          />

          {/* Sources Sheet Button */}
          <IconButton
            onPress={() => {
              if (activeCitationSource) {
                openSourceSheet(activeCitationSource, activeCitationList);
              } else {
                // Find most recent citation if available
                const lastMsgWithCitations = [...messages]
                  .reverse()
                  .find((m) => m.citations && m.citations.length > 0);
                if (lastMsgWithCitations?.citations?.[0]) {
                  openSourceSheet(
                    lastMsgWithCitations.citations[0],
                    lastMsgWithCitations.citations
                  );
                } else {
                  // Fallback demo citation
                  openSourceSheet({
                    id: 'cite-default',
                    index: 1,
                    documentId: 'doc-2',
                    documentName: 'company_policy.pdf',
                    page: 12,
                    snippet:
                      'Refund requests must be submitted within 30 days of initial purchase. All requests require proof of payment and are issued to the original payment method.',
                    relevance: 94,
                  });
                }
              }
            }}
            active={isSourceSheetOpen}
            icon={
              <Ionicons
                name="bookmark-outline"
                size={18}
                color={isSourceSheetOpen ? Colors.primaryCyan : Colors.textPrimary}
              />
            }
            accessibilityLabel="Open sources viewer"
          />

          {/* Logout Button */}
          <IconButton
            onPress={handleLogout}
            icon={
              <Ionicons
                name="log-out-outline"
                size={18}
                color={Colors.textMuted}
              />
            }
            accessibilityLabel="Log out"
          />
        </View>
      </View>

      {/* Main Chat Screen with Keyboard Avoidance */}
      <KeyboardAvoidingView
        style={styles.flexOne}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        <View style={styles.chatContainer}>
          {messages.length === 0 ? (
            /* 18. Empty Chat State */
            <View style={styles.emptyContainer}>
              <View style={styles.emptyIconOutline}>
                <Ionicons
                  name="document-text-outline"
                  size={32}
                  color={Colors.textMuted}
                />
              </View>
              <Text style={styles.emptyTitle}>
                Upload a document{'\n'}to get started
              </Text>
              <Text style={styles.emptySubtitle}>
                Upload a PDF or image and{'\n'}ask questions about it.
              </Text>

              <Pressable
                onPress={() => setIsDocumentsSheetOpen(true)}
                style={styles.emptyUploadButton}
              >
                <Text style={styles.emptyUploadText}>+ Select Document</Text>
              </Pressable>

              <View style={styles.suggestedPromptsContainer}>
                <Text style={styles.suggestedHeader}>OR TRY ASKING:</Text>
                {samplePrompts.map((prompt, idx) => (
                  <Pressable
                    key={idx}
                    onPress={() => sendMessage(prompt)}
                    style={styles.promptChip}
                  >
                    <Text style={styles.promptChipText}>{prompt}</Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            <FlatList
              ref={flatListRef}
              data={messages}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.messageList}
              showsVerticalScrollIndicator={false}
              renderItem={({ item }) => (
                <ChatMessageItem
                  message={item}
                  onCitationPress={handleCitationPress}
                  activeCitationId={activeCitationSource?.id}
                />
              )}
              ListFooterComponent={
                isGenerating ? (
                  <View style={styles.loadingContainer}>
                    <LoadingDots />
                  </View>
                ) : null
              }
            />
          )}

          {/* 19. Chat Input */}
          <ChatInput
            onSend={sendMessage}
            disabled={isGenerating}
            selectedDocument={selectedDocument}
            onClearContext={() => setSelectedDocument(null)}
          />
        </View>
      </KeyboardAvoidingView>

      {/* 11 & 12. Sources Bottom Sheet */}
      <SourceSheet
        visible={isSourceSheetOpen}
        onClose={closeSourceSheet}
        activeSource={activeCitationSource}
        sourcesList={activeCitationList}
        onSelectSource={(src) => openSourceSheet(src, activeCitationList)}
      />

      {/* 13 & 14. Documents Bottom Sheet */}
      <DocumentsSheet
        visible={isDocumentsSheetOpen}
        onClose={() => setIsDocumentsSheetOpen(false)}
        documents={documents}
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
        onUploadPress={pickAndUploadDocument}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        uploadingDocName={uploadingDocName}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  flexOne: {
    flex: 1,
  },
  header: {
    height: 60,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderCyan,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    zIndex: 10,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  chatContainer: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  messageList: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    flexGrow: 1,
  },
  loadingContainer: {
    marginVertical: 4,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 32,
  },
  emptyIconOutline: {
    width: 60,
    height: 60,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    backgroundColor: 'rgba(255, 255, 255, 0.02)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 18,
  },
  emptyTitle: {
    fontFamily: Fonts.mono,
    fontSize: 16,
    fontWeight: '700',
    color: Colors.textPrimary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 8,
  },
  emptySubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 18,
    marginBottom: 20,
  },
  emptyUploadButton: {
    backgroundColor: 'rgba(34, 211, 238, 0.12)',
    borderWidth: 1,
    borderColor: Colors.borderCyan,
    borderRadius: 6,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginBottom: 24,
  },
  emptyUploadText: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
  suggestedPromptsContainer: {
    width: '100%',
    maxWidth: 380,
    gap: 8,
  },
  suggestedHeader: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    letterSpacing: 0.6,
    textAlign: 'center',
    marginBottom: 4,
  },
  promptChip: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  promptChipText: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textSecondary,
    textAlign: 'center',
  },
});
