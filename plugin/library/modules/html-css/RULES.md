---
module: html-css
capability: Semantic HTML, layout and CSS maintainability
technologies: html-css
applies: html, css, layout, flexbox, grid, responsive, forms
checked_against: MDN Web Docs and WHATWG HTML Living Standard
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## semantic-elements: Use semantic elements instead of generic divs
tags: html-css, semantic html, button, nav, main, landmarks, div soup
keywords: div with onclick, clickable div
refs: https://developer.mozilla.org/en-US/docs/Glossary/Semantics#semantics_in_html

Use `<button>` for actions and `<a href>` for navigation, `<nav>`, `<main>`, `<header>`, `<footer>`, `<section>` with headings, and `<ul>/<ol>` for lists. A `<div onclick>` is not focusable, not announced as a button and ignores Enter/Space; native elements provide that behavior for free.

## form-labels-and-types: Label every input and use the right type and autocomplete
tags: html-css, forms, label, input type, autocomplete, validation, mobile keyboard
keywords: placeholder as label
refs: https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input

Associate each input with a `<label for>` (placeholders disappear and are not labels). Use `type="email"`, `tel`, `number`, `date` and `autocomplete="email"`/`"current-password"`/`"one-time-code"` so browsers show the right keyboard and autofill. Client-side validation attributes improve UX but never replace server validation.

## responsive-layout: Build layouts with flexbox and grid, sized with relative units
tags: html-css, responsive, flexbox, css grid, media queries, container queries, rem, layout
keywords: fixed pixel widths, horizontal scroll on mobile
refs: https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Responsive_Design

Use grid for two-dimensional page structure and flexbox for one-dimensional alignment; avoid floats and absolute positioning for layout. Size with `rem`, `%`, `fr`, `minmax()` and `clamp()`; add `<meta name="viewport" content="width=device-width, initial-scale=1">`; prefer container queries for components that must adapt to their slot.

## specificity-management: Keep selector specificity low and flat
tags: html-css, specificity, important, selectors, cascade layers, bem, maintainability
keywords: !important war, styles not applying
refs: https://developer.mozilla.org/en-US/docs/Web/CSS/Specificity

Style with single class selectors, avoid IDs and deep descendant chains, and do not use `!important` to win fights. Use `@layer` to order resets, base, components and utilities explicitly, and scope component styles (CSS modules, BEM naming or framework scoping).

## layout-shift-prevention: Reserve space for images, embeds and late content
tags: html-css, cls, layout shift, images, aspect ratio, width height, web vitals, fonts
keywords: page jumps while loading
refs: https://web.dev/articles/optimize-cls

Set `width` and `height` attributes (or CSS `aspect-ratio`) on images and video, reserve space for ads and embeds, avoid inserting content above existing content, and use `font-display: swap` with size-adjusted fallbacks to limit font-swap shifts.

## css-custom-properties: Use custom properties for design tokens and theming
tags: html-css, css variables, custom properties, theming, dark mode, design tokens
keywords: hardcoded colors everywhere
refs: https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties

Define colors, spacing and typography as custom properties on `:root` and reference them with `var(--color-text)`. Switch themes by redefining them under `@media (prefers-color-scheme: dark)` or a `[data-theme]` attribute instead of duplicating rule sets.

## animation-performance-css: Animate transform and opacity, and respect reduced motion
tags: html-css, animation, transition, transform, opacity, prefers-reduced-motion, jank
keywords: animating width, layout thrashing
refs: https://web.dev/articles/animations-guide

Animating `width`, `height`, `top` or `left` triggers layout every frame. Animate `transform` and `opacity`, which the compositor can handle. Wrap non-essential motion in `@media (prefers-reduced-motion: no-preference)`.

## stacking-context: Understand stacking contexts before raising z-index
tags: html-css, z-index, stacking context, positioning, overlay, modal
keywords: z-index 9999 not working
refs: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_positioned_layout/Understanding_z-index/Stacking_context

`z-index` only competes within the same stacking context; properties such as `transform`, `opacity < 1`, `filter` and `position: fixed` create new ones. Render modals and popovers at the document root (a portal, `<dialog>` with `showModal()`, or the Popover API's top layer) instead of escalating z-index values.
