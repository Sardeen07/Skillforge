---
module: web-performance
capability: Core Web Vitals and front-end loading performance
technologies:
applies: web vitals, lcp, inp, cls, bundle, lighthouse, page load
checked_against: web.dev Core Web Vitals guidance (2025)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## measure-field-data: Measure Core Web Vitals from real users before optimizing
tags: web performance, core web vitals, lcp, inp, cls, rum, lighthouse, measurement
keywords: lighthouse score fine but users complain
refs: https://web.dev/articles/vitals

Lab tools (Lighthouse, DevTools) diagnose; field data decides. Collect LCP, INP and CLS from real users (the `web-vitals` library, CrUX, or your RUM tool) segmented by page and device, and target the 75th percentile: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1.

## optimize-lcp-resource: Make the LCP element discoverable and prioritized
tags: web performance, lcp, largest contentful paint, hero image, preload, fetchpriority, lazy loading
keywords: hero image loads late
refs: https://web.dev/articles/optimize-lcp

The LCP image should be in the initial HTML (not injected by JavaScript or set as a CSS background), not `loading="lazy"`, and marked `fetchpriority="high"`. Serve it compressed in a modern format at the right size, from the same origin or a preconnected CDN.

## reduce-inp: Keep event handlers short and yield to the main thread
tags: web performance, inp, interaction to next paint, long tasks, main thread, event handler, responsiveness
keywords: click feels laggy, ui freezes on input
refs: https://web.dev/articles/optimize-inp

Interactions are slow when long JavaScript tasks block the main thread. Do the visible update first, then defer non-urgent work (`await scheduler.yield()` where supported, or `setTimeout`), break long loops into chunks, move heavy computation to a Web Worker, and avoid forcing layout in handlers.

## code-splitting: Ship less JavaScript: split by route and load on interaction
tags: web performance, bundle size, code splitting, dynamic import, tree shaking, javascript
keywords: huge bundle, slow time to interactive
refs: https://web.dev/articles/reduce-javascript-payloads-with-code-splitting

Split bundles by route, `import()` heavy features (editors, charts, maps) when first needed, remove unused dependencies, and check bundle composition with an analyzer. Every kilobyte of JavaScript costs parse and execution time on slow phones, not only download.

## image-optimization: Serve responsive, modern-format images with explicit dimensions
tags: web performance, images, webp, avif, srcset, sizes, lazy loading, cls
keywords: 4MB image, images slow
refs: https://web.dev/learn/images

Serve AVIF/WebP with fallbacks, provide `srcset` and `sizes` so phones do not download desktop images, lazy-load below-the-fold images with `loading="lazy"`, and always set `width`/`height` to prevent layout shift.

## caching-headers: Cache static assets immutably and revalidate HTML
tags: web performance, caching, cache-control, cdn, etag, immutable, http caching
keywords: users get old js, assets downloaded every visit
refs: https://web.dev/articles/http-cache

Give fingerprinted assets (`app.3f9a2c.js`) `Cache-Control: public, max-age=31536000, immutable`, and HTML `no-cache` (revalidate with ETag) so deploys take effect immediately. Serve through a CDN with compression (Brotli or gzip).

## third-party-scripts: Load third-party scripts late and isolate their cost
tags: web performance, third party scripts, analytics, tag manager, async, defer, main thread
keywords: chat widget slows page
refs: https://web.dev/articles/optimizing-content-efficiency-loading-third-party-javascript

Audit every third-party tag. Load non-critical ones with `async`/`defer` or after user interaction/idle, self-host where licensing allows, `preconnect` to origins you must use early, and consider running analytics off the main thread.

## avoid-layout-thrashing: Batch DOM reads before writes
tags: web performance, layout thrashing, forced reflow, dom, offsetHeight, requestAnimationFrame
keywords: forced synchronous layout warning
refs: https://web.dev/articles/avoid-large-complex-layouts-and-layout-thrashing

Reading layout (`offsetHeight`, `getBoundingClientRect`) after writing styles forces a synchronous layout; doing it in a loop forces one per iteration. Read all measurements first, then write, ideally inside `requestAnimationFrame`; use `ResizeObserver`/`IntersectionObserver` instead of polling layout.
