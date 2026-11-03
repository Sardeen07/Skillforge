---
module: frontend-architecture
capability: Front-end state management and component architecture
technologies:
applies: state management, components, server state, forms, design system
checked_against: React documentation (react.dev), TanStack Query documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## classify-state: Separate server state, URL state and UI state
tags: state management, server state, url state, global state, redux, react query, cache
keywords: everything in redux, stale server data in store
refs: https://tanstack.com/query/latest/docs/framework/react/overview

Most "global state" is a cache of server data. Manage it with a server-state library (TanStack Query, SWR, RTK Query, Apollo) that handles caching, deduplication and invalidation; keep filters, tabs and pagination in the URL so they survive reloads and sharing; and keep only genuinely client-only UI state in component state or a small store.

## single-source-of-truth: Do not duplicate state; derive it
tags: state management, derived state, duplication, synchronization, single source of truth, useEffect
keywords: two copies out of sync, sync effect
refs: https://react.dev/learn/choosing-the-state-structure#avoid-redundant-state

Storing a value that can be computed from props or other state (a filtered list, a full name, a total) creates two sources that drift apart. Compute it during render (memoize only if measurably expensive), and store IDs rather than copies of selected objects.

## colocate-state: Keep state as close as possible to where it is used
tags: state management, colocation, lifting state, prop drilling, context, rerender
keywords: whole app rerenders on keystroke
refs: https://react.dev/learn/sharing-state-between-components

Put state in the lowest component that needs it, lift it only to the closest common parent, and pass components as `children` instead of threading props through layers. Global context that changes often re-renders every consumer; split contexts by update frequency.

## container-presentational-split: Keep components small with one responsibility
tags: component architecture, component design, single responsibility, hooks, composition, reuse
keywords: 1000 line component
refs: https://react.dev/learn/thinking-in-react

Split large components along responsibilities: data-fetching/stateful logic in custom hooks or containers, rendering in presentational components that take props. Prefer composition (`children`, slots, compound components) over configuration flags that multiply branches.

## optimistic-updates-rollback: Roll back optimistic updates on failure
tags: state management, optimistic update, mutation, rollback, error handling, ux
keywords: ui shows success but save failed
refs: https://tanstack.com/query/latest/docs/framework/react/guides/optimistic-updates

When updating the UI before the server confirms, snapshot the previous state, apply the change, and restore the snapshot and show an error if the mutation fails; refetch or invalidate afterwards so the cache matches the server.

## form-state-libraries: Use a form library and schema validation for non-trivial forms
tags: forms, form state, validation, react hook form, zod, controlled inputs, frontend
keywords: rerender per keystroke, validation duplicated
refs: https://react-hook-form.com/get-started

Large forms with hand-rolled state re-render on every keystroke and duplicate validation. Use a form library (React Hook Form, Formik, VeeValidate, Angular reactive forms) with a schema shared with the server where possible, show errors on blur/submit, and disable double submission while pending.
