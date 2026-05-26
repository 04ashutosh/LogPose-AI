/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        card: '#151D30',
        primary: '#6366F1',     // Indigo navigation accent
        secondary: '#10B981',   // Emerald approval accent
        accent: '#EC4899',      // Pink state pulse
        muted: '#94A3B8',
        border: '#1E293B'
      }
    },
  },
  plugins: [],
}