---
module: flutter
capability: Flutter widget performance, state and async safety
technologies: flutter
applies: flutter, dart, widget, setstate, riverpod, bloc
checked_against: Flutter 3.24 and Dart 3 documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## const-and-small-widgets: Split widgets and use const constructors to limit rebuilds
tags: flutter, widgets, const, rebuild, performance, build method, setstate
keywords: whole screen rebuilds on every keystroke
refs: https://docs.flutter.dev/perf/best-practices#control-build-cost

`setState` rebuilds the widget's whole subtree. Push state down into small widgets so only they rebuild, mark widgets that never change `const`, and avoid building large subtrees in a single `build` method or helper function (extract widget classes instead, which can be skipped).

## lazy-lists-flutter: Build long lists lazily with ListView.builder
tags: flutter, listview, builder, lazy loading, scrolling performance, memory
keywords: ListView with children of 10000 items
refs: https://docs.flutter.dev/cookbook/lists/long-lists

`ListView(children: [...])` builds every item up front. Use `ListView.builder`/`SliverList` so items build on demand, give items fixed extents (`itemExtent` or `prototypeItem`) when possible, and cache decoded image sizes with `cacheWidth`/`cacheHeight`.

## mounted-check-async: Check mounted before using context or setState after await
tags: flutter, async, mounted, buildcontext, setstate, lifecycle, dispose
keywords: setState called after dispose
refs: https://dart.dev/tools/linter-rules/use_build_context_synchronously

After an `await`, the widget may have been disposed. Check `if (!mounted) return;` (or `context.mounted`) before calling `setState` or using `BuildContext` (navigation, snackbars), and enable the `use_build_context_synchronously` lint.

## dispose-controllers: Dispose controllers, streams and subscriptions
tags: flutter, dispose, animationcontroller, texteditingcontroller, stream subscription, memory leak
keywords: memory leak, ticker active after dispose
refs: https://api.flutter.dev/flutter/widgets/State/dispose.html

Create `AnimationController`, `TextEditingController`, `ScrollController`, `FocusNode` and stream subscriptions in `initState` and release them in `dispose()`. Never create controllers inside `build`.

## state-management-choice: Pick one state management approach and keep business logic out of widgets
tags: flutter, state management, riverpod, bloc, provider, architecture, testability
keywords: logic inside build method
refs: https://docs.flutter.dev/data-and-backend/state-mgmt/options

Use `setState` for ephemeral widget state, and one app-wide approach (Riverpod, Bloc, Provider) for shared state. Keep networking and business rules in testable classes (repositories, notifiers/blocs), not in widgets, and expose immutable state objects.

## heavy-work-isolates: Move heavy computation to isolates
tags: flutter, dart, isolates, compute, jank, json parsing, performance, ui thread
keywords: ui freezes while parsing json
refs: https://docs.flutter.dev/perf/isolates

Dart runs UI code on one thread per isolate; parsing large JSON or processing images there drops frames. Run such work with `Isolate.run(() => ...)` (or `compute`), and profile with DevTools in profile mode, not debug mode, whose performance is not representative.

## platform-adaptive-flutter: Respect platform conventions, safe areas and text scaling
tags: flutter, safearea, text scaling, accessibility, platform adaptive, semantics
keywords: content under notch, text overflows
refs: https://docs.flutter.dev/ui/accessibility-and-internationalization/accessibility

Wrap screens in `SafeArea`, let text scale with system settings and test layouts at large scales, add `Semantics` labels for icon buttons, and use adaptive widgets where platform conventions differ (back navigation, switches, dialogs).
