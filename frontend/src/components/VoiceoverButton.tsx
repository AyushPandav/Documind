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
  const [status, setStatus] = useState<'idle' | 'loading' | 'playing'>('idle');
  const webAudioRef  = useRef<HTMLAudioElement | null>(null);
  const audioDataRef = useRef<string | null>(null);
  const summaryRef   = useRef<string | null>(null);

  // Stop any active playback
  const stopPlayback = useCallback(() => {
    if (Platform.OS === 'web' && webAudioRef.current) {
      webAudioRef.current.pause();
      webAudioRef.current.currentTime = 0;
      webAudioRef.current = null;
    } else {
      try { Speech.stop(); } catch (_) {}
    }
    setStatus('idle');
  }, []);

  const handlePress = useCallback(async () => {
    // Tap while playing → stop
    if (status === 'playing') {
      stopPlayback();
      return;
    }

    try {
      setStatus('loading');

      // Fetch short summary + audio from Kokoro backend (cached after first call)
      if (!summaryRef.current || !audioDataRef.current) {
        const res = await generateVoiceover(text, 'af_heart', 1.05);
        if (!res) { setStatus('idle'); return; }
        summaryRef.current   = res.short_summary || text.slice(0, 180);
        audioDataRef.current = res.audio_base64 || null;
      }

      // ── Web: play Kokoro WAV via window.Audio ────────────────────────────
      if (Platform.OS === 'web' && typeof window !== 'undefined' && audioDataRef.current) {
        const audio = new window.Audio(audioDataRef.current);
        audio.onended = () => { webAudioRef.current = null; setStatus('idle'); };
        audio.onerror = () => { webAudioRef.current = null; setStatus('idle'); };
        webAudioRef.current = audio;
        await audio.play();
        setStatus('playing');
        return;
      }

      // ── Native (Expo Go): speak via Android/iOS device TTS ───────────────
      // expo-speech works in Expo Go without any native build.
      // Note: Speech.pause/resume are NOT available on Android — we only use speak/stop.
      const summary = summaryRef.current || text.slice(0, 180);
      Speech.speak(summary, {
        language: 'en-US',
        pitch: 1.0,
        rate:  0.92,
        onStart:  () => setStatus('playing'),
        onDone:   () => setStatus('idle'),
        onStopped:() => setStatus('idle'),
        onError:  () => setStatus('idle'),
      });
      setStatus('playing');
    } catch (err) {
      console.log('[Voiceover] error:', err);
      setStatus('idle');
    }
  }, [status, text, stopPlayback]);

  const iconName: any =
    status === 'playing' ? 'stop-circle' : 'volume-medium-outline';

  const iconColor = status === 'playing' ? '#22c55e' : '#a855f7';

  const label =
    status === 'loading' ? 'Generating...' :
    status === 'playing' ? 'Stop Voice' :
    'Voice Summary';

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

      <Text style={[styles.label, status === 'playing' && styles.labelPlaying]}>
        {label}
      </Text>

      {status === 'playing' && (
        <View style={styles.waveWrap}>
          <View style={[styles.waveBar, { height: 5  }]} />
          <View style={[styles.waveBar, { height: 10 }]} />
          <View style={[styles.waveBar, { height: 7  }]} />
          <View style={[styles.waveBar, { height: 4  }]} />
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(168,85,247,0.12)',
    paddingHorizontal: 9,
    paddingVertical: 4,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: 'rgba(168,85,247,0.3)',
    marginLeft: 'auto',
  },
  containerPlaying: {
    backgroundColor: 'rgba(34,197,94,0.15)',
    borderColor: 'rgba(34,197,94,0.45)',
  },
  containerLoading: {
    backgroundColor: 'rgba(168,85,247,0.08)',
    borderColor: 'rgba(168,85,247,0.2)',
  },
  icon:         { marginRight: 4 },
  label:        { fontSize: 11, fontWeight: '600', color: '#d8b4fe' },
  labelPlaying: { color: '#86efac' },
  waveWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    marginLeft: 5,
  },
  waveBar: { width: 2.5, backgroundColor: '#22c55e', borderRadius: 2 },
});
