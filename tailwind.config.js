/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["app/**/templates/**/*.html"],
  darkMode: 'selector',
  theme: {
    extend: {
      fontFamily: {
        'sans': ['Outfit', '"Inter var"', 'Inter', 'sans-serif'],
        'mono': ['"Fira Mono"', '"JetBrains Mono"', 'monospace'],
      },
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            pre: null,
            code: null,
            'code::before': null,
            'code::after': null,
            'pre code': null,
            'pre code::before': null,
            'pre code::after': null
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
