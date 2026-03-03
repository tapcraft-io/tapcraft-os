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
        primary: '#ee8c2b',
        'background-dark': '#111111',
        'surface-dark': '#18181b',
        'surface-light': '#27272a',
        'border-dark': '#3f3f46',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'monospace']
      },
    }
  },
  plugins: []
};
