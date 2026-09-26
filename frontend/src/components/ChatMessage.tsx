import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { ChatMessage as ChatMessageType, CitationSource } from '@/types';
import { Colors, Fonts } from '@/constants/theme';
import { CitationChip } from './CitationChip';
import { VoiceoverButton } from './VoiceoverButton';
import { Ionicons } from '@expo/vector-icons';

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationPress?: (citation: CitationSource, allCitations?: CitationSource[]) => void;
  activeCitationId?: string;
}

// ─── Minimal inline markdown renderer ──────────────────────────────────────────
// Handles: ### headers, **bold**, *italic*, `code`, bullet lists, numbered lists
// and inline citation chips [N].
function renderMarkdownContent(
  rawText: string,
  citations: CitationSource[] | undefined,
  activeCitationId: string | undefined,
  onCitationPress: ((c: CitationSource, all?: CitationSource[]) => void) | undefined
): React.ReactNode[] {
  const lines = rawText.split('\n');
  const nodes: React.ReactNode[] = [];
  let key = 0;

  const resolveCitation = (n: number): CitationSource =>
    citations?.find((c) => c.index === n) || {
      id: `cite-${n}`,
      index: n,
      sourceType: 'document',
      documentId: 'doc-default',
      documentName: 'document.pdf',
      page: n * 4,
      snippet: 'Relevant excerpt from indexed document.',
      relevance: 85,
    };

  // Render a span of inline text (bold/italic/code/citations)
  const renderInline = (text: string, baseStyle: object): React.ReactNode[] => {
    // Split on citation markers [N], **bold**, *italic*, `code`
    const tokenRegex = /(\[(\d+)\]|\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g;
    const parts: React.ReactNode[] = [];
    let last = 0;
    let m: RegExpExecArray | null;

    while ((m = tokenRegex.exec(text)) !== null) {
      if (m.index > last) {
        parts.push(
          <Text key={key++} style={baseStyle}>
            {text.slice(last, m.index)}
          </Text>
        );
      }

      if (m[2]) {
        // Citation [N]
        const n = parseInt(m[2], 10);
        const c = resolveCitation(n);
        parts.push(
          <CitationChip
            key={key++}
            index={n}
            sourceType={c.sourceType}
            active={activeCitationId === c.id}
            onPress={() => onCitationPress?.(c, citations)}
          />
        );
      } else if (m[3]) {
        // **bold**
        parts.push(
          <Text key={key++} style={[baseStyle, styles.bold]}>
            {m[3]}
          </Text>
        );
      } else if (m[4]) {
        // *italic*
        parts.push(
          <Text key={key++} style={[baseStyle, styles.italic]}>
            {m[4]}
          </Text>
        );
      } else if (m[5]) {
        // `code`
        parts.push(
          <Text key={key++} style={styles.inlineCode}>
            {m[5]}
          </Text>
        );
      }

      last = tokenRegex.lastIndex;
    }

    if (last < text.length) {
      parts.push(
        <Text key={key++} style={baseStyle}>
          {text.slice(last)}
        </Text>
      );
    }

    return parts;
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // Skip blank lines (add small gap)
    if (!trimmed) {
      nodes.push(<View key={key++} style={styles.lineGap} />);
      i++;
      continue;
    }

    // ### H3 / ## H2 / # H1
    const headingMatch = trimmed.match(/^(#{1,3})\s+(.*)/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingStyle =
        level === 1 ? styles.h1 : level === 2 ? styles.h2 : styles.h3;
      nodes.push(
        <Text key={key++} style={headingStyle}>
          {headingMatch[2]}
        </Text>
      );
      i++;
      continue;
    }

    // Bullet: - or * or •
    const bulletMatch = trimmed.match(/^[-*•]\s+(.*)/);
    if (bulletMatch) {
      nodes.push(
        <View key={key++} style={styles.bulletRow}>
          <Text style={styles.bulletDot}>•</Text>
          <Text style={styles.bulletText}>
            {renderInline(bulletMatch[1], styles.assistantText)}
          </Text>
        </View>
      );
      i++;
      continue;
    }

    // Numbered list: 1. 2. etc.
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
    if (numberedMatch) {
      nodes.push(
        <View key={key++} style={styles.bulletRow}>
          <Text style={styles.numberedDot}>{numberedMatch[1]}.</Text>
          <Text style={styles.bulletText}>
            {renderInline(numberedMatch[2], styles.assistantText)}
          </Text>
        </View>
      );
      i++;
      continue;
    }

    // Code block (```)
    if (trimmed.startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      nodes.push(
        <View key={key++} style={styles.codeBlock}>
          <Text style={styles.codeText}>{codeLines.join('\n')}</Text>
        </View>
      );
      i++;
      continue;
    }

    // Blockquote or conflict note (> ...)
    if (trimmed.startsWith('>')) {
      nodes.push(
        <View key={key++} style={styles.quoteBlock}>
          <Text style={styles.quoteText}>
            {renderInline(trimmed.replace(/^>\s*/, ''), styles.quoteText)}
          </Text>
        </View>
      );
      i++;
      continue;
    }

    // Normal paragraph line
    nodes.push(
      <Text key={key++} style={styles.assistantText}>
        {renderInline(trimmed, styles.assistantText)}
      </Text>
    );
    i++;
  }

  return nodes;
}

export function ChatMessageItem({
  message,
  onCitationPress,
  activeCitationId,
}: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isInsufficient = message.isInsufficientInfo;

  // ── User bubble ──────────────────────────────────────────────────────────────
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

  // ── Insufficient info bubble ─────────────────────────────────────────────────
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

  // ── Assistant bubble ─────────────────────────────────────────────────────────
  return (
    <View style={styles.assistantRow}>
      <View style={styles.assistantBubble}>
        {/* Header: sender label + voice button */}
        <View style={styles.assistantHeader}>
          <View style={styles.senderContainer}>
            <View style={styles.assistantAccentDot} />
            <Text style={styles.assistantSender}>DocuMind AI</Text>
          </View>
          <VoiceoverButton text={message.content} />
        </View>

        {/* Rendered markdown body */}
        <View style={styles.contentBody}>
          {renderMarkdownContent(
            message.content,
            message.citations,
            activeCitationId,
            onCitationPress
          )}
        </View>

        {/* Multi-Source Evidence Badges Footer */}
        {message.citations && message.citations.length > 0 && (
          <View style={styles.citationsFooter}>
            <Text style={styles.sourcesLabel}>Evidence Sources:</Text>
            <View style={styles.badgesWrapper}>
              {message.citations.map((c) => {
                const isWeb = c.sourceType === 'web' || c.sourceType === 'search';
                const isLive = c.sourceType === 'live_api';

                const iconName = isLive
                  ? 'time-outline'
                  : isWeb
                  ? 'globe-outline'
                  : 'document-text-outline';

                const badgeColor = isLive
                  ? '#10B981'
                  : isWeb
                  ? '#38BDF8'
                  : Colors.primaryCyan;

                const badgeBg = isLive
                  ? 'rgba(16, 185, 129, 0.08)'
                  : isWeb
                  ? 'rgba(56, 189, 248, 0.08)'
                  : 'rgba(34, 211, 238, 0.08)';

                const badgeBorder = isLive
                  ? 'rgba(16, 185, 129, 0.3)'
                  : isWeb
                  ? 'rgba(56, 189, 248, 0.3)'
                  : 'rgba(34, 211, 238, 0.3)';

                const titleLabel =
                  decodeURIComponent(c.documentName || 'Source')
                    .replace(/\.[^/.]+$/, '')
                    .slice(0, 18) + (c.page > 1 ? ` (p.${c.page})` : '');

                return (
                  <Pressable
                    key={c.id}
                    onPress={() => onCitationPress?.(c, message.citations)}
                    style={({ pressed }) => [
                      styles.sourceBadge,
                      { backgroundColor: badgeBg, borderColor: badgeBorder },
                      activeCitationId === c.id && { borderColor: badgeColor, backgroundColor: 'rgba(255,255,255,0.1)' },
                      pressed && { opacity: 0.7 },
                    ]}
                  >
                    <Ionicons name={iconName as any} size={11} color={badgeColor} />
                    <Text style={[styles.sourceBadgeText, { color: badgeColor }]}>
                      [{c.index}] {titleLabel}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}

        <Text style={styles.timestampAssistant}>{message.timestamp}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // ── Layout ──────────────────────────────────────────────────────────────────
  userRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginVertical: 5,
    paddingLeft: 44,
  },
  assistantRow: {
    flexDirection: 'row',
    justifyContent: 'flex-start',
    marginVertical: 5,
    paddingRight: 16,
  },

  // ── User bubble ──────────────────────────────────────────────────────────────
  userBubble: {
    backgroundColor: Colors.surface,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    borderRadius: 16,
    borderBottomRightRadius: 4,
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

  // ── Assistant bubble ─────────────────────────────────────────────────────────
  assistantBubble: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    borderWidth: 1,
    borderColor: 'rgba(168,85,247,0.3)',
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    paddingHorizontal: 14,
    paddingTop: 10,
    paddingBottom: 10,
    maxWidth: '92%',
    shadowColor: Colors.secondaryPurple,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
  },
  assistantHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  senderContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
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
  contentBody: {
    gap: 2,
  },

  // ── Markdown elements ────────────────────────────────────────────────────────
  assistantText: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 22,
    color: Colors.textPrimary,
    flexWrap: 'wrap',
  },
  bold: {
    fontWeight: '700',
    color: '#e2d9f3',
  },
  italic: {
    fontStyle: 'italic',
    color: '#c4b5d4',
  },
  inlineCode: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    backgroundColor: 'rgba(168,85,247,0.15)',
    color: '#e879f9',
    paddingHorizontal: 4,
    paddingVertical: 1,
    borderRadius: 4,
  },
  h1: {
    fontFamily: Fonts.sans,
    fontSize: 17,
    fontWeight: '800',
    color: '#f3e8ff',
    marginTop: 10,
    marginBottom: 4,
    letterSpacing: 0.2,
  },
  h2: {
    fontFamily: Fonts.sans,
    fontSize: 15,
    fontWeight: '700',
    color: '#e9d5ff',
    marginTop: 8,
    marginBottom: 3,
  },
  h3: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    fontWeight: '700',
    color: '#ddd6fe',
    marginTop: 6,
    marginBottom: 2,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginVertical: 2,
    paddingLeft: 4,
  },
  bulletDot: {
    color: Colors.secondaryPurple,
    fontSize: 14,
    marginRight: 7,
    marginTop: 3,
    lineHeight: 20,
  },
  numberedDot: {
    fontFamily: Fonts.mono,
    color: Colors.secondaryPurple,
    fontSize: 13,
    marginRight: 7,
    marginTop: 3,
    lineHeight: 20,
    minWidth: 18,
  },
  bulletText: {
    fontFamily: Fonts.sans,
    fontSize: 14,
    lineHeight: 22,
    color: Colors.textPrimary,
    flex: 1,
    flexWrap: 'wrap',
  },
  codeBlock: {
    backgroundColor: 'rgba(0,0,0,0.35)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(168,85,247,0.2)',
    padding: 10,
    marginVertical: 6,
  },
  codeText: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    color: '#a5f3fc',
    lineHeight: 18,
  },
  quoteBlock: {
    backgroundColor: 'rgba(234, 179, 8, 0.08)',
    borderLeftWidth: 3,
    borderLeftColor: '#EAB308',
    paddingHorizontal: 8,
    paddingVertical: 6,
    borderRadius: 4,
    marginVertical: 4,
  },
  quoteText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    color: '#FDE047',
    lineHeight: 19,
  },
  lineGap: {
    height: 6,
  },

  // ── Multi-Source Citations Footer ────────────────────────────────────────────
  citationsFooter: {
    marginTop: 10,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.06)',
  },
  sourcesLabel: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textMuted,
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  badgesWrapper: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  sourceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 5,
    borderWidth: 1,
  },
  sourceBadgeText: {
    fontFamily: Fonts.mono,
    fontSize: 11,
    fontWeight: '600',
  },
  timestampAssistant: {
    fontFamily: Fonts.mono,
    fontSize: 10,
    color: Colors.textMuted,
    marginTop: 6,
  },

  // ── Insufficient info ────────────────────────────────────────────────────────
  insufficientBubble: {
    backgroundColor: Colors.warningBackground,
    borderWidth: 1,
    borderColor: Colors.warning,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
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
