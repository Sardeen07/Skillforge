---
module: nextjs
capability: Next.js App Router data, caching and security
technologies: nextjs
applies: nextjs, next, app router, server actions, middleware, vercel
checked_against: Next.js 15 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## server-components-default: Keep components on the server; add "use client" only at interactive leaves
tags: nextjs, server components, use client, bundle size, client components, app router
keywords: whole page is client component, large js bundle
refs: https://nextjs.org/docs/app/building-your-application/rendering/composition-patterns

In the App Router components are Server Components by default and ship no JavaScript. Mark only the interactive leaf (a button, a form) with `"use client"`, not a whole page or layout: everything it imports becomes client code. Pass server-rendered content into client components as `children` props.

## server-actions-authorize: Authenticate and authorize inside every Server Action
tags: nextjs, server actions, authorization, authentication, security, use server, mutation
keywords: action callable directly, hidden button not protection
refs: https://nextjs.org/docs/app/building-your-application/authentication#authorization

A Server Action is a public POST endpoint: anyone can call it with any arguments, even if your UI hides the button. Inside each action, verify the session, check that the user may act on the specific resource, and validate arguments with a schema before touching data.

## fetch-caching-explicit: State caching intent explicitly for each data fetch
tags: nextjs, caching, fetch, revalidate, dynamic, stale data, isr, cache
keywords: page shows stale data, data never updates
refs: https://nextjs.org/docs/app/building-your-application/caching

Next.js caching defaults changed between versions (in 15, `fetch` and GET route handlers are not cached by default). Declare intent per request: `fetch(url, { cache: 'force-cache' })` or `{ next: { revalidate: 60, tags: ['products'] } }` for cacheable data, `cache: 'no-store'` for per-user data, and call `revalidateTag`/`revalidatePath` after mutations.

## no-secrets-in-client: Keep secrets out of NEXT_PUBLIC_ variables and client components
tags: nextjs, environment variables, secrets, next_public, security, api key, server only
keywords: api key in browser bundle
refs: https://nextjs.org/docs/app/building-your-application/configuring/environment-variables#bundling-environment-variables-for-the-browser

Variables prefixed `NEXT_PUBLIC_` are inlined into the browser bundle. Read secrets only in server code, and put `import 'server-only'` at the top of modules that use them so an accidental client import fails the build.

## parallel-data-loading: Start independent fetches in parallel in Server Components
tags: nextjs, data fetching, waterfall, promise all, server components, suspense, streaming
keywords: sequential awaits in page, slow ttfb
refs: https://nextjs.org/docs/app/building-your-application/data-fetching/fetching#parallel-and-sequential-data-fetching

Sequential `await`s in a page create a waterfall. Initiate independent requests together (`Promise.all`) or split slow sections into their own async components wrapped in `<Suspense>`, so the shell streams immediately and each section renders when ready.

## image-and-font-optimization: Use next/image and next/font
tags: nextjs, next image, next font, lcp, cls, images, fonts, web vitals
keywords: layout shift, large images, font flash
refs: https://nextjs.org/docs/app/building-your-application/optimizing/images

`next/image` serves resized, modern-format images with lazy loading and reserved dimensions (no layout shift); set `priority` on the LCP image and `sizes` for responsive images. `next/font` self-hosts fonts with no layout shift and no request to Google at runtime.

## route-handler-validation: Validate input and return proper status codes in Route Handlers
tags: nextjs, route handlers, api routes, validation, status codes, zod, rest
keywords: 500 on bad input, request.json throws
refs: https://nextjs.org/docs/app/building-your-application/routing/route-handlers

Parse `await request.json()` inside `try` and validate with a schema; return `NextResponse.json({ error }, { status: 400 })` for invalid input, 401/403 for auth failures and 404 for missing resources, rather than letting exceptions become 500s.

## middleware-lightweight: Keep middleware fast and do not rely on it as the only auth check
tags: nextjs, middleware, edge, authentication, performance, redirects, security
keywords: middleware bypass, slow every request
refs: https://nextjs.org/docs/app/building-your-application/routing/middleware

Middleware runs on every matched request, so keep it to cheap checks (cookie presence, redirects, headers) and narrow it with `matcher`. Do not treat it as the only authorization layer: re-check authorization in the server code that reads or writes data (a 2025 advisory allowed middleware to be bypassed via a crafted header).

## loading-and-error-boundaries: Add loading.tsx and error.tsx per route segment
tags: nextjs, loading, error boundary, error tsx, not found, suspense, ux
keywords: blank page while loading, whole app crashes
refs: https://nextjs.org/docs/app/building-your-application/routing/error-handling

`loading.tsx` gives a segment an instant streaming fallback, `error.tsx` (a client component) isolates failures to that segment with a retry, and `not-found.tsx` with `notFound()` returns a real 404. Without them a slow or failing child blocks or breaks the whole layout.

## generate-metadata-and-static-params: Pre-render known dynamic routes and generate metadata on the server
tags: nextjs, generatestaticparams, metadata, seo, static generation, dynamic routes
keywords: every product page rendered on request
refs: https://nextjs.org/docs/app/api-reference/functions/generate-static-params

Use `generateStaticParams` to pre-render dynamic routes whose parameters are known at build time, and `generateMetadata` for per-page titles and Open Graph data. Fetches in both are deduplicated with the page's fetches in the same render.
