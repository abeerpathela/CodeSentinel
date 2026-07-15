/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#0a0e17",
          panel: "#111827",
          border: "#1e293b",
          accent: "#06b6d4",
          danger: "#ef4444",
          warn: "#f59e0b",
          safe: "#22c55e",
          text: "#e2e8f0",
          muted: "#64748b",
        },
      },
      fontFamily: {
        sans: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(6, 182, 212, 0.15)",
        "glow-red": "0 0 20px rgba(239, 68, 68, 0.2)",
      },
    },
  },
  plugins: [],
};
