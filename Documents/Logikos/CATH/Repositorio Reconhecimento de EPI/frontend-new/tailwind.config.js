/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0A0C0F',
          secondary: '#111418',
          tertiary: '#181C23',
        },
        border: '#1E2530',
        accent: {
          blue: '#00A8FF',
          green: '#00D68F',
          amber: '#FFB800',
          red: '#FF3B30',
        },
        text: {
          primary: '#E8ECF0',
          secondary: '#6B7A8D',
          muted: '#3D4756',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
