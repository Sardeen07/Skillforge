---
module: auth
capability: Authentication, sessions, tokens and authorization
technologies:
applies: authentication, authorization, login, jwt, oauth, session, password, permissions
checked_against: OWASP ASVS 4.0.3, OWASP cheat sheets, RFC 8725 (JWT BCP), OAuth 2.0 Security BCP (RFC 9700)
authorship: Drafted for SkillForge with Claude (Opus 5.5), 2026-11-03; each rule cites the reference it was checked against
review: pending human review
---

## password-storage: Hash passwords with a slow, salted algorithm
tags: authentication, password hashing, argon2, bcrypt, scrypt, salt, security
keywords: sha256 password, md5 password, plaintext password
refs: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

Store passwords only as Argon2id (preferred), scrypt or bcrypt hashes with per-user salts (the libraries handle salts), with parameters tuned to roughly 100ms+ per hash on your hardware. Never use fast hashes (SHA-256, MD5) or encryption. Rehash on login when parameters change, and compare using the library's verify function.

## jwt-verification: Verify JWT signature, algorithm, issuer, audience and expiry
tags: authentication, jwt, token validation, alg none, signature, audience, expiry, security
keywords: jwt decode without verify, accepted unsigned token
refs: https://www.rfc-editor.org/rfc/rfc8725.html

Decode JWTs only through a verify call that pins the expected algorithm(s) (never accept `alg: none` or let the token choose between HMAC and RSA), checks the signature with the right key (fetch and cache the issuer's JWKS), and validates `exp`, `nbf`, `iss` and `aud`. A decoded but unverified token is just user input.

## jwt-lifetime-and-revocation: Keep access tokens short-lived and refresh tokens revocable
tags: authentication, jwt, refresh token, revocation, logout, token lifetime, rotation
keywords: cannot log out user, stolen token valid for days
refs: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_Cheat_Sheet

Stateless JWTs cannot be revoked before expiry. Give access tokens short lifetimes (minutes), keep refresh tokens server-side-revocable (stored hashed, rotated on each use, with reuse detection), and keep a denylist only if you need immediate revocation. Do not put sensitive data in JWT payloads: they are only base64-encoded.

## token-storage-browser: Store browser session tokens in HttpOnly, Secure, SameSite cookies
tags: authentication, cookies, localstorage, xss, csrf, samesite, httponly, session
keywords: jwt in localStorage
refs: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#cookies

Tokens in `localStorage` are readable by any script, so one XSS steals every session. Prefer `HttpOnly; Secure; SameSite=Lax` (or `Strict`) cookies with a `__Host-` prefix, plus CSRF protection for state-changing requests when cookies authenticate them.

## session-fixation: Regenerate session IDs on login and privilege change
tags: authentication, session fixation, session id, login, logout, session management
keywords: same session id before and after login
refs: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#renew-the-session-id-after-any-privilege-level-change

Issue a new session identifier on login, logout and any privilege change, invalidate the old one server-side, set idle and absolute timeouts, and destroy the server session on logout (not only the cookie).

## authorization-every-request: Check object-level authorization on every request
tags: authorization, idor, bola, access control, permissions, multi tenant, security
keywords: change id in url see other users data
refs: https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/

Authentication says who the caller is; authorization must still check, for every resource access, that this caller may act on this specific object (`WHERE id = ? AND tenant_id = ?`). Enforce it centrally in the data-access or policy layer, deny by default, and test it: broken object-level authorization is the top API vulnerability.

## rbac-least-privilege: Model permissions explicitly and grant least privilege
tags: authorization, rbac, abac, roles, permissions, least privilege, policy
keywords: if user.is_admin everywhere
refs: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html

Check permissions (`can(user, "invoice:approve", invoice)`) rather than scattering role names through the code, so roles can change without code changes. Grant the minimum permissions needed, and use attribute rules (owner, tenant, state) when roles alone are not enough. Keep the policy in one place.

## oauth-pkce-state: Use authorization code flow with PKCE and validate state
tags: authentication, oauth, oidc, pkce, authorization code, state, redirect uri, sso
keywords: implicit flow, open redirect
refs: https://www.rfc-editor.org/rfc/rfc9700.html

Use the authorization code flow with PKCE for all clients (the implicit flow is deprecated), validate `state` (and the OIDC `nonce`) to prevent CSRF and replay, register exact redirect URIs (no wildcards), and verify ID tokens like any JWT. Prefer a maintained OIDC library to a hand-written flow.

## brute-force-protection: Throttle login, reset and MFA attempts
tags: authentication, brute force, credential stuffing, rate limiting, lockout, mfa, login
keywords: unlimited login attempts
refs: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#protect-against-automated-attacks

Rate-limit authentication endpoints per account and per IP, add progressive delays rather than permanent lockouts (which enable denial of service), check passwords against breached-password lists, and offer MFA. Use the same generic error message for "no such user" and "wrong password".

## password-reset-tokens: Make reset tokens random, single-use and short-lived
tags: authentication, password reset, tokens, account recovery, email, security
keywords: reset link never expires, predictable token
refs: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html

Generate reset tokens with a CSPRNG (at least 128 bits), store only their hash, expire them within an hour, invalidate them after use and after a password change, and invalidate existing sessions when the password changes. Respond identically whether or not the email exists.

## api-keys-handling: Treat API keys as secrets: hashed at rest, scoped and rotatable
tags: authentication, api keys, secrets, hashing, scopes, rotation, service accounts
keywords: api key stored in plaintext
refs: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

Generate keys with high entropy and a recognizable prefix (to enable secret scanning), show them once, store only a hash, attach scopes and an owner, support multiple active keys per client for rotation, and log their use (never the key itself).

## mfa-implementation: Implement MFA with TOTP or WebAuthn, not SMS alone
tags: authentication, mfa, 2fa, totp, webauthn, passkeys, sms, recovery codes
keywords: sms codes only
refs: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html

Prefer WebAuthn/passkeys (phishing-resistant) and TOTP; SMS is vulnerable to SIM swapping. Require re-authentication for sensitive changes, provide one-time recovery codes stored hashed, and rate-limit code verification.

## revoke-sessions-on-credential-change: Revoke other sessions and tokens when credentials change
tags: authentication, sessions, password change, revoke, refresh tokens, account takeover, logout everywhere
keywords: password change does not log out other devices, refresh tokens survive password reset
refs: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#renew-the-session-id-after-any-privilege-level-change

Changing or resetting a password (or enabling MFA) should end every other session and revoke refresh tokens and outstanding reset links for that account, keeping only the current session if appropriate. Otherwise an attacker who already has a session keeps access after the victim "secures" the account. Offer "log out of all devices" too.

## reauthenticate-sensitive-actions: Require recent authentication for sensitive changes
tags: authentication, reauthentication, step up, email change, password change, mfa, security
keywords: change email without password
refs: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#reauthentication-after-risk-events

Changing the email address, password, MFA settings or payout details should require the current password or a fresh MFA check, even within a valid session. Verify a new email address by sending a link to it, and notify the old address of the change.
