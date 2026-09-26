import { Platform } from 'react-native';

export const Colors = {
  background: '#0A0A0F',
  surface: '#12121A',
  surfaceElevated: '#181826',
  surfaceCard: 'rgba(255, 255, 255, 0.03)',
  surfaceHighlight: 'rgba(34, 211, 238, 0.06)',
  
  primary: '#22D3EE', // Cyan
  primaryCyan: '#22D3EE',
  primaryGlow: 'rgba(34, 211, 238, 0.15)',
  
  secondary: '#A855F7', // Purple
  secondaryPurple: '#A855F7',
  purpleGlow: 'rgba(168, 85, 247, 0.15)',
  
  textPrimary: '#E5E5E5',
  textMuted: '#8B8B95',
  textSecondary: '#A3A3AF',
  
  borderSubtle: 'rgba(255, 255, 255, 0.08)',
  borderCyan: 'rgba(34, 211, 238, 0.25)',
  borderPurple: 'rgba(168, 85, 247, 0.25)',
  
  error: '#EF4444',
  errorBackground: 'rgba(239, 68, 68, 0.1)',
  warning: '#F59E0B',
  warningBackground: 'rgba(245, 158, 11, 0.08)',
  success: '#22D3EE',
  
  // Status Colors
  statusQueued: '#8B8B95',
  statusOcr: '#A855F7',
  statusProcessing: '#22D3EE',
  statusIndexed: '#22D3EE',
} as const;

export const Fonts = {
  mono: Platform.select({
    ios: 'Menlo',
    android: 'monospace',
    web: 'monospace',
    default: 'monospace',
  }),
  sans: Platform.select({
    ios: 'System',
    android: 'Roboto',
    web: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    default: 'System',
  }),
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const BorderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  full: 9999,
};
