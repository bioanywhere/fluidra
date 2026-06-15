import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Tier-aware palette (see §7.3). Values chosen for ≥4.5:1 text contrast.
        tier: {
          escalation: "#C2410C", // coral-700 border/accent for Tier-3
          dosing: "#1D4ED8",     // blue-700 accent for Tier-2 cards
        },
      },
    },
  },
  plugins: [],
};

export default config;
