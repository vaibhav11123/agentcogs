# AgentCOGS Dashboard — Baseline v1.0 Design System

This dashboard follows **Baseline Labs v1.0** (Warm Studio). Source reference: [Baseline example API](https://api.baselinelabs.ai/admin/example).

## Stack

- Vite + React 18 + TypeScript
- Tailwind CSS + shadcn-style primitives
- Tremor charts
- **Phosphor Icons** (`@phosphor-icons/react`) — single icon library
- Motion via `motion/react` + CSS tokens

## Color tokens

| Token | Hex | Usage |
|-------|-----|-------|
| Background | `#faf8f5` | Page canvas |
| Foreground | `#1a1714` | Body text |
| Primary (CTA) | `#c8553a` | Terracotta — buttons, active nav, charts |
| Info | `#5a8fb4` | Informational accents |
| Success | `#6b8f5c` | Healthy margins, positive states |
| Warning | `#e09430` | Budget warnings, anomalies |
| Surface sunken | `#f2efe9` | Table headers, secondary fills |
| Surface raised | `#ffffff` | Cards, panels |

CSS variables live in `src/index.css`. Tailwind maps them via `hsl(var(--token))`.

### Dark mode (optional)

Applied via `.dark` or `[data-theme="dark"]`:

| Token | Hex |
|-------|-----|
| Background | `#141413` |
| Raised | `#1e1d1b` |

Never use pure `#000000`.

## Typography

| Scale | Size | Font |
|-------|------|------|
| xs | 11px | DM Sans |
| sm | 13px | DM Sans |
| base | 16px | DM Sans |
| lg | 18px | DM Sans |
| xl | 20px | DM Sans |
| 2xl | 25px | DM Serif Display (headings) |
| 3xl | 31px | DM Serif Display |
| 4xl | 39px | DM Serif Display |

Monospace / metrics: **JetBrains Mono** with `tabular-nums`.

Tailwind classes: `text-baseline-xs` … `text-baseline-4xl`.

## Spacing & radii

8px grid: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 (`baseline-1` … `baseline-16`).

Radii: 4 / 8 / 12 / 16 / pill — `rounded-baseline-sm` … `rounded-baseline-xl`. Max card radius is 16px.

## Icons (Phosphor)

- **Default weight:** `regular` (via `IconProvider`)
- **Active nav:** `fill` (via `NavIcon`)
- **Small inline emphasis:** `bold` (alerts, anomaly cards)
- **Hero / logo:** `fill` at 28px

```tsx
import { ChartLineUp } from "@phosphor-icons/react";
<ChartLineUp size={16} weight="fill" aria-hidden />
```

## Motion

| Token | Value |
|-------|-------|
| Easing | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Fast | 120ms — hovers, presses |
| Normal | 200ms — toggles |
| Slow | 400ms — page enter, toasts, stagger |

- Page content: staggered fade-up (`FadeUpStagger` / `FadeUpItem`)
- KPI numbers: ease-out counter (`NumberTicker`) — **no springs**
- Charts: 600ms animation on **first paint only** (`useFirstChartAnimation`)
- Toasts: slide from right, 400ms
- `prefers-reduced-motion`: all animations collapse to instant

## Elevation

Cards use **border + raised white**, not heavy drop shadows. Tremor cards use `ring-1 ring-border`.

## Charts (Tremor)

- Primary series: terracotta (`colors={["orange"]}` — orange scale overridden to `#c8553a`)
- Secondary / revenue: baseline green (`emerald` scale → `#6b8f5c`)
- No indigo or purple in `dark-tremor` brand palette

## DON'Ts

- No Lucide, Remix Icon, or Heroicons
- No Inter, Roboto, or system-only stacks for marketing UI
- No indigo / purple accent colors
- No `amber-*` / raw Tailwind semantic colors — use `warning` / `success` tokens
- No ShineBorder, glassmorphism, or neon gradients
- No bouncy spring animations on KPIs or layout
- No `rounded-2xl` or radii above 16px on cards
- No pure black backgrounds in dark mode

## Verification checklist

```bash
# No Lucide in source
rg "lucide-react" dashboard/src

# No banned Tailwind color classes in app code
rg "indigo-|purple-|amber-|emerald-" dashboard/src

# Build
cd dashboard && npm run build
```

Visual smoke test: `/demo` → `/` → `/alerts` → customer detail → Live mode toasts.
