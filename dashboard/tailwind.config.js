import colors from "tailwindcss/colors";
import formsPlugin from "@tailwindcss/forms";
import tailwindcssAnimate from "tailwindcss-animate";

/** Terracotta scale anchored at Baseline CTA #c8553a */
const terracotta = {
  50: "#fdf5f3",
  100: "#faeae6",
  200: "#f5d5cc",
  300: "#e8a090",
  400: "#d4705a",
  500: "#c8553a",
  600: "#c8553a",
  700: "#a8432e",
  800: "#873525",
  900: "#6b2a1e",
  950: "#451a13",
};

/** Success scale anchored at Baseline #6b8f5c */
const baselineGreen = {
  50: "#f4f7f2",
  100: "#e6ede2",
  200: "#cddbc5",
  300: "#adc39f",
  400: "#8da97c",
  500: "#6b8f5c",
  600: "#6b8f5c",
  700: "#557348",
  800: "#445c3a",
  900: "#384a31",
  950: "#1c2618",
};

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@tremor/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    transparent: "transparent",
    current: "currentColor",
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        surface: {
          sunken: "hsl(var(--surface-sunken))",
          raised: "hsl(var(--surface-raised))",
        },
        terracotta: {
          DEFAULT: "#c8553a",
          muted: "#e8a090",
          subtle: "#d4705a",
        },
        /* Chart palettes — Baseline-aligned overrides */
        orange: terracotta,
        emerald: baselineGreen,
        tremor: {
          brand: {
            faint: terracotta[50],
            muted: terracotta[200],
            subtle: terracotta[400],
            DEFAULT: terracotta[600],
            emphasis: terracotta[700],
            inverted: colors.white,
          },
          background: {
            muted: "#f2efe9",
            subtle: "#faf8f5",
            DEFAULT: colors.white,
            emphasis: colors.gray[700],
          },
          border: { DEFAULT: colors.gray[200] },
          ring: { DEFAULT: colors.gray[200] },
          content: {
            subtle: colors.gray[400],
            DEFAULT: colors.gray[500],
            emphasis: colors.gray[700],
            strong: colors.gray[900],
            inverted: colors.white,
          },
        },
        "dark-tremor": {
          brand: {
            faint: "#2a1814",
            muted: terracotta[900],
            subtle: terracotta[700],
            DEFAULT: terracotta[500],
            emphasis: terracotta[400],
            inverted: "#141413",
          },
          background: {
            muted: "#141413",
            subtle: "#1e1d1b",
            DEFAULT: "#1e1d1b",
            emphasis: colors.gray[300],
          },
          border: { DEFAULT: "#2a2926" },
          ring: { DEFAULT: "#2a2926" },
          content: {
            subtle: colors.gray[600],
            DEFAULT: colors.gray[500],
            emphasis: colors.gray[200],
            strong: colors.gray[50],
            inverted: "#141413",
          },
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
        "baseline-sm": "4px",
        "baseline-md": "8px",
        "baseline-lg": "12px",
        "baseline-xl": "16px",
        "tremor-small": "0.375rem",
        "tremor-default": "0.5rem",
        "tremor-full": "9999px",
      },
      spacing: {
        "baseline-1": "4px",
        "baseline-2": "8px",
        "baseline-3": "12px",
        "baseline-4": "16px",
        "baseline-6": "24px",
        "baseline-8": "32px",
        "baseline-12": "48px",
        "baseline-16": "64px",
      },
      boxShadow: {
        "tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "tremor-card": "0 0 0 1px rgb(0 0 0 / 0.04)",
        "tremor-dropdown":
          "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        "dark-tremor-input": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        "dark-tremor-card": "0 0 0 1px rgb(255 255 255 / 0.06)",
        "dark-tremor-dropdown":
          "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
      },
      fontFamily: {
        sans: ['"DM Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ['"DM Serif Display"', "Georgia", "serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      fontSize: {
        "baseline-xs": ["11px", { lineHeight: "16px" }],
        "baseline-sm": ["13px", { lineHeight: "20px" }],
        "baseline-base": ["16px", { lineHeight: "24px" }],
        "baseline-lg": ["18px", { lineHeight: "28px" }],
        "baseline-xl": ["20px", { lineHeight: "28px" }],
        "baseline-2xl": ["25px", { lineHeight: "32px" }],
        "baseline-3xl": ["31px", { lineHeight: "36px" }],
        "baseline-4xl": ["39px", { lineHeight: "44px" }],
        "tremor-label": ["0.75rem", { lineHeight: "1rem" }],
        "tremor-default": ["0.875rem", { lineHeight: "1.25rem" }],
        "tremor-title": ["1.125rem", { lineHeight: "1.75rem" }],
        "tremor-metric": ["1.875rem", { lineHeight: "2.25rem" }],
      },
      transitionTimingFunction: {
        "ease-out-studio": "cubic-bezier(0.16, 1, 0.3, 1)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
      },
      animation: {
        "fade-up": "fade-up 400ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  safelist: [
    {
      pattern:
        /^(bg-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
      variants: ["hover", "data-[selected]"],
    },
    {
      pattern:
        /^(text-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
      variants: ["hover", "data-[selected]"],
    },
    {
      pattern:
        /^(border-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
      variants: ["hover", "data-[selected]"],
    },
    {
      pattern:
        /^(ring-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
    },
    {
      pattern:
        /^(stroke-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
    },
    {
      pattern:
        /^(fill-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-(?:50|100|200|300|400|500|600|700|800|900|950))$/,
    },
  ],
  plugins: [formsPlugin, tailwindcssAnimate],
};
