/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './main/templates/**/*.html',
    './main/**/*.py',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#b5245b',  // Ягаан өнгө
        secondary: '#222631',
        light: '#f8f9fa',
      },
    },
  },
  plugins: [],
}
