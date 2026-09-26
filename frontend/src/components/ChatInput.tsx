import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  Pressable,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors, Fonts } from '@/constants/theme';
import { DocumentItem } from '@/types';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  selectedDocument?: DocumentItem | null;
  onClearContext?: () => void;
}

export function ChatInput({
  onSend,
  disabled = false,
  selectedDocument,
  onClearContext,
}: ChatInputProps) {
  const [text, setText] = useState('');

  const handleSend = () => {
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText('');
  };

  const isSendDisabled = !text.trim() || disabled;

  return (
    <View style={styles.container}>
      {/* Context pill if document is selected */}
      {selectedDocument && (
        <View style={styles.contextBar}>
          <View style={styles.contextPill}>
            <Ionicons name="document-text-outline" size={13} color={Colors.primaryCyan} />
            <Text style={styles.contextText} numberOfLines={1}>
              Context: {selectedDocument.name}
            </Text>
            {onClearContext && (
              <Pressable
                onPress={onClearContext}
                hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                style={styles.clearContextButton}
                accessibilityLabel="Clear document filter"
              >
                <Ionicons name="close" size={13} color={Colors.primaryCyan} />
              </Pressable>
            )}
          </View>
        </View>
      )}

      {/* Main input container */}
      <View style={styles.inputBox}>
        <TextInput
          style={styles.textInput}
          placeholder="Ask about your documents..."
          placeholderTextColor={Colors.textMuted}
          value={text}
          onChangeText={setText}
          multiline
          maxLength={1000}
          editable={!disabled}
          returnKeyType={Platform.OS === 'ios' ? 'default' : 'send'}
          blurOnSubmit={false}
        />

        <Pressable
          onPress={handleSend}
          disabled={isSendDisabled}
          style={({ pressed }) => [
            styles.sendButton,
            !isSendDisabled && styles.sendButtonActive,
            pressed && !isSendDisabled && styles.sendButtonPressed,
          ]}
          hitSlop={{ top: 6, bottom: 6, left: 6, right: 6 }}
          accessibilityRole="button"
          accessibilityLabel="Send message"
        >
          <Ionicons
            name="arrow-up"
            size={18}
            color={isSendDisabled ? Colors.textMuted : '#0A0A0F'}
          />
        </Pressable>
      </View>

      <Text style={styles.helperText}>
        Ask a question about your uploaded documents
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface,
    borderTopWidth: 1,
    borderTopColor: Colors.borderSubtle,
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: Platform.OS === 'ios' ? 12 : 8,
  },
  contextBar: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  contextPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(34, 211, 238, 0.08)',
    borderWidth: 1,
    borderColor: Colors.borderCyan,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    maxWidth: '90%',
  },
  contextText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.primaryCyan,
    flexShrink: 1,
  },
  clearContextButton: {
    marginLeft: 4,
  },
  inputBox: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    minHeight: 46,
    maxHeight: 110,
    gap: 8,
  },
  textInput: {
    flex: 1,
    fontFamily: Fonts.sans,
    fontSize: 14,
    color: Colors.textPrimary,
    paddingTop: 6,
    paddingBottom: 6,
    minHeight: 34,
  },
  sendButton: {
    width: 32,
    height: 32,
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  sendButtonActive: {
    backgroundColor: Colors.primaryCyan,
    shadowColor: Colors.primaryCyan,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 5,
  },
  sendButtonPressed: {
    opacity: 0.8,
  },
  helperText: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: 6,
    marginBottom: 2,
  },
});
