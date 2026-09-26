export type DocumentStatus = 'QUEUED' | 'OCR' | 'PROCESSING' | 'INDEXED';

export interface DocumentItem {
  id: string;
  name: string;
  uri?: string;
  size?: string;
  pages: number;
  status: DocumentStatus;
  progress?: number; // 0 to 100
  uploadedAt: string;
}

export type CitationSourceType = 'document' | 'web' | 'live_api' | 'search';

export interface CitationSource {
  id: string;
  index: number;
  sourceType?: CitationSourceType;
  documentId: string;
  documentName: string;
  page: number;
  snippet: string;
  relevance: number; // e.g. 87 for 87%
  url?: string | null;
  retrievedAt?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: CitationSource[];
  isInsufficientInfo?: boolean;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  documentFilter?: string | null;
  messageCount: number;
  lastMessageSnippet?: string;
}

export interface AuthUser {
  email: string;
  token: string;
}
