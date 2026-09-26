import React, { useRef, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Pressable,
} from 'react-native';

const formatDocName = (name?: string) => {
  if (!name) return '';
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
};
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
import { ChatsSheet } from '@/components/ChatsSheet';
import { RelatednessSheet } from '@/components/RelatednessSheet';
import { CitationSource } from '@/types';

export default function MainAppScreen() {
  const router = useRouter();
  const flatListRef = useRef<FlatList>(null);

  const {
    user,
    logout,
    documents,
    selectedDocument,
    selectedDocuments,
    selectedDocumentIds,
    setSelectedDocument,
    toggleDocumentSelection,
    selectAllDocuments,
    clearDocumentSelection,
    isUploading,
    uploadProgress,
    uploadingDocName,
    pickAndUploadDocument,
    pickAndUploadImages,
    sessions,
    activeSessionId,
    activeSession,
    messages,
    isGenerating,
    sendMessage,
    createNewChat,
    switchSession,
    deleteChat,
    renameChat,
    clearAllChats,
    isDocumentsSheetOpen,
    setIsDocumentsSheetOpen,
    isChatHistorySheetOpen,
    setIsChatHistorySheetOpen,
    relatednessResult,
    isAnalyzingRelatedness,
    isRelatednessSheetOpen,
    setIsRelatednessSheetOpen,
    analyzeRelatedness,
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

  const currentPrompts =
    selectedDocuments.length > 1
      ? [
          `Compare ${selectedDocuments[0]?.name.slice(0, 16)} and ${selectedDocuments[1]?.name.slice(0, 16)}`,
          'What are the key differences or conflicting guidelines between these files?',
          `Synthesize an executive summary across all ${selectedDocuments.length} documents`,
        ]
      : selectedDocument
      ? [
          `What is the primary topic of ${selectedDocument.name}?`,
          'What are the core requirements and policies mentioned?',
          'Provide a detailed section-by-section breakdown.',
        ]
      : [
          "What is the company's refund policy?",
          'How many days of leave are employees entitled to?',
          'What are the requirements mentioned in the document?',
        ];

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
      {/* 1. Main App Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <DocuMindLogo size="compact" />
        </View>

        <View style={styles.headerRight}>
          {/* Local Chat History Drawer Button */}
          <IconButton
            onPress={() => setIsChatHistorySheetOpen(true)}
            active={isChatHistorySheetOpen}
            badgeCount={sessions.length > 1 ? sessions.length : undefined}
            icon={
              <Ionicons
                name="chatbubbles-outline"
                size={17}
                color={
                  isChatHistorySheetOpen
                    ? Colors.primaryCyan
                    : Colors.textPrimary
                }
              />
            }
            accessibilityLabel="Open local chat history"
          />

          {/* Cross-Document Correlation / Relatedness Button */}
          <IconButton
            onPress={() => {
              setIsRelatednessSheetOpen(true);
            }}
            active={isRelatednessSheetOpen || (relatednessResult?.is_related ?? false)}
            badgeCount={documents.length >= 2 ? documents.length : undefined}
            icon={
              <Ionicons
                name="git-network-outline"
                size={17}
                color={
                  isRelatednessSheetOpen
                    ? Colors.primaryCyan
                    : documents.length >= 2
                    ? '#38BDF8'
                    : Colors.textPrimary
                }
              />
            }
            accessibilityLabel="Check cross-document relatedness"
          />

          {/* Documents Drawer Button */}
          <IconButton
            onPress={() => setIsDocumentsSheetOpen(true)}
            active={isDocumentsSheetOpen || selectedDocuments.length > 0}
            badgeCount={selectedDocuments.length > 0 ? selectedDocuments.length : documents.length}
            icon={
              <Ionicons
                name={selectedDocuments.length > 1 ? "layers-outline" : "folder-outline"}
                size={17}
                color={
                  isDocumentsSheetOpen || selectedDocuments.length > 0
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
                size={17}
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
                size={17}
                color={Colors.textMuted}
              />
            }
            accessibilityLabel="Log out"
          />
        </View>
      </View>

      {/* 2. Active Conversation Subheader Bar */}
      <View style={styles.subHeaderBar}>
        <Pressable
          onPress={() => setIsChatHistorySheetOpen(true)}
          style={({ pressed }) => [
            styles.sessionPill,
            pressed && styles.sessionPillPressed,
          ]}
        >
          <Ionicons name="chatbubble-ellipses" size={13} color={Colors.primaryCyan} />
          <Text style={styles.sessionPillText} numberOfLines={1}>
            {activeSession?.title || 'Current Conversation'}
          </Text>
          <Ionicons name="chevron-down" size={13} color={Colors.textMuted} />
        </Pressable>

        {/* Multi-document Active Context Pill */}
        {selectedDocuments.length > 0 && (
          <Pressable
            onPress={() => setIsDocumentsSheetOpen(true)}
            style={({ pressed }) => [
              styles.contextIndicatorPill,
              selectedDocuments.length > 1 && styles.contextIndicatorPillMulti,
              pressed && { opacity: 0.8 },
            ]}
          >
            <Ionicons
              name={selectedDocuments.length > 1 ? 'layers-outline' : 'document-text-outline'}
              size={12}
              color={Colors.primaryCyan}
            />
            <Text style={styles.contextIndicatorText} numberOfLines={1}>
              {selectedDocuments.length > 1
                ? `${selectedDocuments.length} Docs`
                : formatDocName(selectedDocuments[0].name)}
            </Text>
            <Pressable
              onPress={(e: any) => {
                e.stopPropagation?.();
                clearDocumentSelection();
              }}
              hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
            >
              <Ionicons name="close-circle" size={13} color={Colors.textMuted} />
            </Pressable>
          </Pressable>
        )}

        <Pressable
          onPress={() => createNewChat('New Conversation')}
          style={({ pressed }) => [
            styles.newChatPill,
            pressed && styles.newChatPillPressed,
          ]}
        >
          <Ionicons name="add" size={12} color={Colors.primaryCyan} />
          <Text style={styles.newChatPillText}>New</Text>
        </Pressable>
      </View>

      {/* 3. Main Chat Screen with Keyboard Avoidance */}
      <KeyboardAvoidingView
        style={styles.flexOne}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        <View style={styles.chatContainer}>
          {messages.length === 0 ? (
            /* Empty Chat State with Scrollable Viewport */
            <ScrollView
              style={styles.emptyScrollView}
              contentContainerStyle={styles.emptyContainer}
              keyboardShouldPersistTaps="handled"
              showsVerticalScrollIndicator={false}
            >
              <View
                style={[
                  styles.emptyIconOutline,
                  selectedDocuments.length > 1 && styles.emptyIconOutlineMulti,
                ]}
              >
                <Ionicons
                  name={
                    selectedDocuments.length > 1
                      ? 'layers-outline'
                      : 'document-text-outline'
                  }
                  size={32}
                  color={
                    selectedDocuments.length > 0
                      ? Colors.primaryCyan
                      : Colors.textMuted
                  }
                />
              </View>
              <Text style={styles.emptyTitle}>
                {selectedDocuments.length > 1
                  ? `Ready to query\n${selectedDocuments.length} Selected Documents`
                  : selectedDocument
                  ? `Ready to query\n${formatDocName(selectedDocument.name)}`
                  : 'Upload a document\nto get started'}
              </Text>
              <Text style={styles.emptySubtitle}>
                {selectedDocuments.length > 1
                  ? `Cross-referencing: ${selectedDocuments.map((d) => formatDocName(d.name)).join(', ')}\nAsk comparative questions, find discrepancies, or synthesize findings across all files.`
                  : selectedDocument
                  ? 'Ask anything about this document.\nResponses and history are stored locally only.'
                  : 'Upload a PDF, image, or document.\nYour chat is saved locally on device.'}
              </Text>

              {/* Multi-document chip preview */}
              {selectedDocuments.length > 1 && (
                <View style={styles.emptyChipsRow}>
                  {selectedDocuments.map((doc) => (
                    <View key={doc.id} style={styles.emptyDocChip}>
                      <Ionicons
                        name="document-text-outline"
                        size={11}
                        color={Colors.primaryCyan}
                      />
                      <Text style={styles.emptyDocChipText} numberOfLines={1}>
                        {formatDocName(doc.name)}
                      </Text>
                    </View>
                  ))}
                </View>
              )}

              <Pressable
                onPress={() => setIsDocumentsSheetOpen(true)}
                style={styles.emptyUploadButton}
              >
                <Text style={styles.emptyUploadText}>
                  {selectedDocuments.length > 1
                    ? `Manage Documents (${selectedDocuments.length} Selected)`
                    : selectedDocument
                    ? 'Switch Document'
                    : '+ Select Document'}
                </Text>
              </Pressable>

              {/* Suggested Prompts */}
              <View style={styles.suggestedPromptsContainer}>
                <Text style={styles.suggestedHeader}>
                  {selectedDocuments.length > 1
                    ? 'SUGGESTED MULTI-DOCUMENT QUERIES'
                    : 'SUGGESTED QUERIES'}
                </Text>
                {currentPrompts.map((prompt, idx) => (
                  <Pressable
                    key={idx}
                    onPress={() => sendMessage(prompt)}
                    style={({ pressed }) => [
                      styles.promptChip,
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <Text style={styles.promptChipText}>{prompt}</Text>
                  </Pressable>
                ))}
              </View>
            </ScrollView>
          ) : (
            /* Message Feed */
            <FlatList
              ref={flatListRef}
              data={messages}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => (
                <ChatMessageItem
                  message={item}
                  onCitationPress={handleCitationPress}
                />
              )}
              contentContainerStyle={styles.messageList}
              ListFooterComponent={
                isGenerating ? (
                  <View style={styles.loadingContainer}>
                    <LoadingDots />
                  </View>
                ) : null
              }
            />
          )}

          {/* 11 & 12. Floating Chat Input Bar */}
          <ChatInput
            onSend={sendMessage}
            disabled={isGenerating}
            selectedDocument={selectedDocument}
            selectedDocuments={selectedDocuments}
            onClearContext={clearDocumentSelection}
            onRemoveDocument={toggleDocumentSelection}
            onOpenDocumentsSheet={() => setIsDocumentsSheetOpen(true)}
          />
        </View>
      </KeyboardAvoidingView>

      {/* Local Chat History Bottom Sheet */}
      <ChatsSheet
        visible={isChatHistorySheetOpen}
        onClose={() => setIsChatHistorySheetOpen(false)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={switchSession}
        onNewChat={() => createNewChat('New Conversation')}
        onDeleteSession={deleteChat}
        onRenameSession={renameChat}
        onClearAllChats={clearAllChats}
      />

      {/* Sources Bottom Sheet */}
      <SourceSheet
        visible={isSourceSheetOpen}
        onClose={closeSourceSheet}
        activeSource={activeCitationSource}
        sourcesList={activeCitationList}
        onSelectSource={(src) => openSourceSheet(src, activeCitationList)}
      />

      {/* Documents Bottom Sheet */}
      <DocumentsSheet
        visible={isDocumentsSheetOpen}
        onClose={() => setIsDocumentsSheetOpen(false)}
        documents={documents}
        selectedDocument={selectedDocument}
        selectedDocuments={selectedDocuments}
        onSelectDocument={setSelectedDocument}
        onToggleSelectDocument={toggleDocumentSelection}
        onSelectAllDocuments={selectAllDocuments}
        onClearDocumentSelection={clearDocumentSelection}
        onUploadPress={pickAndUploadDocument}
        onUploadImagesPress={pickAndUploadImages}
        isUploading={isUploading}
        uploadProgress={uploadProgress}
        uploadingDocName={uploadingDocName}
        onAnalyzeRelatedness={(docIds) => {
          analyzeRelatedness(docIds);
          setIsRelatednessSheetOpen(true);
        }}
      />

      {/* Cross-Document Correlation & Relatedness Sheet */}
      <RelatednessSheet
        visible={isRelatednessSheetOpen}
        onClose={() => setIsRelatednessSheetOpen(false)}
        result={relatednessResult}
        loading={isAnalyzingRelatedness}
        onRefresh={() => analyzeRelatedness()}
        onSelectQueryContext={(prompt) => sendMessage(prompt)}
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
    height: 56,
    backgroundColor: Colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: Colors.borderCyan,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    zIndex: 10,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flexShrink: 0,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexShrink: 0,
  },
  subHeaderBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: 'rgba(15, 23, 42, 0.65)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  sessionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.18)',
    borderRadius: 20,
    paddingHorizontal: 10,
    paddingVertical: 5,
    maxWidth: '80%',
  },
  sessionPillPressed: {
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
  },
  sessionPillText: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 12,
    color: Colors.textPrimary,
    flexShrink: 1,
  },
  newChatPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: 'rgba(0, 240, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.25)',
    borderRadius: 14,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  newChatPillPressed: {
    backgroundColor: 'rgba(0, 240, 255, 0.16)',
  },
  newChatPillText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
    color: Colors.primaryCyan,
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
  emptyScrollView: {
    flex: 1,
  },
  emptyContainer: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 28,
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
  contextIndicatorPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(34, 211, 238, 0.3)',
    borderRadius: 14,
    paddingHorizontal: 8,
    paddingVertical: 4,
    maxWidth: 160,
  },
  contextIndicatorPillMulti: {
    backgroundColor: 'rgba(34, 211, 238, 0.14)',
    borderColor: Colors.borderCyan,
  },
  contextIndicatorText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '600',
    color: Colors.primaryCyan,
    flexShrink: 1,
  },
  emptyIconOutlineMulti: {
    borderColor: Colors.borderCyan,
    backgroundColor: 'rgba(34, 211, 238, 0.06)',
  },
  emptyChipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 6,
    marginBottom: 16,
    maxWidth: '92%',
  },
  emptyDocChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 4,
    maxWidth: 180,
  },
  emptyDocChipText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textPrimary,
    flexShrink: 1,
  },
});
