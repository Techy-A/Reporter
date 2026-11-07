# Security model

Reporter handles candidate phone numbers and employee identities. The design assumes the
likeliest year-one failures are **identity mistakes and over-broad access**, not clever prompts.

## 1. Admin and employee portals are separate applications

| | Admin portal | Employee portal |
|---|---|---|
| Process / port | `apps.admin` / 8001 | `apps.portal` / 8002 |
| Network | IP allow-list (`PP_ADMIN_ALLOWED_CIDRS`); returns 404 to everyone else | Public |
| Authentication | Argon2 password + **mandatory TOTP**; lockout after 5 failures | 6-digit email code, hashed, 10-min TTL, 5 attempts, single use |
| Session | JWT `aud=admin`, key `PP_ADMIN_JWT_KEY`, cookie `__Host-pp_admin` | JWT `aud=portal`, key `PP_PORTAL_JWT_KEY` (must differ), cookie `__Host-pp_portal` |
| Revocation | `session_version` bump on logout / MFA change | bump on logout or when HR deactivates the employee |
| Postgres role | `pp_admin` | `pp_portal`: no access to admin users, channel tokens, chats or candidate contact columns |

Tests in `tests/test_portal_separation.py` prove a token from one portal is rejected by the other.

## 2. Data-leak controls
- **Explicit response schemas.** Each portal returns only allow-listed fields. Interviewers see a candidate's first name, role and time; never their phone or email.
- **Tenant scoping in code** (`db.scoped`, `db.get_scoped`), plus **Postgres row-level security** as a second wall. Cross-tenant ids return 404.
- **Encryption at rest** (Fernet) for phone numbers, emails, chat ids and channel tokens. Lookups use keyed HMAC hashes. The admin board shows masked phones only.
- **PII redaction** on every log line and on stored message text (phone, email, PAN, Aadhaar, UAN, IFSC, long numbers).
- **Sensitive messages** (harassment, threats, self-harm, legal) are detected locally *before* any LLM call. They are stored only as a marker and handed to a human.
- **Single-use, expiring, candidate-bound button tokens.** Replayed, forwarded or forged buttons are rejected and audited.
- **The LLM only classifies.** It never books, cancels or sends anything. Its output is validated against an allow-list.
- **Hardening:** strict CSP, `X-Frame-Options: DENY`, HSTS, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, CORS locked to each portal's own origin, SameSite=Strict cookies plus a required `x-pp-request` header (CSRF), no OpenAPI/docs endpoints, generic errors without stack traces, and validation errors that never echo input.
- **Webhooks:** WhatsApp `X-Hub-Signature-256` HMAC and Telegram secret token are verified before parsing. Bodies are size-limited and rate-limited. Unknown senders are silently ignored.
- **First-run setup** needs `PP_SETUP_TOKEN` and works only once.
- **Audit log:** metadata only (who, what, which record, result), kept 1 year. Chat logs are purged after 30 days. A **kill switch** pauses all outbound messages.
- **Containers:** non-root user, read-only filesystem, all capabilities dropped. Admin is bound to localhost.

## 3. Your responsibilities when self-hosting
- Keep `.env` secret and back up `PP_DATA_KEY` offline. Without it, encrypted data is unrecoverable.
- Serve the portals and webhooks **only over HTTPS**. Keep the admin portal on VPN or the office network.
- Use an LLM provider that does not train on your data, or a local model.
- Before May 2027 (DPDP Act obligations), publish a privacy notice to candidates and employees and keep a breach runbook (72-hour reporting).

## 4. Known gaps (Phase 1)
- The rate limiter is in-process. Use Redis or Postgres if you run multiple replicas.
- Email login codes depend on your mailbox security. SSO (Google/Microsoft) for the employee portal is planned.
- The Postgres RLS/roles script and the Docker deployment haven't been run in CI yet.

## Reporting a vulnerability
Please email the maintainer privately rather than opening a public issue.
