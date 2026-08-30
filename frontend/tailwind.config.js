/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        encre: {
          DEFAULT: '#14213D',
          clair: '#1F3A5F',
          profond: '#0D1628',
        },
        'or-cachet': {
          DEFAULT: '#B8862E',
          clair: 'rgba(184,134,46,0.12)',
          doux: 'rgba(184,134,46,0.06)',
        },
        craie: '#F6F5F1',
        blanc: '#FFFFFF',
        bordure: '#E4E2D9',
        'texte-secondaire': '#6B6D6A',
        feuille: {
          DEFAULT: '#2F6E4F',
          clair: '#E7F0EA',
        },
        brique: {
          DEFAULT: '#A6432E',
          clair: '#F5E8E4',
        },
        ambre: {
          DEFAULT: '#B8862E',
          clair: '#F7EEDD',
        },
      },
      fontFamily: {
        sans: ['"Public Sans"', 'system-ui', 'sans-serif'],
        display: ['Fraunces', 'Georgia', 'serif'],
      },
      borderRadius: {
        card: '8px',
        input: '8px',
        badge: '6px',
      },
      letterSpacing: {
        'table-header': '0.03em',
        label: '0.06em',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(20, 33, 61, 0.04), 0 4px 16px rgba(20, 33, 61, 0.03)',
        card: '0 1px 0 rgba(255,255,255,0.9) inset, 0 1px 2px rgba(20,33,61,0.05)',
        glow: '0 0 0 1px rgba(184,134,46,0.15)',
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out',
        'slide-up': 'slide-up 0.45s ease-out',
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
