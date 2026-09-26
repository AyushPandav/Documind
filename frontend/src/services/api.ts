import { Platform } from 'react-native';
import Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system/legacy';
import { DocumentItem, ChatMessage, CitationSource } from '@/types';

// Determine default host:
// 1. Check EXPO_PUBLIC_API_URL
// 2. On physical device, resolve the developer machine's LAN IP from Metro (e.g. 192.168.x.x)
// 3. Fallback to 10.0.2.2 for Android emulator, localhost for iOS simulator & web
const getDefaultApiHost = () => {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }

  // Extract host IP from Expo Constants (works on physical Android/iOS devices)
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).manifest?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost;

  if (hostUri) {
    const ip = hostUri.split(':')[0];
    if (ip && ip !== 'localhost' && ip !== '127.0.0.1') {
      return `http://${ip}:8000`;
    }
  }

  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000';
  }
  return 'http://localhost:8000';
};

export const API_BASE_URL = getDefaultApiHost();

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
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
    return data.map((d: any) => {
      let cleanName = d.name || '';
      try {
        cleanName = decodeURIComponent(cleanName);
      } catch {
        // fallback
      }
      return {
        id: d.id,
        name: cleanName,
        uri: d.path,
        size: d.size,
        pages: d.pages || 1,
        status: d.status,
        progress: d.progress || 100,
        uploadedAt: d.created_at || 'Recently',
      };
    });
  } catch (err) {
    console.log('[DocuMind API] Documents fetch skipped/offline:', err);
    return null;
  }
}

/**
 * Uploads a single document to the FastAPI backend.
 * Uses native FileSystem.uploadAsync on mobile (Android/iOS) to prevent
 * "Unsupported FormDataPart implementation" errors with WinterCG fetch.
 * Uses fetch + Blob on Web.
 */
export async function uploadDocumentToBackend(
  fileUri: string,
  fileName: string,
  fileType: string = 'application/octet-stream'
): Promise<DocumentItem | null> {
  try {
    const uploadUrl = `${API_BASE_URL}/api/documents/upload`;
    const base64UploadUrl = `${API_BASE_URL}/api/documents/upload-base64`;

    // ── 1. Native Mobile: Attempt FileSystem.uploadAsync (Native Multipart) ──
    if (Platform.OS !== 'web' && FileSystem && typeof FileSystem.uploadAsync === 'function') {
      try {
        console.log(`[DocuMind API] Uploading ${fileName} via FileSystem.uploadAsync to ${uploadUrl}`);
        
        // uploadType 1 is MULTIPART (defined in FileSystemUploadType.MULTIPART)
        const uploadResult = await FileSystem.uploadAsync(uploadUrl, fileUri, {
          httpMethod: 'POST',
          uploadType: 1 as any,
          fieldName: 'file',
          mimeType: fileType,
          parameters: {},
        });

        if (uploadResult.status >= 200 && uploadResult.status < 300) {
          const data = JSON.parse(uploadResult.body);
          console.log(`[DocuMind API] uploadAsync SUCCESS for ${fileName}:`, data.id);
          return {
            id: data.id,
            name: decodeURIComponent(data.name || fileName),
            size: data.size,
            pages: data.pages || 1,
            status: data.status,
            progress: data.progress,
            uploadedAt: 'Just now',
          };
        } else {
          console.warn(`[DocuMind API] uploadAsync returned status ${uploadResult.status}, trying Base64 fallback...`);
        }
      } catch (uploadAsyncErr) {
        console.warn(`[DocuMind API] uploadAsync error (${uploadAsyncErr}), switching to Base64 JSON fallback...`);
      }

      // ── 2. Native Mobile Fail-safe: Base64 JSON Upload (100% reliable) ──
      try {
        console.log(`[DocuMind API] Uploading ${fileName} via Base64 JSON to ${base64UploadUrl}`);
        const base64Data = await FileSystem.readAsStringAsync(fileUri, {
          encoding: 'base64' as any,
        });

        const b64Res = await fetch(base64UploadUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            filename: fileName,
            file_base64: base64Data,
            mime_type: fileType,
          }),
        });

        if (b64Res.ok) {
          const data = await b64Res.json();
          console.log(`[DocuMind API] Base64 upload SUCCESS for ${fileName}:`, data.id);
          return {
            id: data.id,
            name: decodeURIComponent(data.name || fileName),
            size: data.size,
            pages: data.pages || 1,
            status: data.status,
            progress: data.progress,
            uploadedAt: 'Just now',
          };
        } else {
          const errText = await b64Res.text();
          console.warn(`[DocuMind API] Base64 upload HTTP ${b64Res.status}:`, errText);
        }
      } catch (b64Err) {
        console.warn(`[DocuMind API] Base64 upload error:`, b64Err);
      }
    }

    // ── 3. Fallback / Web: Fetch Blob and append to standard FormData ──
    console.log(`[DocuMind API] Uploading ${fileName} via Web FormData fallback to ${uploadUrl}`);
    const localRes = await fetch(fileUri);
    const blob = await localRes.blob();

    const formData = new FormData();
    formData.append('file', blob, fileName);

    const res = await fetch(uploadUrl, {
      method: 'POST',
      body: formData,
    });

    if (res.ok) {
      const data = await res.json();
      return {
        id: data.id,
        name: data.name,
        size: data.size,
        pages: data.pages || 1,
        status: data.status,
        progress: data.progress,
        uploadedAt: 'Just now',
      };
    } else {
      const errText = await res.text();
      console.warn(`[DocuMind API] FormData upload HTTP ${res.status}:`, errText);
      return null;
    }
  } catch (err) {
    console.log('[DocuMind API] Upload to backend error:', err);
    return null;
  }
}

/**
 * Uploads multiple documents concurrently to the backend.
 */
export async function uploadBatchDocumentsToBackend(
  files: Array<{ uri: string; name: string; type?: string }>
): Promise<DocumentItem[]> {
  const uploadPromises = files.map((f) =>
    uploadDocumentToBackend(f.uri, f.name, f.type || 'application/octet-stream')
  );
  const results = await Promise.all(uploadPromises);
  return results.filter((d): d is DocumentItem => d !== null);
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
  docFilter?: string | null,
  topK: number = 3
): Promise<any | null> {
  try {
    // 1. Client encryption simulation
    const encRes = await fetch(`${API_BASE_URL}/api/fhe/encrypt-query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });
    if (!encRes.ok) return null;
    const encData = await encRes.json();

    // 2. Homomorphic search on server
    const searchRes = await fetch(`${API_BASE_URL}/api/fhe/secure-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        encrypted_query: encData.encrypted_ciphertext,
        doc_filter: docFilter || null,
        top_k: topK,
      }),
    });

    if (!searchRes.ok) return null;
    return await searchRes.json();
  } catch (err) {
    console.log('[DocuMind API] FHE search offline:', err);
    return null;
  }
}

export interface VisualSearchResultItem {
  chunk_id: string;
  doc_id: string;
  doc_name: string;
  page_number: number;
  visual_similarity_score: number;
  category: string;
  classification_confidence: number;
  suggested_route: string;
  pii_redacted: boolean;
  faces_detected: number;
  snippet: string;
}

export interface VisualSearchResponse {
  query: string;
  total_visual_pages: number;
  results_count: number;
  results: VisualSearchResultItem[];
}

/**
 * Visual Multimodal Search using CLIP zero-shot raw image embeddings.
 * Enables queries like 'find all pages with a pie chart' or 'show invoices with stamps'.
 */
export async function performVisualSearch(
  query: string,
  topK: number = 5,
  minSimilarity: number = 0.15
): Promise<VisualSearchResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/documents/visual-search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK, min_similarity: minSimilarity }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.log('[DocuMind API] Visual search offline:', err);
    return null;
  }
}

/**
 * Fetch forensics & EXIF/DPI metadata alongside PII face redaction status for a document.
 */
export async function fetchDocumentForensics(docId: string): Promise<any | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/documents/${docId}/forensics`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.log('[DocuMind API] Forensics fetch offline:', err);
    return null;
  }
}

export interface PairwiseCorrelation {
  doc_a: string;
  doc_b: string;
  composite_score: number;
  similarity_percentage: number;
  semantic_score: number;
  lexical_score: number;
  visual_score: number | null;
  shared_keywords: string[];
  relationship: string;
}

export interface DocumentRelatednessResult {
  is_related: boolean;
  similarity_percentage: number;
  relationship_label: string;
  relationship_explanation: string;
  document_count: number;
  shared_themes: string[];
  doc_summaries: Record<string, string>;
  keyword_fingerprints: Record<string, string[]>;
  pairwise_similarity: PairwiseCorrelation[];
  recommendation: string;
}

/**
 * Checks whether multiple uploaded documents are topically or visually related.
 * Computes dense semantic vectors, CLIP multimodal similarity, and TF-IDF Jaccard overlap,
 * with AI relationship narrative synthesis.
 */
export async function checkDocumentsRelatedness(
  docIds?: string[]
): Promise<DocumentRelatednessResult | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/documents/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(docIds && docIds.length > 0 ? { doc_ids: docIds } : {}),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.log('[DocuMind API] Relatedness analysis error:', err);
    return null;
  }
}
