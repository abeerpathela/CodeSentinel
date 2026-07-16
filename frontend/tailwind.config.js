/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#050505",
          panel: "#0c0c0c",
          border: "#1f1f1f",
          accent: "#00ff41",
          safe: "#00ff41",
          threat: "#ff4b2b",
          highlight: "#ff4b2b",
          danger: "#ff4b2b",
          warn: "#ff4b2b",
          text: "#ffffff",
          muted: "#8a8a8a",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Roboto Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 28px rgba(0, 255, 65, 0.1)",
        "glow-threat": "0 0 28px rgba(255, 75, 43, 0.14)",
      },
    },
  },
  plugins: [],
};
