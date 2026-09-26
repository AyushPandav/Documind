import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ChatMessage as ChatMessageType, CitationSource } from '@/types';
import { Colors, Fonts } from '@/constants/theme';
import { CitationChip } from './CitationChip';
import { Ionicons } from '@expo/vector-icons';

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationPress?: (citation: CitationSource, allCitations?: CitationSource[]) => void;
  activeCitationId?: string;
}

export function ChatMessageItem({
  message,
  onCitationPress,
  activeCitationId,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isInsufficient = message.isInsufficientInfo;

  // Render text with interactive inline citation chips: e.g. "Text [1] more text [2]."
  const renderAssistantContent = () => {
    const text = message.content;
    const regex = /\[(\d+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      const matchStart = match.index;
      const matchEnd = regex.lastIndex;
      const citationNumber = parseInt(match[1], 10);

      // Add text leading up to citation
      if (matchStart > lastIndex) {
        parts.push(
          <Text key={`text-${lastIndex}`} style={styles.assistantText}>
            {text.substring(lastIndex, matchStart)}
          </Text>
        );
      }

      // Find matching citation object if available
      const citationObj = message.citations?.find(
        (c) => c.index === citationNumber
      ) || {
        id: `cite-${citationNumber}`,
        index: citationNumber,
        documentId: 'doc-default',
        documentName: 'company_policy.pdf',
        page: citationNumber * 6,
        snippet: 'Relevant excerpt extracted from indexed document store.',
        relevance: 88,
      };

      const isActive = activeCitationId === citationObj.id;

      parts.push(
        <CitationChip
          key={`chip-${matchStart}`}
          index={citationNumber}
          active={isActive}
          onPress={() => onCitationPress?.(citationObj, message.citations)}
        />
      );

      lastIndex = matchEnd;
    }

    if (lastIndex < text.length) {
      parts.push(
        <Text key={`text-${lastIndex}`} style={styles.assistantText}>
          {text.substring(lastIndex)}
        </Text>
      );
    }

    return (
      <Text style={styles.textWrapper}>
        {parts}
      </Text>
    );
  };

  if (isUser) {
    return (
      <View style={styles.userRow}>
        <View style={styles.userBubble}>
          <Text style={styles.userText}>{message.content}</Text>
          <Text style={styles.timestampUser}>{message.timestamp}</Text>
        </View>
      </View>
    );
  }

  // Insufficient Information state
  if (isInsufficient) {
    return (
      <View style={styles.assistantRow}>
        <View style={styles.insufficientBubble}>
          <View style={styles.insufficientHeader}>
            <Ionicons name="warning-outline" size={16} color={Colors.warning} />
            <Text style={styles.insufficientTitle}>Insufficient information</Text>
          </View>
          <Text style={styles.insufficientBody}>{message.content}</Text>
          <Text style={styles.timestampAssistant}>{message.timestamp}</Text>
        </View>
      </View>
    );
  }

  // Standard Assistant message with purple glass styling
  return (
    <View style={styles.assistantRow}>
      <View style={styles.assistantBubble}>
        <View style={styles.assistantHeader}>
          <View style={styles.assistantAccentDot} />
          <Text style={styles.assistantSender}>DocuMind AI</Text>
        </View>

        {renderAssistantContent()}

        {/* Quick citation summary pills if citations exist */}
        {message.citations && message.citations.length > 0 && (
          <View style={styles.citationsFooter}>
            <Text style={styles.sourcesLabel}>Sources:</Text>
            {message.citations.map((c) => (
              <CitationChip
                key={c.id}
                index={c.index}
                active={activeCitationId === c.id}
                onPress={() => onCitationPress?.(c, message.citations)}
              />
            ))}
          </View>
        )}

        <Text style={styles.timestampAssistant}>{message.timestamp}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  userRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginVertical: 6,
    paddingLeft: 40,
  },
  userBubble: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    borderBottomRightRadius: 2,
    paddingHorizontal: 14,
    paddingVertical: 10,
    maxWidth: '85%',
  },
  userText: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    color: Colors.textPrimary,
    lineHeight: 20,
  },
  timestampUser: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  assistantRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    marginVertical: 6,
    paddingRight: 32,
  },
  assistantBubble: {
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.3)',
    borderRadius: 8,
    borderBottomLeftRadius: 2,
    paddingHorizontal: 14,
    paddingVertical: 12,
    maxWidth: '92%',
    shadowColor: Colors.secondaryPurple,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
  },
  assistantHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  assistantAccentDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.secondaryPurple,
  },
  assistantSender: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '700',
    color: Colors.secondaryPurple,
    letterSpacing: 0.4,
  },
  textWrapper: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 22,
    color: Colors.textPrimary,
  },
  assistantText: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 22,
    color: Colors.textPrimary,
  },
  citationsFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.06)',
  },
  sourcesLabel: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    color: Colors.textMuted,
    marginRight: 4,
  },
  timestampAssistant: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 6,
  },
  insufficientBubble: {
    backgroundColor: Colors.warningBackground,
    borderWidth: 1,
    borderColor: Colors.warning,
    borderRadius: 8,
    borderBottomLeftRadius: 2,
    paddingHorizontal: 14,
    paddingVertical: 12,
    maxWidth: '92%',
  },
  insufficientHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6,
  },
  insufficientTitle: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    fontWeight: '700',
    color: Colors.warning,
  },
  insufficientBody: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    lineHeight: 19,
    color: Colors.textPrimary,
  },
});
