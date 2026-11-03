---
module: vue
capability: Vue 3 reactivity, components and performance
technologies: vue
applies: vue, nuxt, pinia, composition api, reactivity
checked_against: Vue 3.5 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## reactivity-destructuring: Do not destructure reactive objects; use toRefs
tags: vue, reactivity, reactive, ref, toRefs, destructuring, composition api
keywords: value stopped updating, lost reactivity
refs: https://vuejs.org/guide/essentials/reactivity-fundamentals.html#limitations-of-reactive

Destructuring a `reactive()` object (or a Pinia store) copies plain values and disconnects them from reactivity. Use `toRefs(state)` or `storeToRefs(store)`, or prefer `ref()` for state you pass around. Remember `.value` in script; templates unwrap refs automatically.

## computed-over-watch: Derive state with computed, not watch plus a copy
tags: vue, computed, watch, derived state, reactivity, side effects
keywords: watcher sets another ref, state out of sync
refs: https://vuejs.org/guide/essentials/computed.html

If a value can be calculated from other state, make it `computed`: it is cached and always consistent. Use `watch`/`watchEffect` only for side effects (fetching, logging, syncing to storage), and never mutate state inside a computed getter.

## v-for-keys: Give v-for items stable unique keys and never combine v-if on the same element
tags: vue, v-for, key, v-if, list rendering, performance, state bugs
keywords: index as key, input values jump
refs: https://vuejs.org/guide/essentials/list.html#maintaining-state-with-key

Use a stable id (`:key="item.id"`), not the index, so component state and DOM stay attached to the right item when the list reorders. `v-if` takes precedence over `v-for` on the same element in Vue 3; filter with a computed list or wrap in `<template>`.

## props-down-events-up: Never mutate props; emit events or use v-model
tags: vue, props, emit, v-model, one way data flow, component communication
keywords: avoid mutating a prop directly warning
refs: https://vuejs.org/guide/components/props.html#one-way-data-flow

Props flow down and are read-only in the child. To change a value, emit an event the parent handles, or use `defineModel()` (3.4+) for two-way binding. For deep object props, copy into local state if the child needs an editable draft.

## pinia-for-shared-state: Use Pinia for state shared across distant components
tags: vue, pinia, state management, store, provide inject, global state
keywords: prop drilling, event bus
refs: https://pinia.vuejs.org/core-concepts/

For state used by many unrelated components, define a Pinia store (setup stores read like composables). Keep component-local state local; use `provide/inject` for subtree configuration. In SSR (Nuxt), never keep request data in module-level variables; it leaks between users.

## lazy-components-and-routes: Lazy-load routes and heavy components
tags: vue, lazy loading, defineAsyncComponent, router, code splitting, bundle size
keywords: large initial bundle
refs: https://router.vuejs.org/guide/advanced/lazy-loading.html

Use dynamic imports for routes (`component: () => import('./views/Admin.vue')`) and `defineAsyncComponent` for heavy, rarely shown components (charts, editors), so they load only when needed.

## large-lists-shallow: Use shallowRef and virtualization for large data
tags: vue, shallowRef, shallowReactive, large list, virtual scroll, performance, markRaw
keywords: thousands of rows slow, deep reactivity overhead
refs: https://vuejs.org/guide/best-practices/performance.html#reduce-reactivity-overhead-for-large-immutable-structures

Deep reactivity proxies every nested property. For large immutable datasets use `shallowRef` (replace the whole value to update) or `markRaw` for non-reactive objects such as chart instances, and render long lists with a virtual scroller.

## cleanup-in-unmounted: Clean up listeners and timers in onUnmounted
tags: vue, lifecycle, onUnmounted, memory leak, event listener, interval, cleanup
keywords: handler fires after leaving page
refs: https://vuejs.org/api/composition-api-lifecycle.html#onunmounted

Global listeners, intervals and third-party instances created in `onMounted` must be released in `onUnmounted` (or via `watch`'s `onCleanup`/`onWatcherCleanup`), or they keep running and leak after the component is gone.
