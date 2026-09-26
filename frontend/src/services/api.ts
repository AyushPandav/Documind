import { Platform } from 'react-native';
import { DocumentItem, ChatMessage, CitationSource } from '@/types';

// Determine default host: 10.0.2.2 for Android emulator, localhost for iOS simulator & web
const getDefaultApiHost = () => {
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL || getDefaultApiHost();

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);
    const res = await fetch(`${API_BASE_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchBackendDocuments(): Promise<DocumentItem[] | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/documents`);
    if (!res.ok) return null;
    const data = await res.json();
    return data.map((d: any) => ({
      id: d.id,
      name: d.name,
      uri: d.path,
      size: d.size,
      pages: d.pages || 1,
      status: d.status,
      progress: d.progress || 100,
      uploadedAt: d.created_at || 'Recently',
    }));
  } catch (err) {
    console.log('[DocuMind API] Documents fetch skipped/offline:', err);
    return null;
  }
}

export async function uploadDocumentToBackend(
  fileUri: string,
  fileName: string,
  fileType: string = 'application/pdf'
): Promise<DocumentItem | null> {
  try {
    const formData = new FormData();
    // React Native FormData format
    formData.append('file', {
      uri: fileUri,
      name: fileName,
      type: fileType,
    } as any);

    const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!res.ok) return null;
    const data = await res.json();
    return {
      id: data.id,
      name: data.name,
      size: data.size,
      pages: 1,
      status: data.status,
      progress: data.progress,
      uploadedAt: 'Just now',
    };
  } catch (err) {
    console.log('[DocuMind API] Upload to backend error:', err);
    return null;
  }
}

export interface QueryBackendResult {
  id: string;
  answer: string;
  citations: CitationSource[];
  isInsufficientInfo: boolean;
  modelUsed: string;
}

export async function sendQueryToBackend(
  query: string,
  documentContext?: string | null,
  sessionId: string = 'default'
): Promise<QueryBackendResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        document_context: documentContext,
        session_id: sessionId,
      }),
    });

    if (!res.ok) return null;
    const data = await res.json();

    return {
      id: data.id,
      answer: data.content,
      citations: (data.citations || []).map((c: any) => ({
        id: c.id,
        index: c.index,
        documentId: c.documentId || 'doc-1',
        documentName: c.documentName || 'document.pdf',
        page: c.page || 1,
        snippet: c.snippet || '',
        relevance: c.relevance || 85,
      })),
      isInsufficientInfo: Boolean(data.is_insufficient_info),
      modelUsed: data.model_used || 'DocuMind RAG',
    };
  } catch (err) {
    console.log('[DocuMind API] Chat query error, using offline fallback:', err);
    return null;
  }
}

export async function performFheSearch(
  query: string,
  docFilter?: string | null
): Promise<any> {
  try {
    // 1. Client encryption simulation
    const encRes = await fetch(`${API_BASE_URL}/api/fhe/encrypt-query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    const encData = await encRes.json();

    // 2. Homomorphic search on server
    const searchRes = await fetch(`${API_BASE_URL}/api/fhe/secure-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        encrypted_query: encData.encrypted_ciphertext,
        doc_filter: docFilter,
        top_k: 3,
      }),
    });
    return await searchRes.json();
  } catch (err) {
    console.log('[DocuMind API] FHE Search error:', err);
    return null;
  }
}
