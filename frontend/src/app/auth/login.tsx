import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useApp } from '@/context/AppContext';
import { Colors, Fonts } from '@/constants/theme';
import { DocuMindLogo } from '@/components/DocuMindLogo';
import { PrimaryButton } from '@/components/PrimaryButton';
import { GlassCard } from '@/components/GlassCard';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useApp();

  const [email, setEmail] = useState('engineer@documind.ai');
  const [password, setPassword] = useState('password123');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [loading, setLoading] = useState(false);

  const validate = () => {
    let isValid = true;

    // Email check
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email.trim()) {
      setEmailError('Email address is required.');
      isValid = false;
    } else if (!emailRegex.test(email.trim())) {
      setEmailError('Email address is invalid.');
      isValid = false;
    } else {
      setEmailError('');
    }

    // Password check
    if (!password) {
      setPasswordError('Password is required.');
      isValid = false;
    } else if (password.length < 6) {
      setPasswordError('Password must be at least 6 characters.');
      isValid = false;
    } else {
      setPasswordError('');
    }

    return isValid;
  };

  const handleLogin = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      await login(email);
      router.replace('/app');
    } catch {
      setEmailError('Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardAvoid}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.innerContainer}>
            {/* Header branding */}
            <DocuMindLogo size="large" />

            {/* Auth Form Card */}
            <GlassCard style={styles.card}>
              <View style={styles.fieldGroup}>
                <Text style={styles.label}>Email</Text>
                <TextInput
                  style={[styles.input, !!emailError && styles.inputError]}
                  placeholder="name@company.com"
                  placeholderTextColor={Colors.textMuted}
                  value={email}
                  onChangeText={(val) => {
                    setEmail(val);
                    if (emailError) setEmailError('');
                  }}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  autoComplete="email"
                />
                {!!emailError && (
                  <Text style={styles.errorText}>{emailError}</Text>
                )}
              </View>

              <View style={styles.fieldGroup}>
                <View style={styles.passwordLabelRow}>
                  <Text style={styles.label}>Password</Text>
                  <Text style={styles.forgotPassword}>Forgot password?</Text>
                </View>
                <TextInput
                  style={[styles.input, !!passwordError && styles.inputError]}
                  placeholder="••••••••"
                  placeholderTextColor={Colors.textMuted}
                  value={password}
                  onChangeText={(val) => {
                    setPassword(val);
                    if (passwordError) setPasswordError('');
                  }}
                  secureTextEntry
                />
                {!!passwordError && (
                  <Text style={styles.errorText}>{passwordError}</Text>
                )}
              </View>

              <PrimaryButton
                title="Log In"
                onPress={handleLogin}
                loading={loading}
                style={styles.submitButton}
              />

              <View style={styles.switchAuthRow}>
                <Text style={styles.switchPromptText}>
                  Don't have an account?{' '}
                </Text>
                <Pressable
                  onPress={() => router.push('/auth/signup')}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                >
                  <Text style={styles.switchLinkText}>Sign up</Text>
                </Pressable>
              </View>
            </GlassCard>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  keyboardAvoid: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 20,
    paddingVertical: 24,
  },
  innerContainer: {
    maxWidth: 420,
    width: '100%',
    alignSelf: 'center',
  },
  card: {
    padding: 24,
    gap: 18,
    marginTop: 12,
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderColor: 'rgba(34, 211, 238, 0.2)',
  },
  fieldGroup: {
    gap: 6,
  },
  label: {
    fontFamily: Fonts.mono,
    fontSize: 12,
    color: Colors.textSecondary,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  passwordLabelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  forgotPassword: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.textMuted,
    opacity: 0.6,
  },
  input: {
    height: 46,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    paddingHorizontal: 14,
    fontFamily: Fonts.sans,
    fontSize: 14,
    color: Colors.textPrimary,
  },
  inputError: {
    borderColor: Colors.error,
    backgroundColor: 'rgba(239, 68, 68, 0.05)',
  },
  errorText: {
    fontFamily: Fonts.sans,
    fontSize: 11,
    color: Colors.error,
    marginTop: 2,
  },
  submitButton: {
    marginTop: 8,
  },
  switchAuthRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 8,
  },
  switchPromptText: {
    fontFamily: Fonts.sans,
    fontSize: 13,
    color: Colors.textMuted,
  },
  switchLinkText: {
    fontFamily: Fonts.mono,
    fontSize: 13,
    fontWeight: '700',
    color: Colors.primaryCyan,
  },
});
