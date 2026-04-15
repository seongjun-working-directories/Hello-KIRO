import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['KBFGDisplay', 'sans-serif'],
        sans: ['KBFGText', 'sans-serif'],
      },
      colors: {
        kb: {
          yellow: '#FFB800',
          'yellow-dark': '#E6A600',
          'yellow-light': '#FFF3CC',
          navy: '#1A1A2E',
          'navy-mid': '#2D2D44',
          'navy-light': '#3D3D5C',
          gray: '#F5F5F5',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
