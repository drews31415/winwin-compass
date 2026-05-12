import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./app/**/*.{ts,tsx}",
    "./src/**/*.{ts,tsx}",
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      // ── 폰트 ─────────────────────────────────────────────────────────────
      fontFamily: {
        sans:    ["Pretendard", "system-ui", "sans-serif"],
        display: ['"Gmarket Sans"', "Pretendard", "system-ui"],
        mono:    ["var(--font-geist-mono)", "monospace"],
      },

      // ── 컬러 ─────────────────────────────────────────────────────────────
      colors: {
        // 브랜드 토큰
        golmok: {
          primary:      "#2D6A4F",
          "primary-light": "#52B788",
          "primary-dark":  "#1B4332",
          accent:       "#F4A261",
          "accent-light":  "#FFDDD2",
          surface:      "#F8F7F2",
          card:         "#FFFFFF",
          "text-main":  "#1A1A1A",
          "text-muted": "#6B7280",
          "risk-low":   "#52B788",
          "risk-mid":   "#F4A261",
          "risk-high":  "#E63946",
          // 하위 호환 alias
          secondary:    "#52B788",
          light:        "#B7E4C7",
          dark:         "#1B4332",
        },

        // shadcn/ui CSS 변수 토큰 (그대로 유지)
        border:      "hsl(var(--border))",
        input:       "hsl(var(--input))",
        ring:        "hsl(var(--ring))",
        background:  "hsl(var(--background))",
        foreground:  "hsl(var(--foreground))",
        primary: {
          DEFAULT:    "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT:    "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT:    "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT:    "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT:    "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT:    "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT:    "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },

      // ── 반경 ─────────────────────────────────────────────────────────────
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },

      // ── 키프레임 ─────────────────────────────────────────────────────────
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to:   { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to:   { height: "0" },
        },
        "bubble-in": {
          from: { opacity: "0", transform: "translateY(8px) scale(0.97)" },
          to:   { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        shimmer: {
          "0%":   { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },

      // ── 애니메이션 ────────────────────────────────────────────────────────
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "bubble-in":      "bubble-in 0.22s ease-out",
        "fade-in":        "fade-in 0.3s ease-out",
        shimmer:          "shimmer 1.6s infinite linear",
      },

      // ── 그림자 ────────────────────────────────────────────────────────────
      boxShadow: {
        card:   "0 1px 4px 0 rgba(0,0,0,0.06), 0 4px 16px 0 rgba(0,0,0,0.04)",
        "card-hover": "0 4px 12px 0 rgba(0,0,0,0.1), 0 12px 32px 0 rgba(0,0,0,0.06)",
        sidebar: "1px 0 0 0 #F3F4F6",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
