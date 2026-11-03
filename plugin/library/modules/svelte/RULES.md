---
module: svelte
capability: Svelte 5 runes and SvelteKit data loading
technologies: svelte
applies: svelte, sveltekit, runes, load, store
checked_against: Svelte 5 and SvelteKit 2 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## runes-derived: Derive values with $derived instead of $effect assignments
tags: svelte, runes, derived, effect, state, reactivity, svelte 5
keywords: $effect sets state, infinite loop
refs: https://svelte.dev/docs/svelte/$derived

In Svelte 5, compute values from state with `let total = $derived(items.reduce(...))`. Using `$effect` to assign another `$state` creates extra renders and can loop; reserve `$effect` for side effects such as DOM integrations, analytics or subscriptions, and return a cleanup function from it.

## sveltekit-load-server: Load private data in +page.server.ts and validate form actions
tags: svelte, sveltekit, load function, server, form actions, security, secrets
keywords: api key in +page.ts, universal load
refs: https://kit.svelte.dev/docs/load#universal-vs-server

`+page.ts` load functions run on both server and client, so anything they use ships to the browser. Put database access, secrets and authorization checks in `+page.server.ts`/`+layout.server.ts`, and validate inputs inside form actions; a form action is a public endpoint.

## sveltekit-parallel-loads: Avoid load waterfalls caused by await parent()
tags: svelte, sveltekit, load, parent, waterfall, performance, streaming
keywords: layout and page load sequentially
refs: https://kit.svelte.dev/docs/load#using-parent-data

Calling `await parent()` before your own fetches serializes layout and page loads. Start independent requests first and await `parent()` afterwards, or return promises un-awaited from server loads so SvelteKit streams them.

## keyed-each: Key each blocks with stable ids
tags: svelte, each block, keyed, list rendering, animation, state bugs
keywords: wrong item updated
refs: https://svelte.dev/docs/svelte/each#Keyed-each-blocks

Write `{#each items as item (item.id)}` so Svelte moves DOM nodes and component state with their items when the list changes; without a key, inputs and transitions attach to the wrong rows after inserts or deletes.

## props-bindable: Treat props as read-only unless declared $bindable
tags: svelte, props, bindable, two way binding, component api, runes
keywords: mutating prop warning
refs: https://svelte.dev/docs/svelte/$bindable

In Svelte 5, props are read from `$props()` and should not be mutated unless the prop is declared with `$bindable()` and the parent opts in with `bind:`. Otherwise communicate changes through callback props.

## ssr-safe-globals: Guard browser-only APIs during SSR
tags: svelte, sveltekit, ssr, window, browser, localstorage, hydration
keywords: window is not defined
refs: https://kit.svelte.dev/docs/state-management#avoid-shared-state-on-the-server

Code at the top of a component or in a load function runs on the server, where `window`, `document` and `localStorage` do not exist. Access them in `onMount`/`$effect` or behind `import { browser } from '$app/environment'`. Never store per-user data in module-level variables on the server: it is shared across requests.
