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
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
