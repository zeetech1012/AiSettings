---
name: svg-dashboard-generator
description: Генерация динамических и анимированных SVG-дашбордов, виджетов и тикеров из табличных баз данных или ответов API. Реализует CSS keyframe-прокрутку и совместимость с dark/light mode.
---
# SVG Dashboard & Widget Generator

## Objective
Convert flat database values or API data into visually interactive, self-contained SVG files optimized for embedding into README.md files and documentation.

## Workflow

When tasked with generating a visual dashboard, badge, or ticker in SVG format:

1. **Incorporate Tabular Data:** Parse data from source files (e.g., CSV databases, API status JSONs).
2. **Apply Styling Constraints:**
   - Use clean, premium-looking font stacks (e.g., Inter, Segoe UI, sans-serif).
   - Establish high-contrast harmonious palettes suitable for a dark/light mode context.
   - Implement media queries `@media (prefers-color-scheme: dark)` inside the SVG `<style>` tag to automatically swap fills, borders, and backgrounds based on the user's OS theme.
3. **Embed Dynamic Animations:**
   - Create CSS-based keyframe animations directly inside the SVG (e.g., horizontal scrolling `@keyframes scroll { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }`).
   - Use linear, infinite transitions for clean, hardware-accelerated movements (tickers, scanline overlays).
4. **Compile and Save SVG:** Use XML etrees or clean template string replacements to output standard, verified XML. Avoid any third-party script tags inside the SVG.

## Structure & Templates
- Horizontal Ticker: A self-scrolling viewport showing starred projects, daily deltas, and stats.
- TOC Button Grid: Static or animated SVG badges containing icons, categories, and responsive links.
