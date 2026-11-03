---
module: swiftui-uikit
capability: SwiftUI and UIKit state, rendering and performance
technologies: swiftui, uikit
applies: swiftui, uikit, ios, view, observable, table view, collection view
checked_against: Apple developer documentation (SwiftUI, UIKit; iOS 18)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## state-ownership-swiftui: Use the right property wrapper for who owns the state
tags: swiftui, state, observable, stateobject, binding, environment, data flow
keywords: view model recreated, state reset on redraw
refs: https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app

A view that creates a model must own it: `@State` for `@Observable` models (iOS 17+) or `@StateObject` for `ObservableObject`; never create them with `@ObservedObject` or plain `let` in a view that re-initializes, or the model is recreated on every parent update. Pass ownership downward with plain properties, `@Bindable`, `@Binding` or the environment.

## view-body-cheap: Keep SwiftUI view bodies cheap and dependencies narrow
tags: swiftui, performance, view body, recomputation, observation, redraw
keywords: list scrolls slowly, body recomputed constantly
refs: https://developer.apple.com/documentation/Xcode/understanding-and-improving-swiftui-performance

`body` can run often. Do not sort, filter, format dates or decode images inside it; precompute in the model. With `@Observable`, views re-render only for properties they read, so pass small sub-models or values to subviews rather than a large object every row reads.

## stable-identity-lists: Give list and ForEach items stable, unique identity
tags: swiftui, foreach, list, identifiable, identity, animations, state bugs
keywords: id: \.self on non unique values, wrong row animates
refs: https://developer.apple.com/documentation/swiftui/foreach

`ForEach` uses identity to diff. Use `Identifiable` models with stable IDs; avoid `id: \.self` for values that can repeat or change, and avoid array indices for mutable lists, or SwiftUI attaches state and animations to the wrong rows.

## async-work-in-task-modifier: Start async work with .task, not onAppear plus Task
tags: swiftui, task modifier, async, cancellation, onappear, lifecycle
keywords: request continues after leaving screen
refs: https://developer.apple.com/documentation/swiftui/view/task%28name%3Apriority%3Afile%3Aline%3A_%3A%29

`.task { await model.load() }` starts work when the view appears and cancels it when the view disappears; `.task(id:)` restarts it when a value changes. A `Task {}` inside `onAppear` is not cancelled automatically and can update state after the user left.

## uikit-cell-reuse: Configure reused table and collection cells completely
tags: uikit, uitableview, uicollectionview, cell reuse, prepareforreuse, images, diffable data source
keywords: wrong image in cell after scrolling
refs: https://developer.apple.com/documentation/uikit/uitableviewcell/prepareforreuse()

Cells are reused, so every configuration must set every property (or reset in `prepareForReuse`), and async image loads must check the cell still represents the same item before assigning. Use diffable data sources with stable identifiers for animated, crash-free updates.

## main-thread-io-ios: Keep I/O and heavy work off the main thread
tags: uikit, swiftui, main thread, hangs, performance, file io, image decoding, ios
keywords: app freezes, hang detected
refs: https://developer.apple.com/documentation/xcode/improving-app-responsiveness

The main thread must stay free to render frames. Move networking, disk access, JSON decoding and image processing to background tasks, and use Instruments (Time Profiler, Hangs) to find main-thread blocks.

## image-memory-ios: Downsample large images before display
tags: uikit, swiftui, images, memory, downsampling, image io, out of memory, ios
keywords: app killed for memory, huge photos in list
refs: https://developer.apple.com/documentation/imageio/cgimagesourcecreatethumbnailatindex(_:_:_:)

A decoded image costs width × height × 4 bytes regardless of its file size. Downsample to the displayed size with ImageIO thumbnails (or a library that does) before showing photos in lists, and cache the downsampled result, not the original.

## accessibility-ios: Support Dynamic Type, VoiceOver labels and sufficient hit areas
tags: swiftui, uikit, accessibility, voiceover, dynamic type, accessibility label, ios
keywords: text truncated at large sizes, unlabeled icon button
refs: https://developer.apple.com/documentation/accessibility/

Use text styles so fonts scale with Dynamic Type and let layouts wrap at large sizes, give icon-only controls `accessibilityLabel`s, group related elements, and keep tap targets at least 44×44 points. Test with VoiceOver and the Accessibility Inspector.
