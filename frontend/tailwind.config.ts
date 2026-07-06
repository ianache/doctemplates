import type { Config } from "tailwindcss";

// Precision Archival design system tokens — canonical source: .design/DESIGN.md
// (NOT the .design/*.html mockups' embedded Tailwind config, which is outdated per 01-UI-SPEC.md)
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#fff8f6",
        "surface-container-lowest": "#ffffff",
        "surface-container": "#ffe9e6",
        primary: "#610000",
        error: "#ba1a1a",
        "on-surface": "#261816",
        "on-surface-variant": "#5a403c",
        secondary: "#5e5e5e",
        outline: "#8e706b",
        "outline-variant": "#e3beb8",
      },
      fontFamily: {
        headings: ["'Hanken Grotesk'", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      spacing: {
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "48px",
        "3xl": "64px",
      },
      borderRadius: {
        sm: "0.125rem",
        DEFAULT: "0.25rem",
        md: "0.375rem",
        lg: "0.5rem",
        xl: "0.75rem",
        full: "9999px",
      },
    },
  },
  plugins: [],
} satisfies Config;
