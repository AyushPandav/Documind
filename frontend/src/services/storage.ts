import AsyncStorage from '@react-native-async-storage/async-storage';
import { ChatMessage, ChatSession } from '@/types';
import { INITIAL_MESSAGES } from '@/data/mockData';

const SESSIONS_KEY = '@documind_chat_sessions_v1';
const ACTIVE_SESSION_ID_KEY = '@documind_active_session_id_v1';
const MESSAGES_PREFIX = '@documind_chat_messages_v1_';

// Fallback in-memory cache to guarantee zero-fail operation
const memoryStorage: Record<string, string> = {};

async function getItem(key: string): Promise<string | null> {
  try {
    const val = await AsyncStorage.getItem(key);
    if (val !== null) return val;
  } catch (err) {
    console.warn(`[Local Storage] AsyncStorage read error for ${key}:`, err);
  }

  // Web localStorage fallback
  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      const webVal = window.localStorage.getItem(key);
      if (webVal !== null) return webVal;
    } catch {}
  }

  return memoryStorage[key] || null;
}

async function setItem(key: string, value: string): Promise<void> {
  memoryStorage[key] = value;
  try {
    await AsyncStorage.setItem(key, value);
  } catch (err) {
    console.warn(`[Local Storage] AsyncStorage write error for ${key}:`, err);
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.setItem(key, value);
    } catch {}
  }
}

async function removeItem(key: string): Promise<void> {
  delete memoryStorage[key];
  try {
    await AsyncStorage.removeItem(key);
  } catch (err) {
    console.warn(`[Local Storage] AsyncStorage remove error for ${key}:`, err);
  }

  if (typeof window !== 'undefined' && window.localStorage) {
    try {
      window.localStorage.removeItem(key);
    } catch {}
  }
}

/**
 * Loads all chat sessions stored locally on device.
 * If empty, initializes a default starting session.
 */
export async function getLocalChatSessions(): Promise<ChatSession[]> {
  try {
    const raw = await getItem(SESSIONS_KEY);
    if (!raw) {
      // First boot: create initial welcome session
      const defaultSession: ChatSession = {
        id: 'session-default',
        title: 'Initial Consultation',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        documentFilter: null,
        messageCount: INITIAL_MESSAGES.length,
        lastMessageSnippet: INITIAL_MESSAGES[INITIAL_MESSAGES.length - 1]?.content.slice(0, 60) || 'Welcome to DocuMind',
      };
      await saveLocalChatSessions([defaultSession]);
      await saveSessionMessages(defaultSession.id, INITIAL_MESSAGES);
      await saveActiveSessionId(defaultSession.id);
      return [defaultSession];
    }
    return JSON.parse(raw);
  } catch (err) {
    console.error('[Local Storage] Failed to parse stored sessions:', err);
    return [];
  }
}

/**
 * Persists the list of chat sessions locally.
 */
export async function saveLocalChatSessions(sessions: ChatSession[]): Promise<void> {
  try {
    await setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch (err) {
    console.error('[Local Storage] Failed to save sessions:', err);
  }
}

/**
 * Retrieves the currently active session ID from local storage.
 */
export async function getActiveSessionId(): Promise<string | null> {
  return await getItem(ACTIVE_SESSION_ID_KEY);
}

/**
 * Persists the active session ID.
 */
export async function saveActiveSessionId(sessionId: string): Promise<void> {
  await setItem(ACTIVE_SESSION_ID_KEY, sessionId);
}

/**
 * Retrieves messages for a specific chat session from local storage.
 */
export async function getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  try {
    const raw = await getItem(`${MESSAGES_PREFIX}${sessionId}`);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (err) {
    console.error(`[Local Storage] Failed to parse messages for session ${sessionId}:`, err);
    return [];
  }
}

/**
 * Persists messages for a specific session locally on device.
 */
export async function saveSessionMessages(sessionId: string, messages: ChatMessage[]): Promise<void> {
  try {
    await setItem(`${MESSAGES_PREFIX}${sessionId}`, JSON.stringify(messages));
  } catch (err) {
    console.error(`[Local Storage] Failed to save messages for session ${sessionId}:`, err);
  }
}

/**
 * Deletes a session and its associated messages locally.
 */
export async function deleteLocalChatSession(sessionId: string): Promise<void> {
  try {
    await removeItem(`${MESSAGES_PREFIX}${sessionId}`);
    const sessions = await getLocalChatSessions();
    const updated = sessions.filter((s) => s.id !== sessionId);
    await saveLocalChatSessions(updated);

    const currentActive = await getActiveSessionId();
    if (currentActive === sessionId) {
      if (updated.length > 0) {
        await saveActiveSessionId(updated[0].id);
      } else {
        await removeItem(ACTIVE_SESSION_ID_KEY);
      }
    }
  } catch (err) {
    console.error(`[Local Storage] Failed to delete session ${sessionId}:`, err);
  }
}

/**
 * Clears all local chat history across all sessions.
 */
export async function clearAllLocalChats(): Promise<void> {
  try {
    const sessions = await getLocalChatSessions();
    for (const session of sessions) {
      await removeItem(`${MESSAGES_PREFIX}${session.id}`);
    }
    await removeItem(SESSIONS_KEY);
    await removeItem(ACTIVE_SESSION_ID_KEY);
  } catch (err) {
    console.error('[Local Storage] Failed to wipe all local chats:', err);
  }
}
