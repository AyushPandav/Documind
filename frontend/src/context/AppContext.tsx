import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import * as DocumentPicker from 'expo-document-picker';
import { DocumentItem, ChatMessage, CitationSource, AuthUser } from '@/types';
import { INITIAL_DOCUMENTS, INITIAL_MESSAGES, MOCK_KNOWLEDGE_BASE } from '@/data/mockData';
import {
  checkBackendHealth,
  fetchBackendDocuments,
  uploadDocumentToBackend,
  sendQueryToBackend,
  performFheSearch,
} from '@/services/api';

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

  // Chat
  messages: ChatMessage[];
  isGenerating: boolean;
  sendMessage: (text: string) => Promise<void>;
  clearChat: () => void;

  // Sheets
  isDocumentsSheetOpen: boolean;
  setIsDocumentsSheetOpen: (open: boolean) => void;
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

  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [isGenerating, setIsGenerating] = useState(false);

  // Sheets
  const [isDocumentsSheetOpen, setIsDocumentsSheetOpen] = useState(false);
  const [isSourceSheetOpen, setIsSourceSheetOpen] = useState(false);
  const [activeCitationSource, setActiveCitationSource] = useState<CitationSource | null>(null);
  const [activeCitationList, setActiveCitationList] = useState<CitationSource[]>([]);

  // Check backend health & sync initial documents on mount
  useEffect(() => {
    let isMounted = true;
    async function syncWithBackend() {
      const isHealthy = await checkBackendHealth();
      if (!isMounted) return;
      setIsBackendConnected(isHealthy);

      if (isHealthy) {
        const backendDocs = await fetchBackendDocuments();
        if (backendDocs && backendDocs.length > 0 && isMounted) {
          // Merge backend documents with initial list
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

      const newDocs: DocumentItem[] = [];

      for (let i = 0; i < result.assets.length; i++) {
        const asset = result.assets[i];
        const fileName = asset.name || `uploaded_doc_${i + 1}`;
        const fileSize = asset.size ? `${(asset.size / (1024 * 1024)).toFixed(1)} MB` : '1.2 MB';
        const mimeType = asset.mimeType || 'application/octet-stream';
        const docId = `doc-${Date.now()}-${i}`;

        // Estimate pages based on extension
        const ext = fileName.split('.').pop()?.toLowerCase();
        let estimatedPages = 1;
        if (ext === 'pdf') {
          estimatedPages = Math.floor(Math.random() * 20) + 3;
        } else if (ext === 'docx' || ext === 'doc') {
          estimatedPages = Math.floor(Math.random() * 8) + 2;
        } else if (ext === 'pptx' || ext === 'ppt') {
          estimatedPages = Math.floor(Math.random() * 12) + 4;
        }

        const newDoc: DocumentItem = {
          id: docId,
          name: fileName,
          uri: asset.uri,
          size: fileSize,
          pages: estimatedPages,
          status: 'QUEUED',
          progress: 20,
          uploadedAt: 'Just now',
        };

        newDocs.push(newDoc);

        // Upload to live backend asynchronously
        uploadDocumentToBackend(asset.uri, fileName, mimeType)
          .then((backendDoc) => {
            if (backendDoc) {
              setDocuments((prev) =>
                prev.map((d) => (d.id === docId ? { ...d, id: backendDoc.id, status: 'INDEXED', progress: 100 } : d))
              );
            }
          })
          .catch((e) => console.log(`[DocuMind] Background upload for ${fileName}:`, e));
      }

      // Add all new documents to list immediately
      setDocuments((prev) => [...newDocs, ...prev]);
      if (newDocs.length > 0) {
        setSelectedDocument(newDocs[0]);
      }

      // Progress animation
      setTimeout(() => {
        setUploadProgress(50);
        setDocuments((prev) =>
          prev.map((d) => (newDocs.some((nd) => nd.id === d.id) ? { ...d, status: 'PROCESSING', progress: 50 } : d))
        );
      }, 800);

      setTimeout(() => {
        setUploadProgress(100);
        setIsUploading(false);
        setUploadingDocName(null);
        setDocuments((prev) =>
          prev.map((d) => (newDocs.some((nd) => nd.id === d.id) ? { ...d, status: 'INDEXED', progress: 100 } : d))
        );
      }, 1800);
    } catch (err) {
      console.error('Error selecting documents:', err);
      setIsUploading(false);
      setUploadingDocName(null);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isGenerating) return;

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsGenerating(true);

    try {
      // 1. Attempt Real RAG execution via FastAPI Gateway
      const backendResult = await sendQueryToBackend(
        text.trim(),
        selectedDocument ? selectedDocument.name : null
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
        setMessages((prev) => [...prev, assistantMessage]);
        setIsGenerating(false);
        return;
      }
    } catch (apiErr) {
      console.log('FastAPI Gateway offline or request error, switching to local offline model:', apiErr);
    }

    // 2. Offline Fallback Simulation
    setTimeout(() => {
      const lower = text.toLowerCase();

      const isInsufficient =
        lower.includes('recipe') ||
        lower.includes('cake') ||
        lower.includes('weather') ||
        lower.includes('stock price') ||
        lower.includes('alien') ||
        lower.includes('mars');

      if (isInsufficient) {
        const insufficientMessage: ChatMessage = {
          id: `msg-resp-${Date.now()}`,
          role: 'assistant',
          content: "I couldn't find enough information in the uploaded documents to answer this.",
          isInsufficientInfo: true,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, insufficientMessage]);
        setIsGenerating(false);
        return;
      }

      // Check against mock knowledge base
      let matched = MOCK_KNOWLEDGE_BASE.find((entry) =>
        entry.keywords.some((kw) => lower.includes(kw))
      );

      let assistantMessage: ChatMessage;

      if (matched) {
        assistantMessage = {
          id: `msg-resp-${Date.now()}`,
          role: 'assistant',
          content: matched.answer,
          citations: matched.citations,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      } else {
        // Check if asking for document description / summary
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

      setMessages((prev) => [...prev, assistantMessage]);
      setIsGenerating(false);
    }, 900);
  };

  const clearChat = () => {
    setMessages([]);
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
        messages,
        isGenerating,
        sendMessage,
        clearChat,
        isDocumentsSheetOpen,
        setIsDocumentsSheetOpen,
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
