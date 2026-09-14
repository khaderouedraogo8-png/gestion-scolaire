/**
 * Design system v2 — Gestion Scolaire Premium (réf. Metric Flow / Wise / Zence)
 *
 * Choix :
 * - Accent unique pétrole (#0F766E) : crédible éducation, pas de jaune/rose Dribbble.
 * - Rayon 16px cards : respiration type dashboards 2025.
 * - Surfaces élevées (blanc / anthracite) + ombre soft, pas de bordures lourdes.
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
          muted: 'rgba(15, 118, 110, 0.12)',
          soft: 'rgba(15, 118, 110, 0.06)',
          foreground: '#F0FDFA',
        },
        encre: {
          DEFAULT: '#0B1220',
          clair: '#151D2E',
          profond: '#070B14',
        },
        'or-cachet': {
          DEFAULT: '#0F766E',
          clair: 'rgba(15, 118, 110, 0.12)',
          doux: 'rgba(15, 118, 110, 0.06)',
        },
        craie: '#F4F6F9',
        blanc: '#FFFFFF',
        bordure: '#E6EAF0',
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
        kpi: ['1.875rem', { lineHeight: '1.1', letterSpacing: '-0.03em', fontWeight: '650' }],
      },
      borderRadius: {
        card: '16px',
        input: '10px',
        badge: '9999px',
        shell: '20px',
      },
      letterSpacing: {
        'table-header': '0.05em',
        label: '0.02em',
        tight: '-0.025em',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(11, 18, 32, 0.04), 0 12px 32px -16px rgba(11, 18, 32, 0.12)',
        card: '0 1px 2px rgba(11, 18, 32, 0.03), 0 0 0 1px rgba(11, 18, 32, 0.04)',
        elevated: '0 8px 28px -12px rgba(11, 18, 32, 0.14), 0 0 0 1px rgba(11, 18, 32, 0.04)',
        glow: '0 0 0 3px rgba(15, 118, 110,.18)',
        focus: '0 0 0 3px rgba(15, 118, 110, 0.22)',
      },
      spacing: {
        section: '2.5rem',
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
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
