/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0a0a0a',
        surface: '#171717',
        border: '#262626',
        primary: '#0070f3',
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f5a623',
        muted: '#a1a1aa'
      }
    },
  },
  plugins: [],
}
