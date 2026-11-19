---
module: tailwind
capability: Tailwind CSS configuration and maintainable utilities
technologies: tailwind
applies: tailwind, utility classes, classnames, design tokens
checked_against: Tailwind CSS v4 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## no-dynamic-class-names: Never build Tailwind class names by string concatenation
tags: tailwind, dynamic classes, purge, content detection, missing styles, class names
keywords: bg-${color}-500 not working
refs: https://tailwindcss.com/docs/detecting-classes-in-source-files#dynamic-class-names

Tailwind generates CSS only for complete class names it finds in source files, so `` `bg-${color}-500` `` produces no styles. Map values to full class strings (`const colors = { red: 'bg-red-500', blue: 'bg-blue-500' }`) or use inline style/CSS variables for truly dynamic values.

## merge-conflicting-classes: Merge conditional classes with clsx and tailwind-merge
tags: tailwind, clsx, tailwind-merge, cn, conditional classes, overrides, components
keywords: className override ignored, p-2 p-4 both applied
refs: https://github.com/dcastil/tailwind-merge

When a component accepts a `className` override, both `p-2` and `p-4` end up in the class list and the winner depends on CSS order, not on which you passed last. Combine with a `cn()` helper (`twMerge(clsx(...))`) so later conflicting utilities replace earlier ones.

## design-tokens-in-theme: Define tokens in the theme instead of arbitrary values
tags: tailwind, theme, design tokens, arbitrary values, colors, spacing, consistency
keywords: text-[#3a3a3a] everywhere
refs: https://tailwindcss.com/docs/theme

Repeated arbitrary values (`text-[#1e293b]`, `mt-[13px]`) drift from the design system. Add brand colors, fonts and spacing to the theme (`@theme { --color-brand: ... }` in v4, `theme.extend` in v3) and use semantic names; keep arbitrary values for genuine one-offs.

## extract-components-not-apply: Reuse markup through components, not @apply everywhere
tags: tailwind, apply, components, duplication, maintainability, css
keywords: long repeated class lists
refs: https://tailwindcss.com/docs/styling-with-utility-classes#managing-duplication

When the same long class list repeats, extract a component (React/Vue/Svelte) or template partial. Heavy `@apply` recreates the cascade and specificity problems utilities avoid; reserve it for third-party markup you cannot change.

## responsive-and-state-variants: Write mobile-first with responsive and state variants
tags: tailwind, responsive, breakpoints, mobile first, dark mode, hover, focus visible
keywords: md: styles not applying on mobile
refs: https://tailwindcss.com/docs/responsive-design

Unprefixed utilities apply to all sizes; `md:`/`lg:` apply from that breakpoint up. Style the mobile layout first and add larger-screen overrides. Use `focus-visible:` for keyboard focus rings (never remove outlines without a replacement) and `dark:` with a consistent dark-mode strategy.

## content-paths-coverage: Point Tailwind at every file that contains class names
tags: tailwind, content configuration, source detection, missing styles, production build, purge
keywords: styles work in dev but not in production, classes from a package missing
refs: https://tailwindcss.com/docs/detecting-classes-in-source-files

Tailwind scans source files for class names; classes used only in files it does not scan (a component library in node_modules, templates in another folder, markdown content) are missing from the build. Register extra sources (`@source "../node_modules/@acme/ui"` in v4, the `content` array in v3) instead of safelisting individual classes.

## accessible-utilities: Keep focus, contrast and motion accessible with utilities
tags: tailwind, accessibility, focus visible, sr only, motion reduce, contrast, outline none
keywords: outline-none removed focus ring
refs: https://tailwindcss.com/docs/hover-focus-and-other-states#focus-visible

Do not ship `outline-none` without a `focus-visible:ring-*` replacement, use `sr-only` for text that screen readers need, wrap animations with `motion-safe:`/`motion-reduce:`, and check that text and background color pairs meet contrast ratios (gray-400 on white does not).

## arbitrary-variants-sparingly: Prefer theme variables over arbitrary values in components
tags: tailwind, arbitrary values, css variables, theming, dark mode, maintainability
keywords: bg-[var(--x)], hardcoded hex in classes
refs: https://tailwindcss.com/docs/adding-custom-styles#using-arbitrary-values

Arbitrary values (`w-[317px]`, `bg-[#123456]`) bypass the design system and do not respond to themes. Expose shared values as theme variables (`@theme` in v4) and reference them by name; reserve arbitrary values for genuine one-offs and document why.
