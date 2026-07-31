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
        primary: '#AB334C',  // Ягаан өнгө
        secondary: '#222631',
        light: '#f8f9fa',
      },
    },
  },
  plugins: [],
}
