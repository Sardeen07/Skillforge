---
module: javascript
capability: JavaScript language pitfalls and async correctness
technologies: javascript
applies: javascript, js, promise, async, await, array, object
checked_against: MDN Web Docs and ECMAScript 2025
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## strict-equality: Use === and !== and handle null explicitly
tags: javascript, equality, comparison, type coercion, null, undefined
keywords: == coercion, '0' == 0, falsy
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Equality_comparisons_and_sameness

`==` coerces types (`'0' == 0`, `[] == false` are true). Use `===`. To test "null or undefined" write `value == null` deliberately or `value === null || value === undefined`. Use `??` (not `||`) for defaults so `0`, `''` and `false` are kept: `const port = config.port ?? 8080`.

## unhandled-promise-rejections: Await or handle every promise
tags: javascript, promise, async, await, unhandled rejection, error handling, floating promise
keywords: forgot await, catch, fire and forget, process crashes
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Using_promises#error_handling

A promise that is neither awaited nor given a `.catch` loses its error; in Node.js an unhandled rejection terminates the process by default. Await every promise whose result or failure matters; for deliberate fire-and-forget, attach `.catch(err => log(err))`. Enable the `@typescript-eslint/no-floating-promises` or `no-async-promise-executor` lint rules.

## promise-all-for-independent-work: Start independent async work together
tags: javascript, promise all, async, await, parallel, waterfall, sequential, allSettled
keywords: await in loop, one after another
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all

`await` inside a loop or consecutive awaits on independent calls serialize them. Start them first and await together: `const [user, orders] = await Promise.all([getUser(id), getOrders(id)])`. Use `Promise.allSettled` when one failure must not discard the others, and bound concurrency (for example with `p-limit`) for large arrays.

## array-methods-mutation: Know which array methods mutate
tags: javascript, array, sort, reverse, splice, mutation, immutable, toSorted
keywords: sort changed original, state mutated
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/toSorted

`sort`, `reverse`, `splice` and `fill` mutate in place, which corrupts shared or framework state. Use `toSorted`, `toReversed`, `toSpliced` and `with` (ES2023) or copy first (`[...arr].sort()`). `sort()` without a comparator sorts as strings: `[10, 9, 1].sort()` gives `[1, 10, 9]`; pass `(a, b) => a - b`.

## number-precision: Do not use floating point for money or large integer IDs
tags: javascript, number, float, precision, bigint, money, integer id
keywords: 0.1 + 0.2, MAX_SAFE_INTEGER, id changed after JSON.parse
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER

All numbers are IEEE-754 doubles: integers above 2^53-1 lose precision (64-bit database IDs parsed from JSON change silently) and decimal fractions are inexact. Transport large IDs as strings, use `BigInt` for big integer arithmetic, and represent money as integer minor units or a decimal library.

## this-binding: Use arrow functions or bind for callbacks that use this
tags: javascript, this, arrow function, bind, callback, class method, event handler
keywords: this is undefined, cannot read property of undefined
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this

`this` depends on how a function is called, so a method passed as a callback (`setTimeout(obj.tick, 100)`, `button.addEventListener('click', this.onClick)`) loses its object. Use an arrow function wrapper, a class field arrow (`onClick = () => {...}`), or `.bind(this)` once in the constructor.

## modules-esm: Prefer ES modules with explicit, side-effect-free exports
tags: javascript, esm, modules, import, export, commonjs, tree shaking
keywords: require vs import, default export, circular dependency
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules

Write ES modules with named exports; avoid top-level side effects so bundlers can tree-shake and imports stay cheap. Do not mix `require` and `import` in one package without a clear `"type"` field and export map. Break circular imports by moving shared code to a third module; cycles yield `undefined` bindings at load time.

## avoid-prototype-pollution: Never merge untrusted objects into plain objects
tags: javascript, prototype pollution, security, merge, object assign, json, __proto__
keywords: deep merge user input, Object.create(null)
refs: https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html

Recursive merges of parsed JSON can write `__proto__` or `constructor.prototype` and change every object. Validate input against a schema, use `Map` or `Object.create(null)` for dictionaries keyed by user input, reject `__proto__`/`constructor`/`prototype` keys, and keep merge libraries patched.

## structured-clone-copies: Copy deeply with structuredClone, not JSON round trips
tags: javascript, deep copy, clone, structuredClone, json stringify, date
keywords: JSON.parse(JSON.stringify, lost Date, Map
refs: https://developer.mozilla.org/en-US/docs/Web/API/Window/structuredClone

Spread (`{...obj}`) copies one level only. `JSON.parse(JSON.stringify(x))` drops `undefined`, functions and turns `Date` into strings and `Map`/`Set` into `{}`. Use `structuredClone(x)` (browsers and Node 17+) for deep copies of data.

## timers-and-cleanup: Clear timers, listeners and intervals you create
tags: javascript, setInterval, setTimeout, event listener, memory leak, cleanup, abortcontroller
keywords: leak, removeEventListener, interval keeps running
refs: https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener#signal

Every `setInterval`, `setTimeout`, `addEventListener` and subscription keeps its closure alive until removed. Store the handle and clear it on teardown, or pass an `AbortController` signal to `addEventListener` and `fetch` and call `abort()` once to remove all of them.

## fetch-error-handling: Check response.ok and set timeouts on fetch
tags: javascript, fetch, http, error handling, timeout, abort, response ok
keywords: 404 treated as success, request hangs forever
refs: https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#checking_that_the_fetch_was_successful

`fetch` rejects only on network failure; a 404 or 500 resolves normally. Check `if (!res.ok) throw new Error(...)` before parsing. There is no default timeout: pass `signal: AbortSignal.timeout(10_000)`.

## regex-catastrophic-backtracking: Avoid nested quantifiers in regexes run on user input
tags: javascript, regex, redos, backtracking, security, performance, validation
keywords: (a+)+, regex hangs, event loop blocked
refs: https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS

Patterns such as `(a+)+$` or `(\w+\s?)*$` take exponential time on crafted input and freeze a single-threaded runtime. Avoid nested or overlapping quantifiers, cap input length before matching, anchor patterns, and prefer a parser or a library validator for emails/URLs.
