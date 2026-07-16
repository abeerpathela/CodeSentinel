/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#020202",
          panel: "#0a0a0a",
          border: "#1a1a1a",
          accent: "#10b981",
          highlight: "#f97316",
          danger: "#ef4444",
          warn: "#f97316",
          safe: "#10b981",
          text: "#e2e8f0",
          muted: "#6b7280",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(16, 185, 129, 0.12)",
        "glow-orange": "0 0 24px rgba(249, 115, 22, 0.15)",
        "glow-red": "0 0 24px rgba(239, 68, 68, 0.18)",
      },
    },
  },
  plugins: [],
};
