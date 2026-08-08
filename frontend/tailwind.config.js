/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        encre: {
          DEFAULT: '#14213D',
          clair: '#1F3A5F',
        },
        'or-cachet': {
          DEFAULT: '#B8862E',
          clair: 'rgba(184,134,46,0.12)',
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
        input: '6px',
        badge: '4px',
      },
      letterSpacing: {
        'table-header': '0.03em',
      },
    },
  },
  plugins: [],
};
