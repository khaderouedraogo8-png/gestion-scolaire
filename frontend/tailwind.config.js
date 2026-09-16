/** @type {import('tailwindcss').Config} */
/**
 * Design system — Gestion Scolaire (SaaS institutionnel)
 * Tokens FR conservés pour compatibilité ; valeurs = identité premium cool.
 */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        /* Primary — encre (navy institutionnel) */
        encre: {
          DEFAULT: '#0B1F33',
          clair: '#163A56',
          profond: '#061525',
        },
        /* Accent — or-cachet (teal institutionnel, pas or) */
        'or-cachet': {
          DEFAULT: '#0E7490',
          clair: 'rgba(14, 116, 144, 0.10)',
          doux: 'rgba(14, 116, 144, 0.05)',
        },
        /* Surfaces */
        craie: '#F4F6F9',
        blanc: '#FFFFFF',
        bordure: '#E2E8F0',
        'texte-secondaire': '#64748B',
        /* Semantics */
        feuille: {
          DEFAULT: '#047857',
          clair: '#ECFDF5',
        },
        brique: {
          DEFAULT: '#B91C1C',
          clair: '#FEF2F2',
        },
        ambre: {
          DEFAULT: '#B45309',
          clair: '#FFFBEB',
        },
        info: '#0369A1',
      },
      fontFamily: {
        sans: ['"Figtree"', 'system-ui', 'sans-serif'],
        display: ['"Outfit"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        card: '10px',
        input: '8px',
        badge: '6px',
      },
      letterSpacing: {
        'table-header': '0.04em',
        label: '0.05em',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(11, 31, 51, 0.04), 0 4px 12px rgba(11, 31, 51, 0.03)',
        card: '0 1px 2px rgba(11, 31, 51, 0.04)',
        elevated: '0 4px 24px rgba(11, 31, 51, 0.06)',
        glow: '0 0 0 3px rgba(14, 116, 144, 0.15)',
      },
      animation: {
        'fade-in': 'fade-in 0.28s ease-out',
        'slide-up': 'slide-up 0.32s ease-out',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};
