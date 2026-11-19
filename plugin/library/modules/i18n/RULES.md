---
module: i18n
capability: Internationalization, localization and Unicode text handling
technologies:
applies: i18n, internationalization, localization, l10n, translation, unicode, locale, timezone
checked_against: Unicode Standard Annex #15, ICU MessageFormat, MDN Intl documentation
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-18; each rule cites the reference it was checked against
review: pending human review
---

## no-string-concatenation-translations: Externalize whole sentences with placeholders, never concatenated fragments
tags: i18n, localization, string concatenation, placeholders, icu messageformat, gettext, externalized strings
keywords: localized ui strings built with plus, sentence fragments in resource files
refs: https://unicode-org.github.io/icu/userguide/format_parse/messages/

Concatenating translated fragments breaks in languages with different word order and grammar. Externalize whole sentences with named placeholders (`"{count} messages from {name}"`) in a message format (ICU MessageFormat, Fluent, gettext), so translators can reorder them.

## plural-rules: Use CLDR plural rules instead of if count == 1
tags: i18n, plurals, cldr, icu, localization, count, message format
keywords: 1 items, plural form wrong in other languages
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/PluralRules

Languages have up to six plural categories (Arabic, Polish, Russian differ from English). Use ICU plural syntax or `Intl.PluralRules` / gettext `ngettext` so each locale picks the right form, instead of `count == 1 ? "item" : "items"`.

## locale-aware-formatting: Format numbers, currencies and dates with locale APIs
tags: i18n, number formatting, currency, dates, intl, locale, babel
keywords: 1,234.56 vs 1.234,56, date shown as 03/04
refs: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat

Decimal separators, grouping, currency position and date order vary by locale. Store canonical values (numbers, ISO currency codes, UTC instants) and format at display time with `Intl.NumberFormat`/`Intl.DateTimeFormat`, Babel (Python), or ICU; never parse or format user-facing numbers with fixed patterns.

## unicode-normalization: Normalize and case-fold text before comparing identifiers
tags: i18n, unicode, normalization, nfc, nfkc, casefold, usernames, comparison
keywords: two accounts with the same name, é not equal to é
refs: https://unicode.org/reports/tr15/

The same visible string can have different code-point sequences (precomposed `é` vs `e` + combining accent). Normalize (NFC for storage, NFKC plus case folding for identifiers such as usernames and emails) before comparing or enforcing uniqueness, and consider confusable-character checks for names shown to other users.

## text-length-and-truncation: Count and truncate text by grapheme clusters, not bytes or code units
tags: i18n, unicode, grapheme clusters, emoji, truncation, string length, utf 8
keywords: emoji cut in half, length limit counts wrong
refs: https://unicode.org/reports/tr29/

A single user-perceived character (an emoji with skin tone, a flag, an accented letter) can be several code points and more UTF-16 units or bytes. Truncate and count limits with grapheme segmentation (`Intl.Segmenter`, the `regex` module's `\X`, ICU), and size database columns for bytes when storing UTF-8.

## rtl-layout-support: Support right-to-left layouts with logical properties
tags: i18n, rtl, right to left, arabic, hebrew, css logical properties, dir attribute, layout
keywords: layout broken in arabic
refs: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_logical_properties_and_values

Set `dir="rtl"` (or `dir="auto"` for user content) on the document for right-to-left locales and use CSS logical properties (`margin-inline-start`, `padding-inline-end`, `inset-inline-start`) instead of left/right, so layouts mirror correctly; mirror directional icons such as arrows, but not logos or media controls.
