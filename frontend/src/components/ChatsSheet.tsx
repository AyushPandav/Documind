import React, { useEffect, useRef, useState } from 'react';
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
  TextInput,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { ChatSession } from '@/types';
import { Colors, Fonts } from '@/constants/theme';

interface ChatsSheetProps {
  visible: boolean;
  onClose: () => void;
  sessions: ChatSession[];
  activeSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
  onClearAllChats: () => void;
}

const SCREEN_HEIGHT = Dimensions.get('window').height;
const SHEET_HEIGHT = Math.min(SCREEN_HEIGHT * 0.8, 640);

export function ChatsSheet({
  visible,
  onClose,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onClearAllChats,
}: ChatsSheetProps) {
  const slideAnim = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');

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
      setEditingId(null);
    }
  }, [visible]);

  if (!visible) return null;

  const handleStartRename = (session: ChatSession) => {
    setEditingId(session.id);
    setEditingTitle(session.title);
  };

  const handleSaveRename = (sessionId: string) => {
    if (editingTitle.trim()) {
      onRenameSession(sessionId, editingTitle.trim());
    }
    setEditingId(null);
  };

  const confirmDelete = (session: ChatSession) => {
    onDeleteSession(session.id);
  };

  const confirmClearAll = () => {
    if (onClearAllChats) {
      onClearAllChats();
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
            <View style={styles.handle} />
          </View>

          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <View style={styles.iconCircle}>
                <Ionicons name="chatbubbles" size={18} color={Colors.primaryCyan} />
              </View>
              <View>
                <Text style={styles.headerTitle}>Local Chat History</Text>
                <View style={styles.privacyBadge}>
                  <Ionicons name="shield-checkmark" size={11} color={Colors.primaryCyan} />
                  <Text style={styles.privacyText}>Stored locally on-device • Zero Cloud</Text>
                </View>
              </View>
            </View>

            <Pressable
              onPress={onClose}
              style={({ pressed }) => [styles.closeBtn, pressed && styles.pressed]}
              hitSlop={8}
            >
              <Ionicons name="close" size={20} color={Colors.textSecondary} />
            </Pressable>
          </View>

          {/* Action Row: New Chat Button */}
          <View style={styles.actionRow}>
            <Pressable
              onPress={() => {
                onNewChat();
                onClose();
              }}
              style={({ pressed }) => [
                styles.newChatBtn,
                pressed && styles.newChatBtnPressed,
              ]}
            >
              <Ionicons name="add" size={18} color="#0B101B" />
              <Text style={styles.newChatBtnText}>Start New Chat</Text>
            </Pressable>
          </View>

          {/* Sessions List */}
          <ScrollView
            style={styles.scrollList}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {sessions.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="chatbubble-ellipses-outline" size={36} color={Colors.textMuted} />
                <Text style={styles.emptyTitle}>No saved chats</Text>
                <Text style={styles.emptySubtitle}>
                  Your conversations will be stored locally on this device.
                </Text>
              </View>
            ) : (
              sessions.map((session) => {
                const isActive = session.id === activeSessionId;
                const isEditing = editingId === session.id;

                const formattedDate = new Date(session.updatedAt || session.createdAt).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                });

                return (
                  <Pressable
                    key={session.id}
                    onPress={() => {
                      if (!isEditing) {
                        onSelectSession(session.id);
                        onClose();
                      }
                    }}
                    style={({ pressed }) => [
                      styles.sessionCard,
                      isActive && styles.sessionCardActive,
                      pressed && !isEditing && styles.sessionCardPressed,
                    ]}
                  >
                    <View style={styles.sessionLeftIcon}>
                      <Ionicons
                        name={isActive ? "chatbubble-ellipses" : "chatbubble-outline"}
                        size={18}
                        color={isActive ? Colors.primaryCyan : Colors.textMuted}
                      />
                    </View>

                    <View style={styles.sessionMain}>
                      {isEditing ? (
                        <View style={styles.renameRow}>
                          <TextInput
                            style={styles.renameInput}
                            value={editingTitle}
                            onChangeText={setEditingTitle}
                            autoFocus
                            onSubmitEditing={() => handleSaveRename(session.id)}
                            returnKeyType="done"
                          />
                          <Pressable
                            onPress={() => handleSaveRename(session.id)}
                            style={styles.renameConfirmBtn}
                          >
                            <Ionicons name="checkmark" size={16} color={Colors.primaryCyan} />
                          </Pressable>
                        </View>
                      ) : (
                        <View style={styles.sessionTitleRow}>
                          <Text
                            style={[
                              styles.sessionTitle,
                              isActive && styles.sessionTitleActive,
                            ]}
                            numberOfLines={1}
                          >
                            {session.title || 'Conversation'}
                          </Text>
                          {isActive && (
                            <View style={styles.activeTag}>
                              <Text style={styles.activeTagText}>Active</Text>
                            </View>
                          )}
                        </View>
                      )}

                      <Text style={styles.sessionSnippet} numberOfLines={1}>
                        {session.lastMessageSnippet || 'No messages yet'}
                      </Text>

                      <View style={styles.sessionMetaRow}>
                        <Text style={styles.sessionMetaText}>{formattedDate}</Text>
                        <Text style={styles.sessionMetaDivider}>•</Text>
                        <Text style={styles.sessionMetaText}>
                          {session.messageCount || 0} msgs
                        </Text>
                      </View>
                    </View>

                    {/* Actions: Edit & Delete */}
                    <View style={styles.sessionActions}>
                      {!isEditing && (
                        <Pressable
                          onPress={() => handleStartRename(session)}
                          style={({ pressed }) => [styles.actionBtn, pressed && styles.actionBtnPressed]}
                          hitSlop={6}
                        >
                          <Ionicons name="pencil-outline" size={15} color={Colors.textMuted} />
                        </Pressable>
                      )}

                      <Pressable
                        onPress={() => confirmDelete(session)}
                        style={({ pressed }) => [styles.deleteBtn, pressed && styles.deleteBtnPressed]}
                        hitSlop={6}
                      >
                        <Ionicons name="trash-outline" size={15} color="#EF4444" />
                      </Pressable>
                    </View>
                  </Pressable>
                );
              })
            )}
          </ScrollView>

          {/* Footer Info & Wipe Option */}
          {sessions.length > 0 && (
            <View style={styles.footer}>
              <Pressable
                onPress={confirmClearAll}
                style={({ pressed }) => [styles.clearAllBtn, pressed && styles.clearAllBtnPressed]}
              >
                <Ionicons name="trash-bin-outline" size={14} color="#EF4444" />
                <Text style={styles.clearAllText}>Delete All Local History</Text>
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
    backgroundColor: 'rgba(0, 0, 0, 0.65)',
  },
  sheetContainer: {
    backgroundColor: '#0F1626',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.15)',
    height: SHEET_HEIGHT,
    paddingTop: 10,
    paddingBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
    elevation: 20,
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: 6,
  },
  handle: {
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
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(0, 240, 255, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 16,
    color: Colors.textPrimary,
  },
  privacyBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  privacyText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.primaryCyan,
    letterSpacing: 0.2,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.7,
  },
  actionRow: {
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  newChatBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: Colors.primaryCyan,
    paddingVertical: 11,
    paddingHorizontal: 16,
    borderRadius: 12,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  newChatBtnPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.99 }],
  },
  newChatBtnText: {
    fontFamily: Fonts.sans,
    fontWeight: '700',
    fontSize: 14,
    color: '#0B101B',
  },
  scrollList: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 16,
    gap: 10,
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
    gap: 8,
  },
  emptyTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 15,
    color: Colors.textSecondary,
    marginTop: 4,
  },
  emptySubtitle: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    maxWidth: 240,
  },
  sessionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.07)',
    borderRadius: 14,
    padding: 12,
    gap: 12,
  },
  sessionCardActive: {
    backgroundColor: 'rgba(0, 240, 255, 0.06)',
    borderColor: 'rgba(0, 240, 255, 0.35)',
  },
  sessionCardPressed: {
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
  },
  sessionLeftIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  sessionMain: {
    flex: 1,
    gap: 3,
  },
  sessionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sessionTitle: {
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 14,
    color: Colors.textPrimary,
    flexShrink: 1,
  },
  sessionTitleActive: {
    color: Colors.primaryCyan,
  },
  activeTag: {
    backgroundColor: 'rgba(0, 240, 255, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(0, 240, 255, 0.3)',
  },
  activeTagText: {
    fontFamily: Fonts.mono,
    fontSize: 9,
    color: Colors.primaryCyan,
    textTransform: 'uppercase',
  },
  sessionSnippet: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: Colors.textSecondary,
  },
  sessionMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 2,
  },
  sessionMetaText: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
  },
  sessionMetaDivider: {
    fontSize: 10,
    color: Colors.textMuted,
  },
  sessionActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  actionBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
  },
  actionBtnPressed: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  deleteBtn: {
    padding: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
  },
  deleteBtnPressed: {
    backgroundColor: 'rgba(239, 68, 68, 0.25)',
  },
  renameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  renameInput: {
    flex: 1,
    fontFamily: Fonts.sans,
    fontWeight: '600',
    fontSize: 13,
    color: Colors.textPrimary,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: Colors.primaryCyan,
  },
  renameConfirmBtn: {
    padding: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(0, 240, 255, 0.15)',
  },
  footer: {
    paddingHorizontal: 20,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
    alignItems: 'center',
  },
  clearAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  clearAllBtnPressed: {
    opacity: 0.6,
  },
  clearAllText: {
    fontFamily: Fonts.sans,
    fontSize: 12,
    color: '#EF4444',
  },
});
