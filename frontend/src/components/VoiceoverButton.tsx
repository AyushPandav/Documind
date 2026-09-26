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
import * as Speech from 'expo-speech';
import { Colors } from '../constants/theme';
import { generateVoiceover } from '../services/api';

interface VoiceoverButtonProps {
  text: string;
}

export const VoiceoverButton: React.FC<VoiceoverButtonProps> = ({ text }) => {
  const [status, setStatus] = useState<'idle' | 'loading' | 'playing' | 'paused'>('idle');
  const webAudioRef = useRef<HTMLAudioElement | null>(null);
  const audioDataRef = useRef<string | null>(null);
  const summaryRef   = useRef<string | null>(null);

  const stopAll = useCallback(() => {
    if (Platform.OS === 'web' && webAudioRef.current) {
      webAudioRef.current.pause();
      webAudioRef.current = null;
    }
    if (Platform.OS !== 'web') {
      Speech.stop();
    }
    setStatus('idle');
  }, []);

  const handlePress = useCallback(async () => {
    // ── Stop / pause ─────────────────────────────────────────────────────────
    if (status === 'playing') {
      if (Platform.OS === 'web' && webAudioRef.current) {
        webAudioRef.current.pause();
        setStatus('paused');
        return;
      }
      Speech.pause?.();          // expo-speech pause (Android ≥ API 26)
      setStatus('paused');
      return;
    }

    if (status === 'paused') {
      if (Platform.OS === 'web' && webAudioRef.current) {
        webAudioRef.current.play();
        setStatus('playing');
        return;
      }
      Speech.resume?.();
      setStatus('playing');
      return;
    }

    // ── Fetch short summary from Kokoro backend ───────────────────────────────
    try {
      setStatus('loading');

      let shortSummary = summaryRef.current;
      let audioUri     = audioDataRef.current;

      if (!shortSummary || !audioUri) {
        const res = await generateVoiceover(text, 'af_heart', 1.05);
        if (!res) { setStatus('idle'); return; }
        shortSummary = res.short_summary || text.slice(0, 180);
        audioUri     = res.audio_base64  || null;
        summaryRef.current   = shortSummary;
        audioDataRef.current = audioUri;
      }

      // ── Web: play Kokoro WAV via window.Audio ──────────────────────────────
      if (Platform.OS === 'web' && typeof window !== 'undefined' && audioUri) {
        const audio = new window.Audio(audioUri);
        audio.onended = () => { webAudioRef.current = null; setStatus('idle'); };
        audio.onerror = () => { webAudioRef.current = null; setStatus('idle'); };
        webAudioRef.current = audio;
        await audio.play();
        setStatus('playing');
        return;
      }

      // ── Native (Expo Go): speak the short summary with device TTS ──────────
      // expo-speech uses Android/iOS built-in TTS — no native module issues.
      Speech.speak(shortSummary || text.slice(0, 180), {
        language: 'en-US',
        pitch: 1.0,
        rate: 0.95,
        onStart:  () => setStatus('playing'),
        onDone:   () => setStatus('idle'),
        onError:  () => setStatus('idle'),
        onStopped:() => setStatus('idle'),
      });
      setStatus('playing');
    } catch (err) {
      console.log('[Voiceover] error:', err);
      setStatus('idle');
    }
  }, [status, text, stopAll]);

  const label =
    status === 'loading' ? 'Generating...' :
    status === 'playing' ? 'Tap to Stop' :
    status === 'paused'  ? 'Resume' :
    'Voice Summary';

  const iconName: any =
    status === 'playing' ? 'stop-circle' :
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
        <Ionicons name={iconName} size={15} color={iconColor} style={styles.icon} />
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

      {status === 'playing' && (
        <View style={styles.liveIndicator}>
          <View style={[styles.waveBar, { height: 6 }]} />
          <View style={[styles.waveBar, { height: 11 }]} />
          <View style={[styles.waveBar, { height: 7 }]} />
          <View style={[styles.waveBar, { height: 4 }]} />
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
    paddingHorizontal: 9,
    paddingVertical: 4,
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
  icon:         { marginRight: 4 },
  label:        { fontSize: 11, fontWeight: '600', color: '#d8b4fe' },
  labelPlaying: { color: '#86efac' },
  labelPaused:  { color: '#67e8f9' },
  liveIndicator:{
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginLeft: 5,
  },
  waveBar: { width: 2.5, backgroundColor: '#22c55e', borderRadius: 2 },
});
