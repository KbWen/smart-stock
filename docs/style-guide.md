# Sniper Design System & Style Guide

A high-performance, dark-themed design system optimized for data density and expert-level decision-making.

## 1. Foundation: The 8-Pixel Grid

All spacing, sizing, and alignment must follow an 8px (0.5rem) baseline to ensure visual mathematical harmony.

- **Baseline**: 8px
- **Padding/Margins**: 8px (xs), 16px (sm), 32px (md), 48px (lg), 64px (xl)
- **Border Radius**: 4px (tight), 8px (default), 12px (rounded), 999px (pill)

## 2. Typography

Using **Inter** (or System Sans) for UI and **JetBrains Mono** for data.

| Level | Size | Weight | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **H1 (Display)** | 32px / 2rem | 800 | 1.2 | Page Titles |
| **H2 (Heading)** | 24px / 1.5rem | 700 | 1.3 | Section Headers |
| **H3 (Subhead)** | 18px / 1.125rem | 600 | 1.4 | Card Titles |
| **Body (Default)** | 14px / 0.875rem | 400 | 1.5 | General UI Text |
| **Small/Muted** | 12px / 0.75rem | 400 | 1.6 | Tooltips, Metadata |
| **Data Mono** | 14px / 0.875rem | 500 | 1.0 | Prices, Tickers |

## 3. Color Palette (Semantic Tokens)

| Token | HEX | Usage |
| :--- | :--- | :--- |
| **Background** | `#0B0F1A` | Main page background |
| **Surface (Card)** | `#151B2B` | Standard card background |
| **Border** | `#262F42` | Default component borders |
| **Sniper Green** | `#10B981` | Positive action / Strong Buy |
| **Sniper Gold** | `#F59E0B` | Secondary highlights / AI Prob |
| **Sniper Flame** | `#EF4444` | High risk / Sell signals |
| **Muted Text** | `#6B7280` | Secondary information |

## 4. Component Layouts

### The Dashboard Skeleton

- **Container Max-Width**: 1440px (Centered)
- **Main Gap**: 32px (2rem) between major sections.
- **Inner Gap**: 16px (1rem) inside cards.

### Premium Card Effect

- **Background**: `bg-surface/80` with `backdrop-blur-md`
- **Border**: 1px solid `border-white/5`
- **Shadow**: Suburban, deep shadows `shadow-[0_20px_50px_rgba(0,0,0,0.3)]`

## 5. Responsive Breakpoints

- **Mobile (Default)**: Single column, 16px margin.
- **Tablet (768px+)**: 2-column or stacked grid.
- **Desktop (1280px+)**: Multi-column layout with fixed sidebar (280px).
