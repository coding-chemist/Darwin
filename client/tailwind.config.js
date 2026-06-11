const path = require('path');
module.exports = {
  content: [
    path.resolve(__dirname, 'src/**/*.{js,jsx,ts,tsx}'),
    path.resolve(__dirname, 'public/index.html'),
  ],
  theme: {
    extend: {
      fontFamily: {
        sans:  ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono:  ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        darwin: {
          50:  '#ecfdf5',
          100: '#d1fae5',
          200: 'rgba(5,150,105,0.22)',
          300: 'rgba(5,150,105,0.30)',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        ink:  '#18181b',
        mid:  '#71717a',
      },
      letterSpacing: {
        tight2: '-0.04em',
        tight3: '-0.045em',
      },
      borderRadius: {
        '2xl': '20px',
      },
      backdropBlur: {
        '3xl': '48px',
      },
    },
  },
  plugins: [],
};