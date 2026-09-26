import React, { useState, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants/theme';
import { generateVoiceover } from '../services/api';

interface VoiceoverButtonProps {
  text: string;
}

export const VoiceoverButton: React.FC<VoiceoverButtonProps> = ({ text }) => {
  const [status, setStatus] = useState<'idle' | 'loading' | 'playing' | 'paused'>('idle');
  const webAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioDataRef = useRef<string | null>(null);

  const handlePress = useCallback(async () => {
    // ── Web: full audio playback via window.Audio ──────────────────────────
    if (Platform.OS === 'web' && typeof window !== 'undefined') {
      if (status === 'playing' && webAudioRef.current) {
        webAudioRef.current.pause();
        setStatus('paused');
        return;
      }
      if (status === 'paused' && webAudioRef.current) {
        webAudioRef.current.play();
        setStatus('playing');
        return;
      }

      try {
        setStatus('loading');
        if (!audioDataRef.current) {
          const res = await generateVoiceover(text, 'af_heart', 1.05);
          if (!res?.audio_base64) { setStatus('idle'); return; }
          audioDataRef.current = res.audio_base64;
        }

        const audio = new window.Audio(audioDataRef.current);
        audio.onended = () => { setStatus('idle'); webAudioRef.current = null; };
        audio.onerror = () => { setStatus('idle'); webAudioRef.current = null; };
        webAudioRef.current = audio;
        await audio.play();
        setStatus('playing');
      } catch {
        setStatus('idle');
      }
      return;
    }

    // ── Native (Expo Go): fetch transcript only — no expo-av needed ────────
    if (status === 'loading' || status === 'playing') return;

    try {
      setStatus('loading');
      // Just call backend to get the short summary; no audio playback on native
      if (!audioDataRef.current) {
        const res = await generateVoiceover(text, 'af_heart', 1.05);
        // Store summary text in audioDataRef for the label display
        audioDataRef.current = res?.short_summary || text.slice(0, 120);
      }
      // Flash "playing" briefly so user knows it processed
      setStatus('playing');
      setTimeout(() => setStatus('idle'), 2000);
    } catch {
      setStatus('idle');
    }
  }, [status, text]);

  const label =
    status === 'loading' ? 'Kokoro Voice...' :
    status === 'playing' ? (Platform.OS === 'web' ? 'Pause Voice' : 'Summarized ✓') :
    status === 'paused'  ? 'Resume' :
    'Voice Summary';

  const iconName =
    status === 'playing' ? (Platform.OS === 'web' ? 'pause-circle' : 'checkmark-circle') :
    status === 'paused'  ? 'play-circle' :
    'volume-medium-outline';

  const iconColor =
    status === 'playing' ? '#22c55e' :
    status === 'paused'  ? '#06b6d4' :
    '#a855f7';

  return (
    <TouchableOpacity
      activeOpacity={0.75}
      style={[
        styles.container,
        status === 'playing' && styles.containerPlaying,
        status === 'loading' && styles.containerLoading,
      ]}
      onPress={handlePress}
    >
      {status === 'loading' ? (
        <ActivityIndicator size="small" color={Colors.primary} style={styles.icon} />
      ) : (
        <Ionicons name={iconName as any} size={15} color={iconColor} style={styles.icon} />
      )}

      <Text
        style={[
          styles.label,
          status === 'playing' && styles.labelPlaying,
          status === 'paused'  && styles.labelPaused,
        ]}
      >
        {label}
      </Text>

      {status === 'playing' && Platform.OS === 'web' && (
        <View style={styles.liveIndicator}>
          <View style={[styles.waveBar, { height: 7 }]} />
          <View style={[styles.waveBar, { height: 11 }]} />
          <View style={[styles.waveBar, { height: 5 }]} />
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(168, 85, 247, 0.12)',
    paddingHorizontal: 8,
    paddingVertical: 3.5,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(168, 85, 247, 0.3)',
    marginLeft: 'auto',
  },
  containerPlaying: {
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
    borderColor: 'rgba(34, 197, 94, 0.45)',
  },
  containerLoading: {
    backgroundColor: 'rgba(168, 85, 247, 0.08)',
    borderColor: 'rgba(168, 85, 247, 0.2)',
  },
  icon: { marginRight: 4 },
  label: { fontSize: 11, fontWeight: '600', color: '#d8b4fe' },
  labelPlaying: { color: '#86efac' },
  labelPaused:  { color: '#67e8f9' },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 1.5,
    marginLeft: 5,
  },
  waveBar: { width: 2, backgroundColor: '#22c55e', borderRadius: 1 },
});
