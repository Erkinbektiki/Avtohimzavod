module.exports = {
  content: ["./templates/**/*.html", "./core/**/*.html"],
  theme: { extend: {} },
  plugins: [require('@tailwindcss/line-clamp'), require('@tailwindcss/aspect-ratio')]

}
