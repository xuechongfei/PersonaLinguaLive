/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Warm storybook palette — replaces indigo/slate defaults
        cream: '#FFF8F0',
        sand: '#F5E6D3',
        honey: '#D97706',
        'honey-light': '#FDE68A',
        'honey-dark': '#92400E',
        ink: '#1E1B18',
        'ink-light': '#5C5148',
        teal: '#0D9488',
        'teal-light': '#CCFBF1',
        rose: '#E11D48',
        'rose-light': '#FFE4E6',
        moss: '#4D7C0F',
        'moss-light': '#ECFCCB',
        sky: '#0369A1',
        'sky-light': '#E0F2FE',
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.75rem',
      },
      boxShadow: {
        'soft': '0 2px 16px rgba(30, 27, 24, 0.06)',
        'card': '0 4px 24px rgba(30, 27, 24, 0.08)',
        'glow': '0 0 20px rgba(217, 119, 6, 0.15)',
        'glow-teal': '0 0 20px rgba(13, 148, 136, 0.12)',
      },
      animation: {
        'float': 'float 3s ease-in-out infinite',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'pop-in': 'popIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        popIn: {
          '0%': { transform: 'scale(0.9)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(12px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
