/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './index.html',
    './src/**/*.{ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        holo: {
          blue: '#4fd1ff',
          amber: '#ffb347',
          violet: '#9f7aea'
        },
        deck: {
          base: '#05070f',
          panel: '#0f1424',
          accent: '#1f2b4d'
        }
      },
      fontFamily: {
        sans: ['"SF Pro Display"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular']
      },
      boxShadow: {
        glow: '0 0 15px rgba(79, 209, 255, 0.4)',
        ember: '0 0 12px rgba(255, 179, 71, 0.45)'
      },
      animation: {
        flicker: 'flicker 3s infinite',
        pulseSlow: 'pulseSlow 4s ease-in-out infinite'
      },
      keyframes: {
        flicker: {
          '0%, 19%, 21%, 23%, 25%, 54%, 56%, 100%': { opacity: 1 },
          '20%, 24%, 55%': { opacity: 0.6 },
          '22%': { opacity: 0.3 }
        },
        pulseSlow: {
          '0%, 100%': { opacity: 0.9 },
          '50%': { opacity: 0.6 }
        }
      }
    }
  },
  plugins: []
};
