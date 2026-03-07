import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        nonna: {
          cream: "#FFF8F0",
          warm: "#F5E6D3",
          gold: "#D4A574",
          brown: "#8B6F47",
          dark: "#4A3728",
          accent: "#C17817",
          sage: "#A8B5A0",
          rose: "#D4A0A0",
        },
      },
      fontFamily: {
        serif: ["Georgia", "Cambria", "serif"],
        sans: ["system-ui", "-apple-system", "sans-serif"],
      },
      fontSize: {
        elder: ["1.5rem", { lineHeight: "2rem" }],
        "elder-lg": ["2rem", { lineHeight: "2.5rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
