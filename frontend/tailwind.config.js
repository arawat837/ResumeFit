/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#F0F9FF',   // Background
          100: '#E0F2FE',  // Light accents / borders
          200: '#BAE6FD',
          400: '#38BDF8',  // Primary sky blue
          500: '#0EA5E9',
          600: '#0284C7',  // Primary dark (buttons/hover)
          700: '#0369A1',
          900: '#0F172A',  // Slate text
        },
        slate: {
          900: '#0F172A',  // Slate text
          700: '#334155',
          600: '#475569',
          400: '#94A3B8',
          200: '#E2E8F0',
          100: '#F1F5F9',
          50: '#F8FAFC',
        },
        score: {
          high: '#22C55E', // Green
          mid: '#F59E0B',  // Amber
          low: '#EF4444',   // Red
        }
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      boxShadow: {
        'soft': '0 4px 20px -2px rgba(2, 132, 199, 0.08), 0 2px 6px -1px rgba(15, 23, 42, 0.04)',
        'card': '0 8px 30px -4px rgba(2, 132, 199, 0.07)',
        'glass': '0 8px 32px 0 rgba(2, 132, 199, 0.12)',
      }
    },
  },
  plugins: [],
}
