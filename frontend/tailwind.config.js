/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0e14",
          900: "#0f151d",
          800: "#161e29",
          700: "#202b3a",
          600: "#2c3a4d",
          500: "#425065",
        },
        amber: {
          400: "#ffb84d",
          500: "#ff9e2c",
        },
        cyan: {
          300: "#7fe3e8",
          400: "#4fd1d9",
        },
        rose: {
          400: "#ff6b6b",
        },
      },
      fontFamily: {
        mono: ["'IBM Plex Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["'IBM Plex Sans'", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
}
