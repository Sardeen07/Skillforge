---
module: android
capability: Android with Jetpack Compose: state, lifecycle and performance
technologies: android
applies: android, jetpack compose, viewmodel, room, workmanager, kotlin
checked_against: Android Developers documentation (Compose, architecture guide), 2025
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## state-hoisting-compose: Hoist state and keep composables stateless where possible
tags: android, jetpack compose, state hoisting, remember, viewmodel, unidirectional data flow
keywords: state lost on rotation, untestable composable
refs: https://developer.android.com/develop/ui/compose/state-hoisting

Pass state down and events up: a reusable composable takes `value` and `onValueChange`. Hold screen state in a `ViewModel` exposed as `StateFlow` and collected with `collectAsStateWithLifecycle()`; use `rememberSaveable` for UI state that must survive configuration changes and process death.

## recomposition-performance: Avoid unnecessary recomposition
tags: android, jetpack compose, recomposition, performance, stable types, remember, derivedStateOf, lazy column keys
keywords: list janky, recomposing every frame
refs: https://developer.android.com/develop/ui/compose/performance/bestpractices

Wrap expensive calculations in `remember(key)`, use `derivedStateOf` for values that change less often than their inputs (e.g. "show scroll-to-top button"), provide `key`s in `LazyColumn` items, prefer immutable/stable parameter types, and defer frequently changing state reads to lambdas (`Modifier.offset { }`). Check with the Layout Inspector's recomposition counts.

## lifecycle-aware-collection: Collect flows only while the UI is visible
tags: android, lifecycle, flow, collectAsStateWithLifecycle, repeatOnLifecycle, battery, leaks
keywords: updates processed in background
refs: https://developer.android.com/topic/libraries/architecture/coroutines#lifecycle-aware

Collecting flows in `lifecycleScope.launch` without lifecycle awareness keeps work running while the app is in the background, wasting battery and risking crashes. Use `collectAsStateWithLifecycle()` in Compose or `repeatOnLifecycle(STARTED)` in views.

## no-main-thread-io-android: Keep disk and network off the main thread to avoid ANRs
tags: android, anr, main thread, strictmode, coroutines, dispatchers io, room
keywords: application not responding
refs: https://developer.android.com/topic/performance/vitals/anr

Blocking the main thread for 5 seconds produces an ANR. Do network, database and file I/O in coroutines on `Dispatchers.IO` (Room and Retrofit suspend functions do this for you), enable `StrictMode` in debug builds to catch violations, and watch ANR rates in Play Console vitals.

## workmanager-deferrable: Use WorkManager for deferrable, guaranteed background work
tags: android, workmanager, background work, constraints, retries, doze, sync
keywords: background sync killed by system
refs: https://developer.android.com/develop/background-work/background-tasks/persistent

Background services are restricted on modern Android. Schedule uploads, syncs and cleanups with WorkManager, with constraints (network, charging), exponential backoff and unique work names to avoid duplicates; work survives app restarts and reboots.

## room-migrations: Write Room migrations and test them
tags: android, room, database, migrations, schema export, data loss, sqlite
keywords: fallbackToDestructiveMigration wiped user data
refs: https://developer.android.com/training/data-storage/room/migrating-db-versions

Export schemas (`exportSchema = true`), write a `Migration` or auto-migration for every version bump, and test them with `MigrationTestHelper`. `fallbackToDestructiveMigration()` deletes users' data on upgrade; use it only for caches.

## secure-storage-android: Store secrets with the Android Keystore and protect exported components
tags: android, security, keystore, encrypted storage, exported activities, intents, permissions
keywords: token in shared preferences, exported activity
refs: https://developer.android.com/privacy-and-security/security-tips

Keep keys in the Android Keystore and encrypt sensitive data at rest; never hardcode API secrets in the APK (it can be decompiled). Set `android:exported="false"` on components not meant for other apps, validate data from incoming intents and deep links, and request only the permissions you need.

## baseline-profiles-startup: Measure and improve startup with Macrobenchmark and Baseline Profiles
tags: android, startup time, baseline profiles, macrobenchmark, app startup, performance
keywords: slow cold start
refs: https://developer.android.com/topic/performance/baselineprofiles/overview

Measure cold startup with Macrobenchmark, ship Baseline Profiles so critical code paths are precompiled, defer non-essential initialization (lazy SDK init, App Startup library), and avoid heavy work in `Application.onCreate`.
