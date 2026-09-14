/**
 * Design system — Gestion Scolaire Premium SaaS
 * Inspiré Linear / Vercel / Stripe Dashboard
 *
 * Choix :
 * - Primaire pétrole (#0F766E) : crédible éducation UEMOA, distinctif sans purple générique.
 * - Neutres slate froids : fond aéré, hiérarchie claire.
 * - Plus Jakarta Sans : sans moderne à personnalité.
 * - Rayon 10px, ombres soft, transitions 180ms.
 * - Accents sémantiques uniquement (succès / alerte / danger).
 */
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#0F766E',
          hover: '#0D9488',
          muted: 'rgba(15, 118, 110, 0.10)',
          soft: 'rgba(15, 118, 110, 0.06)',
          foreground: '#F0FDFA',
        },
        encre: {
          DEFAULT: '#0F172A',
          clair: '#1E293B',
          profond: '#020617',
        },
        'or-cachet': {
          DEFAULT: '#0F766E',
          clair: 'rgba(15, 118, 110, 0.10)',
          doux: 'rgba(15, 118, 110, 0.06)',
        },
        craie: '#F8FAFC',
        blanc: '#FFFFFF',
        bordure: '#E2E8F0',
        'texte-secondaire': '#64748B',
        feuille: {
          DEFAULT: '#059669',
          clair: '#ECFDF5',
        },
        brique: {
          DEFAULT: '#E11D48',
          clair: '#FFF1F2',
        },
        ambre: {
          DEFAULT: '#D97706',
          clair: '#FFFBEB',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.04em' }],
      },
      borderRadius: {
        card: '10px',
        input: '8px',
        badge: '6px',
      },
      letterSpacing: {
        'table-header': '0.04em',
        label: '0.02em',
        tight: '-0.02em',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px -12px rgba(15, 23, 42, 0.08)',
        card: '0 1px 2px rgba(15, 23, 42, 0.04), 0 0 0 1px rgba(15, 23, 42, 0.03)',
        elevated: '0 4px 16px -4px rgba(15, 23, 42, 0.10), 0 0 0 1px rgba(15, 23, 42, 0.04)',
        glow: '0 0 0 3px rgba(15, 118, 110, 0.18)',
        focus: '0 0 0 3px rgba(15, 118, 110, 0.22)',
      },
      transitionDuration: {
        fast: '150ms',
        base: '180ms',
        slow: '250ms',
      },
      animation: {
        'fade-in': 'fade-in 0.35s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
