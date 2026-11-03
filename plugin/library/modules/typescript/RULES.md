---
module: typescript
capability: TypeScript type safety and configuration
technologies: typescript
applies: typescript, types, tsconfig, generics, interface
checked_against: TypeScript 5.x handbook
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## strict-mode: Enable strict and noUncheckedIndexedAccess in tsconfig
tags: typescript, tsconfig, strict, null checks, compiler options, configuration
keywords: strictNullChecks, undefined is not an object, index signature
refs: https://www.typescriptlang.org/tsconfig/#strict

Turn on `"strict": true` (null checks, implicit any, strict function types) for every new project, and add `"noUncheckedIndexedAccess": true` so `arr[i]` and `record[key]` are typed `T | undefined`. Migrate an existing codebase file by file rather than leaving strictness off.

## avoid-any: Use unknown instead of any and narrow it
tags: typescript, any, unknown, type safety, narrowing, type guard
keywords: as any, disables type checking
refs: https://www.typescriptlang.org/docs/handbook/2/narrowing.html

`any` switches type checking off and spreads silently through every value it touches. Type untrusted values (JSON, `catch` errors, third-party callbacks) as `unknown` and narrow with `typeof`, `instanceof`, `in` or a user-defined type guard before use. Ban `any` with `@typescript-eslint/no-explicit-any`.

## validate-at-runtime-boundaries: Validate external data at runtime; types do not
tags: typescript, validation, zod, runtime, api response, json, schema, type assertion
keywords: as User, trusted the type, response shape changed
refs: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#type-assertions

Types are erased at runtime, so `const user = await res.json() as User` asserts without checking. Parse request bodies, API responses, environment variables and storage with a schema validator (zod, valibot, io-ts) and derive the static type from the schema (`type User = z.infer<typeof User>`).

## discriminated-unions: Model states with discriminated unions and exhaustive switches
tags: typescript, discriminated union, union type, switch, exhaustive, never, state machine
keywords: optional fields everywhere, impossible states
refs: https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions

Instead of one object with many optional fields (`{ loading?: boolean; data?: T; error?: E }`), model each state: `type State = { kind: 'loading' } | { kind: 'ok'; data: T } | { kind: 'error'; error: E }`. Switch on `kind` and add a `default` branch that assigns to `never`, so adding a state becomes a compile error at every unhandled site.

## avoid-non-null-assertion: Avoid ! and as casts; narrow instead
tags: typescript, non null assertion, type assertion, cast, narrowing, undefined
keywords: user!.name, as unknown as
refs: https://www.typescriptlang.org/docs/handbook/2/everyday-types.html#non-null-assertion-operator-postfix-

`value!` and `x as T` tell the compiler to trust you and move the crash to runtime. Prefer an explicit check (`if (!user) throw new NotFound()`), optional chaining with a fallback, or fixing the type at its source. Reserve `as` for genuinely unrepresentable cases and add a comment saying why it is safe.

## satisfies-operator: Use satisfies to check a literal without widening it
tags: typescript, satisfies, const, literal types, configuration object, inference
keywords: lost key autocomplete, widened to string
refs: https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html#the-satisfies-operator

Annotating `const routes: Record<string, Route> = {...}` loses the exact keys. `const routes = {...} satisfies Record<string, Route>` checks the shape while keeping literal keys and values for inference; combine with `as const` for readonly literal tuples and unions.

## generics-constraints: Constrain generics and let inference work
tags: typescript, generics, constraints, extends, keyof, inference, utility types
keywords: T extends, generic function returns any
refs: https://www.typescriptlang.org/docs/handbook/2/generics.html#generic-constraints

Write `function pluck<T, K extends keyof T>(obj: T, key: K): T[K]` rather than `any`-typed helpers. Constrain type parameters to what the body uses, avoid type parameters that appear only once (they add nothing), and reuse built-in utility types (`Pick`, `Omit`, `Partial`, `ReturnType`, `Awaited`) before writing your own.

## readonly-and-immutability: Mark data readonly at API boundaries
tags: typescript, readonly, immutable, as const, ReadonlyArray, mutation
keywords: function mutated my array
refs: https://www.typescriptlang.org/docs/handbook/2/objects.html#readonly-properties

Accept `readonly T[]`/`ReadonlyArray<T>` and `Readonly<T>` parameters when a function must not mutate its inputs; the compiler then rejects `push` or assignment. `readonly` is shallow and compile-time only; use `Object.freeze` if runtime protection matters.

## enums-vs-unions: Prefer string literal unions or const objects over enums
tags: typescript, enum, union, const enum, string literal, isolatedModules
keywords: enum runtime code, const enum with babel
refs: https://www.typescriptlang.org/docs/handbook/enums.html#objects-vs-enums

Numeric enums accept any number and both regular and `const` enums emit or require special compilation (`const enum` breaks under `isolatedModules`, used by esbuild/SWC/Babel). A union `type Role = 'admin' | 'user'` or `const Role = { Admin: 'admin' } as const` with `type Role = typeof Role[keyof typeof Role]` is erasable and works with every transpiler.

## type-only-imports: Use import type and verbatimModuleSyntax
tags: typescript, import type, modules, bundler, esm, verbatimModuleSyntax, isolatedModules
keywords: import elided, circular import at runtime
refs: https://www.typescriptlang.org/tsconfig/#verbatimModuleSyntax

Mark type-only imports (`import type { User } from './types'`) and enable `verbatimModuleSyntax`, so transpilers drop exactly those imports and never keep a runtime import of a module that only provides types (a common source of circular-dependency bugs and bundle bloat).

## error-typing-in-catch: Treat caught errors as unknown
tags: typescript, catch, error handling, unknown, useUnknownInCatchVariables, exception
keywords: err.message on non Error
refs: https://www.typescriptlang.org/tsconfig/#useUnknownInCatchVariables

Anything can be thrown, so `catch (err)` is `unknown` under strict mode. Narrow before use: `const message = err instanceof Error ? err.message : String(err)`. When rethrowing, wrap with `new Error('context', { cause: err })` to keep the original.

## project-references-and-paths: Keep path aliases in sync between tsconfig and the runtime
tags: typescript, tsconfig, paths, alias, module resolution, monorepo, project references
keywords: cannot find module at runtime, works in editor
refs: https://www.typescriptlang.org/tsconfig/#paths

`compilerOptions.paths` only affects type checking; the bundler, test runner and Node must resolve the same aliases (bundler config, `vite-tsconfig-paths`, Node subpath `imports`). In monorepos, use project references or workspace packages with `exports` rather than reaching into another package's `src` through relative paths.
