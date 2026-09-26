import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as DocumentPicker from 'expo-document-picker';
import { DocumentItem, ChatMessage, CitationSource, AuthUser, ChatSession } from '@/types';
import { INITIAL_DOCUMENTS, INITIAL_MESSAGES, MOCK_KNOWLEDGE_BASE } from '@/data/mockData';
import {
  checkBackendHealth,
  fetchBackendDocuments,
  uploadDocumentToBackend,
  sendQueryToBackend,
  performFheSearch,
} from '@/services/api';
import {
  getLocalChatSessions,
  saveLocalChatSessions,
  getActiveSessionId,
  saveActiveSessionId,
  getSessionMessages,
  saveSessionMessages,
  deleteLocalChatSession,
  clearAllLocalChats,
} from '@/services/storage';

interface AppContextType {
  // Auth
  user: AuthUser | null;
  login: (email: string) => Promise<boolean>;
  signup: (email: string) => Promise<boolean>;
  logout: () => void;

  // Backend connection
  isBackendConnected: boolean;

  // Documents
  documents: DocumentItem[];
  selectedDocument: DocumentItem | null;
  setSelectedDocument: (doc: DocumentItem | null) => void;
  isUploading: boolean;
  uploadProgress: number;
  uploadingDocName: string | null;
  pickAndUploadDocument: () => Promise<void>;

  // Chat & Local Persistence
  sessions: ChatSession[];
  activeSessionId: string;
  activeSession: ChatSession | null;
  messages: ChatMessage[];
  isGenerating: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => Promise<void>;
  createNewChat: (title?: string) => Promise<string>;
  switchSession: (sessionId: string) => Promise<void>;
  deleteChat: (sessionId: string) => Promise<void>;
  renameChat: (sessionId: string, newTitle: string) => Promise<void>;
  clearAllChats: () => Promise<void>;

  // Sheets
  isDocumentsSheetOpen: boolean;
  setIsDocumentsSheetOpen: (open: boolean) => void;
  isChatHistorySheetOpen: boolean;
  setIsChatHistorySheetOpen: (open: boolean) => void;
  activeCitationSource: CitationSource | null;
  activeCitationList: CitationSource[];
  isSourceSheetOpen: boolean;
  openSourceSheet: (source: CitationSource, allCitationsInMessage?: CitationSource[]) => void;
  closeSourceSheet: () => void;
  runFheSearch: (query: string) => Promise<any>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>({
    email: 'engineer@documind.ai',
    token: 'mock-jwt-token-123',
  });

  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [documents, setDocuments] = useState<DocumentItem[]>(INITIAL_DOCUMENTS);
  const [selectedDocument, setSelectedDocument] = useState<DocumentItem | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadingDocName, setUploadingDocName] = useState<string | null>(null);

  // Chat local persistence states
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>('session-default');
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [isGenerating, setIsGenerating] = useState(false);

  // Sheets
  const [isDocumentsSheetOpen, setIsDocumentsSheetOpen] = useState(false);
  const [isChatHistorySheetOpen, setIsChatHistorySheetOpen] = useState(false);
  const [isSourceSheetOpen, setIsSourceSheetOpen] = useState(false);
  const [activeCitationSource, setActiveCitationSource] = useState<CitationSource | null>(null);
  const [activeCitationList, setActiveCitationList] = useState<CitationSource[]>([]);

  // 1. Initialize local chat sessions and load stored messages on boot
  useEffect(() => {
    let isMounted = true;
    async function loadSessionsFromStorage() {
      try {
        const storedSessions = await getLocalChatSessions();
        if (!isMounted) return;
        setSessions(storedSessions);

        const storedActiveId = await getActiveSessionId();
        const targetId =
          storedActiveId && storedSessions.some((s) => s.id === storedActiveId)
            ? storedActiveId
            : storedSessions[0]?.id || 'session-default';

        setActiveSessionId(targetId);
        const storedMsgs = await getSessionMessages(targetId);
        if (isMounted) {
          setMessages(storedMsgs.length > 0 ? storedMsgs : INITIAL_MESSAGES);
        }
      } catch (err) {
        console.warn('[AppContext] Failed to load local chats from storage:', err);
      }
    }
    loadSessionsFromStorage();
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Check backend health & sync initial documents on mount
  useEffect(() => {
    let isMounted = true;
    async function syncWithBackend() {
      const isHealthy = await checkBackendHealth();
      if (!isMounted) return;
      setIsBackendConnected(isHealthy);

      if (isHealthy) {
        const backendDocs = await fetchBackendDocuments();
        if (backendDocs && backendDocs.length > 0 && isMounted) {
          setDocuments((prev) => {
            const existingIds = new Set(backendDocs.map((d) => d.id));
            const uniqueInitial = prev.filter((d) => !existingIds.has(d.id));
            return [...backendDocs, ...uniqueInitial];
          });
        }
      }
    }

    syncWithBackend();
    const interval = setInterval(syncWithBackend, 15000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const login = async (email: string) => {
    setUser({ email, token: 'mock-jwt-token-' + Date.now() });
    return true;
  };

  const signup = async (email: string) => {
    setUser({ email, token: 'mock-jwt-token-' + Date.now() });
    return true;
  };

  const logout = () => {
    setUser(null);
  };

  const pickAndUploadDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: '*/*',
        multiple: true,
        copyToCacheDirectory: true,
      });

      if (result.canceled || !result.assets || result.assets.length === 0) {
        return;
      }

      const totalFiles = result.assets.length;
      setIsUploading(true);
      setUploadingDocName(totalFiles > 1 ? `${totalFiles} documents` : (result.assets[0].name || 'document'));
      setUploadProgress(15);

      const uploadedDocs: DocumentItem[] = [];

      for (let i = 0; i < totalFiles; i++) {
        const asset = result.assets[i];
        setUploadingDocName(asset.name || `file_${i + 1}`);
        setUploadProgress(Math.round(((i + 0.3) / totalFiles) * 85));

        const backendDoc = await uploadDocumentToBackend(
          asset.uri,
          asset.name || `upload_${Date.now()}_${i}`,
          asset.mimeType || 'application/octet-stream'
        );

        if (backendDoc) {
          uploadedDocs.push(backendDoc);
        } else {
          const fallbackDoc: DocumentItem = {
            id: `doc-${Date.now()}-${i}`,
            name: asset.name || `document_${i + 1}`,
            uri: asset.uri,
            size: asset.size ? `${(asset.size / (1024 * 1024)).toFixed(1)} MB` : '1.2 MB',
            pages: 1,
            status: 'INDEXED',
            uploadedAt: 'Just now',
          };
          uploadedDocs.push(fallbackDoc);
        }

        setUploadProgress(Math.round(((i + 1) / totalFiles) * 95));
      }

      setUploadProgress(100);
      setDocuments((prev) => [...uploadedDocs, ...prev]);

      if (uploadedDocs.length > 0) {
        setSelectedDocument(uploadedDocs[0]);
      }

      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadingDocName(null);
      }, 600);
    } catch (err) {
      console.error('Error selecting documents:', err);
      setIsUploading(false);
      setUploadingDocName(null);
    }
  };

  // Helper to persist current session's messages and metadata locally
  const persistMessagesLocally = async (
    targetSessionId: string,
    updatedMessages: ChatMessage[],
    userQueryPrompt?: string
  ) => {
    try {
      await saveSessionMessages(targetSessionId, updatedMessages);
      const lastMsg = updatedMessages[updatedMessages.length - 1];

      setSessions((prevSessions) => {
        let matched = false;
        const nextSessions = prevSessions.map((s) => {
          if (s.id === targetSessionId) {
            matched = true;
            let title = s.title;
            if (
              (!title || title === 'New Conversation' || title === 'New Chat') &&
              userQueryPrompt
            ) {
              title =
                userQueryPrompt.length > 30
                  ? userQueryPrompt.slice(0, 30) + '...'
                  : userQueryPrompt;
            }
            return {
              ...s,
              title,
              messageCount: updatedMessages.length,
              lastMessageSnippet: lastMsg ? lastMsg.content.slice(0, 60) : 'No messages',
              updatedAt: new Date().toISOString(),
            };
          }
          return s;
        });

        if (!matched) {
          const newSession: ChatSession = {
            id: targetSessionId,
            title: userQueryPrompt ? (userQueryPrompt.length > 30 ? userQueryPrompt.slice(0, 30) + '...' : userQueryPrompt) : 'New Consultation',
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            documentFilter: selectedDocument ? selectedDocument.name : null,
            messageCount: updatedMessages.length,
            lastMessageSnippet: lastMsg ? lastMsg.content.slice(0, 60) : 'No messages',
          };
          nextSessions.unshift(newSession);
        }

        saveLocalChatSessions(nextSessions);
        return nextSessions;
      });
    } catch (e) {
      console.warn('[AppContext] Failed to persist messages locally:', e);
    }
  };

  // Chat Actions
  const createNewChat = async (title?: string): Promise<string> => {
    const newId = `session-${Date.now()}`;
    const newSession: ChatSession = {
      id: newId,
      title: title || 'New Conversation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      documentFilter: selectedDocument ? selectedDocument.name : null,
      messageCount: 0,
      lastMessageSnippet: 'Fresh consultation',
    };

    const nextSessions = [newSession, ...sessions];
    setSessions(nextSessions);
    setActiveSessionId(newId);
    setMessages([]);

    await saveLocalChatSessions(nextSessions);
    await saveActiveSessionId(newId);
    await saveSessionMessages(newId, []);

    return newId;
  };

  const switchSession = async (sessionId: string) => {
    if (sessionId === activeSessionId) return;
    setActiveSessionId(sessionId);
    await saveActiveSessionId(sessionId);
    const stored = await getSessionMessages(sessionId);
    setMessages(stored);
  };

  const deleteChat = async (sessionId: string) => {
    await deleteLocalChatSession(sessionId);
    const updated = sessions.filter((s) => s.id !== sessionId);
    setSessions(updated);

    if (activeSessionId === sessionId) {
      if (updated.length > 0) {
        const nextId = updated[0].id;
        setActiveSessionId(nextId);
        await saveActiveSessionId(nextId);
        const msgs = await getSessionMessages(nextId);
        setMessages(msgs);
      } else {
        await createNewChat('New Conversation');
      }
    }
  };

  const renameChat = async (sessionId: string, newTitle: string) => {
    const updated = sessions.map((s) =>
      s.id === sessionId ? { ...s, title: newTitle.trim(), updatedAt: new Date().toISOString() } : s
    );
    setSessions(updated);
    await saveLocalChatSessions(updated);
  };

  const clearChat = async () => {
    setMessages([]);
    if (activeSessionId) {
      await saveSessionMessages(activeSessionId, []);
      const updated = sessions.map((s) =>
        s.id === activeSessionId
          ? { ...s, messageCount: 0, lastMessageSnippet: 'Chat cleared', updatedAt: new Date().toISOString() }
          : s
      );
      setSessions(updated);
      await saveLocalChatSessions(updated);
    }
  };

  const clearAllChats = async () => {
    await clearAllLocalChats();
    const freshId = `session-${Date.now()}`;
    const freshSession: ChatSession = {
      id: freshId,
      title: 'New Consultation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      documentFilter: null,
      messageCount: 0,
      lastMessageSnippet: 'Started new chat',
    };
    setSessions([freshSession]);
    setActiveSessionId(freshId);
    setMessages([]);
    await saveLocalChatSessions([freshSession]);
    await saveActiveSessionId(freshId);
    await saveSessionMessages(freshId, []);
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isGenerating) return;

    const currentSessionId = activeSessionId;
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const messagesWithUser = [...messages, userMessage];
    setMessages(messagesWithUser);
    setIsGenerating(true);
    await persistMessagesLocally(currentSessionId, messagesWithUser, text.trim());

    try {
      // 1. Real RAG execution via FastAPI Gateway
      const backendResult = await sendQueryToBackend(
        text.trim(),
        selectedDocument ? selectedDocument.name : null,
        currentSessionId
      );

      if (backendResult) {
        const assistantMessage: ChatMessage = {
          id: backendResult.id || `msg-resp-${Date.now()}`,
          role: 'assistant',
          content: backendResult.answer,
          citations: backendResult.citations,
          isInsufficientInfo: backendResult.isInsufficientInfo,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        const messagesWithAssistant = [...messagesWithUser, assistantMessage];
        setMessages(messagesWithAssistant);
        setIsGenerating(false);
        await persistMessagesLocally(currentSessionId, messagesWithAssistant);
        return;
      }
    } catch (apiErr) {
      console.log('FastAPI Gateway offline or request error, switching to local offline model:', apiErr);
    }

    // 2. Offline Fallback Simulation
    setTimeout(async () => {
      const lower = text.toLowerCase();

      const isInsufficient =
        lower.includes('recipe') ||
        lower.includes('cake') ||
        lower.includes('weather') ||
        lower.includes('stock price') ||
        lower.includes('alien') ||
        lower.includes('mars');

      let assistantMessage: ChatMessage;

      if (isInsufficient) {
        assistantMessage = {
          id: `msg-resp-${Date.now()}`,
          role: 'assistant',
          content: "I couldn't find enough information in the uploaded documents to answer this.",
          isInsufficientInfo: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      } else {
        // Check against mock knowledge base
        const matched = MOCK_KNOWLEDGE_BASE.find((entry) =>
          entry.keywords.some((kw) => lower.includes(kw))
        );

        if (matched) {
          assistantMessage = {
            id: `msg-resp-${Date.now()}`,
            role: 'assistant',
            content: matched.answer,
            citations: matched.citations,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };
        } else {
          const isDescQuery =
            lower.includes('what is') ||
            lower.includes('about') ||
            lower.includes('describe') ||
            lower.includes('description') ||
            lower.includes('summarize') ||
            lower.includes('summary') ||
            lower.includes('overview') ||
            lower.includes('explain');

          const targetDocName = selectedDocument ? selectedDocument.name : 'company_policy.pdf';

          if (isDescQuery) {
            assistantMessage = {
              id: `msg-resp-${Date.now()}`,
              role: 'assistant',
              content: `This document, "${targetDocName}," serves as an authoritative guide covering key policies, procedures, and architectural standards [1]. It details implementation specifications, compliance obligations, and operational workflows designed to ensure seamless system execution [2].\n\nKey areas include core procedural requirements, security governance, and operational auditing protocols.`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              citations: [
                {
                  id: `cite-${Date.now()}-1`,
                  index: 1,
                  documentId: selectedDocument?.id || 'doc-1',
                  documentName: targetDocName,
                  page: 1,
                  snippet: `Overview and general purpose of ${targetDocName}: Outlines the foundational architecture and guidelines.`,
                  relevance: 95,
                },
                {
                  id: `cite-${Date.now()}-2`,
                  index: 2,
                  documentId: selectedDocument?.id || 'doc-1',
                  documentName: targetDocName,
                  page: 3,
                  snippet: `Procedural guidelines require authenticated logging across all integrated services with automated discrepancy flagging.`,
                  relevance: 90,
                },
              ],
            };
          } else {
            assistantMessage = {
              id: `msg-resp-${Date.now()}`,
              role: 'assistant',
              content: `According to section 4 of ${targetDocName}, all procedures must adhere to verifiable audit protocols [1]. Additional verification parameters are detailed in the appendix [2].`,
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              citations: [
                {
                  id: `cite-${Date.now()}-1`,
                  index: 1,
                  documentId: selectedDocument?.id || 'doc-2',
                  documentName: targetDocName,
                  page: 15,
                  snippet: `Procedural guidelines require authenticated logging across all integrated services with automated discrepancy flagging.`,
                  relevance: 91,
                },
                {
                  id: `cite-${Date.now()}-2`,
                  index: 2,
                  documentId: selectedDocument?.id || 'doc-2',
                  documentName: targetDocName,
                  page: 19,
                  snippet: `Verification parameters must be submitted to the document governance team for quarterly review.`,
                  relevance: 84,
                },
              ],
            };
          }
        }
      }

      const finalMessages = [...messagesWithUser, assistantMessage];
      setMessages(finalMessages);
      setIsGenerating(false);
      await persistMessagesLocally(currentSessionId, finalMessages);
    }, 900);
  };

  const openSourceSheet = (source: CitationSource, allCitationsInMessage?: CitationSource[]) => {
    setActiveCitationSource(source);
    if (allCitationsInMessage && allCitationsInMessage.length > 0) {
      setActiveCitationList(allCitationsInMessage);
    } else {
      setActiveCitationList([source]);
    }
    setIsSourceSheetOpen(true);
  };

  const closeSourceSheet = () => {
    setIsSourceSheetOpen(false);
  };

  const runFheSearch = async (query: string) => {
    return await performFheSearch(query, selectedDocument?.id);
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId) || null;

  return (
    <AppContext.Provider
      value={{
        user,
        login,
        signup,
        logout,
        isBackendConnected,
        documents,
        selectedDocument,
        setSelectedDocument,
        isUploading,
        uploadProgress,
        uploadingDocName,
        pickAndUploadDocument,
        sessions,
        activeSessionId,
        activeSession,
        messages,
        isGenerating,
        sendMessage,
        clearChat,
        createNewChat,
        switchSession,
        deleteChat,
        renameChat,
        clearAllChats,
        isDocumentsSheetOpen,
        setIsDocumentsSheetOpen,
        isChatHistorySheetOpen,
        setIsChatHistorySheetOpen,
        activeCitationSource,
        activeCitationList,
        isSourceSheetOpen,
        openSourceSheet,
        closeSourceSheet,
        runFheSearch,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
