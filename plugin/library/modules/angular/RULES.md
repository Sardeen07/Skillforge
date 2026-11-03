---
module: angular
capability: Angular change detection, RxJS and signals
technologies: angular
applies: angular, rxjs, signals, observable, component
checked_against: Angular 19 documentation (angular.dev) and RxJS 7
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## onpush-change-detection: Use OnPush change detection with immutable inputs or signals
tags: angular, change detection, onpush, performance, signals, immutable
keywords: slow ui, change detection runs constantly
refs: https://angular.dev/best-practices/skipping-subtrees

`ChangeDetectionStrategy.OnPush` re-checks a component only when an input reference changes, an event fires in it, or a signal/async pipe it reads updates. Combine it with immutable updates (new objects, not mutation) or signals; mutating an input object in place will not re-render an OnPush child.

## unsubscribe-observables: Never leave manual subscriptions open
tags: angular, rxjs, subscribe, memory leak, takeUntilDestroyed, async pipe, unsubscribe
keywords: subscription leak, handler fires twice
refs: https://angular.dev/ecosystem/rxjs-interop/take-until-destroyed

Prefer the `async` pipe or `toSignal()`, which unsubscribe automatically. When you must `subscribe()` in a component, pipe through `takeUntilDestroyed()` (or `takeUntilDestroyed(this.destroyRef)` outside the constructor). HTTP observables complete on their own, but streams such as `valueChanges`, router events and intervals do not.

## flattening-operators: Pick the right flattening operator for nested requests
tags: angular, rxjs, switchMap, mergeMap, concatMap, exhaustMap, race condition, http
keywords: stale search results, nested subscribe
refs: https://rxjs.dev/api/operators/switchMap

Never subscribe inside a subscribe. Use `switchMap` for searches and route-param loads (cancel the previous request), `concatMap` to keep order for writes, `mergeMap` for independent parallel work, and `exhaustMap` to ignore repeat clicks while a submit is in flight.

## track-in-control-flow: Provide track expressions in @for loops
tags: angular, control flow, for loop, track, trackBy, ngFor, list rendering, performance
keywords: whole list re-rendered
refs: https://angular.dev/guide/templates/control-flow#why-is-track-in-for-blocks-important

The `@for` block requires `track`; use a stable id (`track item.id`), not `$index`, for lists that reorder or reload, so Angular reuses DOM nodes. In older `*ngFor` code, add a `trackBy` function.

## signals-for-state: Use signals and computed for component state
tags: angular, signals, computed, effect, state management, zoneless
keywords: BehaviorSubject for simple state
refs: https://angular.dev/guide/signals

For synchronous component and service state use `signal()`, derive with `computed()`, and reserve `effect()` for side effects that sync with the outside world (not for setting other signals). Keep RxJS for event streams and async orchestration, bridging with `toSignal`/`toObservable`.

## no-logic-in-templates: Avoid function calls in templates; use pipes or computed values
tags: angular, templates, pure pipe, performance, change detection, method call
keywords: method called every change detection
refs: https://angular.dev/guide/templates/pipes

A method called in a template (`{{ total(items) }}`) runs on every change-detection pass. Use a pure pipe, a `computed()` signal, or a precomputed field instead.

## lazy-load-routes: Lazy-load feature routes and standalone components
tags: angular, lazy loading, router, loadComponent, loadChildren, bundle size, standalone
keywords: large main bundle
refs: https://angular.dev/guide/routing/common-router-tasks#lazy-loading

Load feature areas on demand with `loadComponent: () => import('./admin/admin.component').then(m => m.AdminComponent)` or `loadChildren`, and use `@defer` blocks for heavy below-the-fold widgets.

## sanitization-bypass: Do not bypass Angular's sanitizer on untrusted values
tags: angular, xss, sanitization, bypassSecurityTrustHtml, innerHTML, security
keywords: bypassSecurityTrust, DomSanitizer
refs: https://angular.dev/best-practices/security

Angular escapes interpolation and sanitizes `[innerHTML]`. `DomSanitizer.bypassSecurityTrustHtml/Url/ResourceUrl` turns that off: use it only for constant or server-sanitized content, never for user input. Avoid direct DOM manipulation through `ElementRef.nativeElement.innerHTML`.
