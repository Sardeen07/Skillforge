---
module: accessibility
capability: Web accessibility (WCAG 2.2) for components and pages
technologies:
applies: accessibility, a11y, screen reader, keyboard, aria, wcag, contrast
checked_against: WCAG 2.2 and WAI-ARIA Authoring Practices Guide
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## keyboard-operable: Make every interactive element reachable and usable by keyboard
tags: accessibility, a11y, keyboard, focus, tab order, tabindex, wcag
keywords: cannot tab to button, mouse only
refs: https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html

All functionality must work with Tab, Shift+Tab, Enter, Space and arrow keys where expected. Use native controls; if you must build a custom one, give it `tabindex="0"`, a role and key handlers. Never use positive `tabindex` values, and keep DOM order matching visual order.

## visible-focus: Never remove focus indicators without a visible replacement
tags: accessibility, a11y, focus visible, outline, keyboard, css, wcag
keywords: outline none, cannot see focus
refs: https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html

`outline: none` without a replacement makes keyboard navigation impossible. Style `:focus-visible` with a clear indicator (at least 2px, sufficient contrast against adjacent colors), and ensure focused elements are not hidden behind sticky headers (WCAG 2.2 Focus Not Obscured).

## accessible-names: Give every control and image an accessible name
tags: accessibility, a11y, alt text, aria-label, icon button, screen reader, labels
keywords: icon only button, missing alt
refs: https://www.w3.org/WAI/tutorials/images/decision-tree/

Informative images need `alt` describing their purpose; decorative ones `alt=""`. Icon-only buttons need visible text, visually hidden text or `aria-label`. Form fields need associated `<label>`s. Test with a screen reader or the browser's accessibility tree, not by eye.

## aria-first-rule: Prefer native HTML over ARIA, and never use ARIA to contradict semantics
tags: accessibility, a11y, aria, roles, semantic html, aria-hidden, widgets
keywords: role button on div, aria-hidden focusable
refs: https://www.w3.org/TR/using-aria/#rule1

No ARIA is better than bad ARIA. Use a native element when one exists. When building custom widgets (tabs, combobox, menu), follow the APG pattern completely, including keyboard behavior and states (`aria-expanded`, `aria-selected`). Never put `aria-hidden="true"` on focusable content.

## color-contrast: Meet contrast ratios and never convey meaning by color alone
tags: accessibility, a11y, contrast, color, wcag aa, error states, design
keywords: light gray text, red only for errors
refs: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html

Body text needs at least 4.5:1 contrast (3:1 for large text and for UI component boundaries and focus indicators). Pair color with text, icons or patterns for status, errors and chart series, so color-blind users and grayscale displays get the meaning.

## modal-focus-management: Trap and restore focus in dialogs
tags: accessibility, a11y, modal, dialog, focus trap, escape key, screen reader
keywords: focus behind modal, cannot close with escape
refs: https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/

When a modal opens, move focus into it, keep Tab within it, close on Escape, make the background inert, and return focus to the trigger on close. The native `<dialog>` element with `showModal()` provides most of this.

## announce-dynamic-content: Announce async updates with live regions
tags: accessibility, a11y, aria-live, live region, status messages, toast, form errors
keywords: screen reader not notified, toast not read
refs: https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html

Content that changes without a page load (toasts, "saved", result counts, validation summaries) is silent to screen readers unless it is in a live region: render a persistent container with `role="status"` (polite) or `role="alert"` (assertive) and change its text. Move focus to the error summary after a failed submit.

## form-errors-accessible: Associate error messages with fields and describe how to fix them
tags: accessibility, a11y, forms, validation, error message, aria-describedby, aria-invalid
keywords: red border only, error not read
refs: https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html

Identify errors in text next to the field, link them with `aria-describedby`, set `aria-invalid="true"`, and say how to fix the problem ("Use the format YYYY-MM-DD"). Do not clear the user's input on error.

## headings-and-landmarks: Structure pages with one h1, ordered headings and landmarks
tags: accessibility, a11y, headings, landmarks, skip link, navigation, screen reader
keywords: headings chosen for size
refs: https://www.w3.org/WAI/tutorials/page-structure/headings/

Screen reader users navigate by headings and landmarks. Use one `<h1>`, do not skip levels for styling (style with CSS instead), wrap regions in `<main>`, `<nav>`, `<header>`, `<footer>`, and add a "Skip to main content" link as the first focusable element.

## target-size-and-zoom: Provide adequate target sizes and support 200% zoom and reflow
tags: accessibility, a11y, target size, touch, zoom, reflow, mobile, wcag 2.2
keywords: tiny buttons, user-scalable=no
refs: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html

Interactive targets should be at least 24x24 CSS pixels (WCAG 2.2 AA; 44x44 is a common platform guideline). Never disable zoom (`user-scalable=no`), and make content reflow without horizontal scrolling at 320 CSS pixels wide.
