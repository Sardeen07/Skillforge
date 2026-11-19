---
module: mobile-architecture
capability: Mobile app architecture, offline-first sync and mobile performance
technologies: mobile
applies: mobile, offline, sync, push notifications, deep links, battery, app performance
checked_against: Android architecture guide, Apple App Store Review Guidelines, web.dev offline cookbook
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## offline-first-local-source: Make the local database the source of truth for the UI
tags: mobile, offline first, local database, sync, repository pattern, caching, connectivity
keywords: app unusable without network
refs: https://developer.android.com/topic/architecture/data-layer/offline-first

Render from a local store (Room, Core Data/SwiftData, SQLite, Realm) and sync with the server in the background, so the app works offline and loads instantly. The repository writes server responses into the store and the UI observes the store, never the network directly.

## sync-conflicts: Queue offline writes and resolve conflicts deliberately
tags: mobile, offline sync, conflict resolution, outbox, idempotency, last write wins, crdt
keywords: offline edits lost, duplicates after reconnect
refs: https://developer.android.com/topic/architecture/data-layer/offline-first#write-strategies

Record offline changes in a local outbox with client-generated IDs, send them idempotently when online (retry with backoff), and choose a conflict policy per data type (last-write-wins with server timestamps, field-level merge, or user resolution). Never assume requests reach the server in order.

## network-efficiency-mobile: Minimize requests, payload size and radio wake-ups
tags: mobile, networking, battery, payload size, batching, caching, http caching, compression
keywords: app drains battery, slow on cellular
refs: https://developer.android.com/develop/connectivity/network-ops/network-access-optimization

Each radio wake-up costs battery. Batch requests, prefetch when on Wi-Fi/charging, cache with HTTP caching headers, compress payloads and request only needed fields, paginate lists, and set timeouts suited to flaky cellular networks with retry/backoff.

## backward-compatible-apis: Keep APIs compatible with old app versions in the field
tags: mobile, api versioning, backward compatibility, forced update, app versions, release
keywords: old app versions crash after backend deploy
refs: https://cloud.google.com/apis/design/compatibility

Users run old app versions for months. Backends must keep serving every supported version: add fields instead of changing them, tolerate unknown enum values in clients, send the app version with each request, and provide a minimum-version check with a forced-update flow for unsupported versions.

## deep-link-validation: Validate deep links and universal links like any untrusted input
tags: mobile, deep links, universal links, app links, security, navigation, validation
keywords: deep link opened screen without login
refs: https://developer.android.com/training/app-links/verify-android-applinks

Deep links can be crafted by anyone. Verify domains (Universal Links/App Links), parse and validate parameters, require authentication for protected destinations, and never perform state-changing actions directly from a link without user confirmation.

## secure-local-storage-mobile: Store tokens in the Keychain or Keystore, not plain preferences
tags: mobile, secure storage, keychain, keystore, tokens, encryption, security
keywords: token in UserDefaults or SharedPreferences
refs: https://developer.apple.com/documentation/security/keychain-services

Keep refresh tokens and credentials in the iOS Keychain or Android Keystore-backed encrypted storage, never in `UserDefaults`/`SharedPreferences` or plain files, exclude them from backups where appropriate, and clear them on logout. Do not embed server secrets in the app binary.

## crash-and-performance-monitoring: Monitor crashes, ANRs/hangs and startup in production
tags: mobile, crash reporting, performance monitoring, anr, hangs, startup time, releases
keywords: crash only on some devices
refs: https://developer.android.com/topic/performance/vitals

Ship crash reporting with symbolication (dSYMs, ProGuard/R8 mappings), track ANR/hang rates, cold-start time and frame drops per release and device class, and roll out releases in stages so regressions are caught before reaching everyone.

## mobile-feature-flags-kill-switch: Ship risky features behind remotely controlled flags
tags: mobile, feature flags, remote config, kill switch, release, rollback, app store review
keywords: cannot roll back a mobile release
refs: https://firebase.google.com/docs/remote-config

A mobile release cannot be rolled back instantly. Gate new or risky features behind remote flags (Firebase Remote Config, LaunchDarkly, your own endpoint) with safe defaults when the fetch fails, so a bad feature can be switched off without a new build.
