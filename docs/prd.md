# Snip — URL Shortener PRD

**Author:** Product
**Status:** Draft v4
**Last updated:** 2026-06-01

## Overview

Snip is a URL shortener for small marketing teams. A marketer pastes a long destination URL, gets back a short link they can share, and sees per-link click analytics afterward. Behind the scenes, the redirect service records every click before redirecting.

The product targets teams of 5–50 employees who run campaigns across email, social, and ads. It is a simple alternative to Bitly for teams who don't need enterprise features but want more than a free tier with usage caps.

## Glossary

| Term | Definition |
|---|---|
| **Workspace** | The canonical container for a group of users and the links they own. Also called "the team" in casual usage, but **Workspace** is the system-of-record name. |
| **Member** | A user who belongs to a Workspace. Roles: **Admin** (can invite/remove others) or **Editor** (can create/edit links). |
| **Invite** | A pending request to join a Workspace, sent to an email address. |
| **Short code** | The unique identifier string that comes after the slash. The canonical generated form is 7 lowercase + uppercase alphanumeric characters using nanoid. |
| **Slug** | A user-chosen short code. Treated identically to a generated short code once stored, just with a different origin. |
| **Short URL** | The full HTTPS URL: `https://snip.io/<short-code>`. |
| **Destination URL** | The long URL the short URL redirects to. |
| **Click** | One successful redirect event (GET on `/<short-code>` returning a 30x). |
| **Activated Workspace** | A Workspace whose creator has verified their email **and** which has created at least one link. The denominator for all "activation"-based success metrics. |
| **User** | A signed-up Snip account, before and independently of Workspace membership. In feature descriptions, "Member" refers to a User who currently belongs to a Workspace. |

## Target users

The primary user is a marketing manager at a small business (5–50 employees) running campaigns across email, social, and ads. They are comfortable with web tools but not technical engineers. They care about:

1. Creating short links quickly (paste → click → copy in under 5 seconds).
2. Seeing per-link performance without having to learn a BI tool.
3. Sharing results inside the team.

Secondary users are the marketing manager's teammates — content writers, social-media coordinators — who create links inside the same Workspace.

## Goals and success metrics

| Goal | Metric | Target (by end of month 6) |
|---|---|---|
| Make link creation fast | Median paste-to-copy time per link | < 5 seconds |
| Drive habitual use | Workspaces creating ≥ 3 links in week 1 | ≥ 60% of activated Workspaces |
| Reliable redirect path | p95 redirect latency, server-side | < 100ms globally |
| Reliable redirect path | Redirect endpoint monthly availability | ≥ 99.95% |
| Useful analytics | Workspaces who open a link detail page in week 1 | ≥ 40% of activated Workspaces |
| Conversion to paid | Activated Workspaces who convert to paid by week 8 | ≥ 5% |

## User flows

### Flow A — Authenticated user creates a short link

1. **Trigger.** A signed-in Member opens the Snip dashboard at `/links`.
2. **Action.** They paste a destination URL into the create-link input and either (a) leave the slug field empty for auto-generation, or (b) type a custom slug.
3. **System response.** On submit, the link-creation API validates the URL, generates or accepts the short code, persists the link, and returns the Short URL. The dashboard displays the new Short URL with a Copy button focused.
4. **End state.** The new link appears at the top of the Workspace's link list.

**Failure path.** If the API returns an error (validation failure, rate limit, or storage error), the form remains open and shows the relevant inline error message (see Error scenarios). No partial link is created.

### Flow B — Anonymous visitor follows a short URL

1. **Trigger.** A browser requests `https://snip.io/<short-code>`.
2. **Action.** The redirect service looks up the short code.
3. **System response.** On hit, the redirect service emits a click event synchronously to the click pipeline, then returns a `302 Found` with `Location: <destination-url>`. On miss or soft-delete, returns a branded 404 page.
4. **End state.** The visitor is redirected to the destination URL; the click ingest service records the click in the analytics store within 60 seconds.

**Failure paths.** If the redirect datastore is unreachable, the redirect service returns a `503` page (not a branded 404). If the click pipeline is unavailable, the click event is durably queued locally; the 302 redirect still completes immediately.

### Flow C — Member views analytics for a link

1. **Trigger.** A signed-in Member clicks a row in the link list.
2. **Action.** The dashboard navigates to `/links/<short-code>`.
3. **System response.** The link-detail page loads showing click count, a time-series chart of clicks per UTC day for the last 30 days, and a country breakdown.
4. **End state.** Member sees up-to-date analytics (data freshness: ≤ 60 seconds behind real-time).

## Features

### Link creation

**Acceptance criteria:**

- Given a signed-in Member submits an `http://` or `https://` URL of ≤ 2048 characters, when they click Create, then the system returns a Short URL and the new link is visible in the Workspace's link list.
- The auto-generated short code is exactly 7 characters from the alphabet `[A-Za-z0-9]` (nanoid-style).
- A custom slug must match `^[A-Za-z0-9_-]{3,32}$`. Slugs are case-sensitive and unique globally across `snip.io`. Case-variants of the same string (`Foo` and `foo`) are treated as distinct slugs and may both exist simultaneously.
- Reserved prefixes (cannot be used as slugs): `admin`, `api`, `app`, `auth`, `dashboard`, `help`, `login`, `logout`, `settings`, `signup`, `static`, `www`.
- A previously deleted slug becomes reusable after 30 days.
- Only schemes `http:` and `https:` are accepted. `ftp:`, `javascript:`, `data:`, `file:`, and others are rejected.
- IDN hosts are accepted and stored in punycode form.
- Submitting the same Destination URL twice by the same Member creates a second short code; deduplication is not performed.
- Destination URLs are checked against the **Google Safe Browsing v4 Lookup API** (host+path) at create time. Lookup timeout: 800ms. Fail-open on timeout or API error: the link is created and silently added to the **Abuse review queue** — an internal ops tool where trust-and-safety reviewers inspect flagged links within 24 hours. Reviewer actions are: whitelist (no change to the live link), disable (link returns 404 to visitors until reviewed), or hard-delete. While a link is pending in the queue it redirects normally. A blocked URL surfaces the error described below; the support email in the error is the manual override path for operators in v1.

**Error scenarios:**

| Failure | User-visible behavior |
|---|---|
| URL syntax invalid | Inline form error: "That doesn't look like a URL. Make sure it starts with http:// or https://." |
| Scheme not allowed | Inline form error: "Only http and https links are supported." |
| URL > 2048 chars | Inline form error: "URL is too long. Maximum 2048 characters." |
| Custom slug taken | Inline form error on slug field: "That short link is already in use. Try a different one." |
| Custom slug malformed | Inline form error: "Short links must be 3–32 letters, numbers, hyphens, or underscores." |
| Destination on blocklist | Inline form error: "We can't shorten this link. Contact support if you think this is a mistake." |
| Rate-limited (> 60 links/min/user) | HTTP 429 + toast: "You're creating links faster than allowed. Try again in a minute." |
| Storage write failure | HTTP 500 + toast: "Something went wrong on our end. We've logged it — please try again." |

### Link list

**Acceptance criteria:**

- Members see every link in their Workspace (not just their own), sorted by `created_at` DESC. Tiebreaker: `id` DESC.
- The list shows: Short URL (with copy button), Destination URL (truncated to 60 chars with full URL on hover), click count, creator, and `created_at` displayed in the viewer's browser timezone.
- The list is paginated, 50 items per page. Beyond page 1, navigation is forward/back only (no jump-to-page). Pagination controls are hidden when the result set fits on a single page (≤ 50 items).
- Filter by date range filters by `created_at`, inclusive on both bounds. The frontend converts the browser-timezone date bounds to UTC before sending filter parameters to the API; the API always operates in UTC. The UI offers four presets — Today, Last 7 days, Last 30 days, Custom — where Custom is a date-picker bounded to the last 12 months.
- Empty state (no links yet in the Workspace) shows a single CTA "Create your first link" pointing at the create-link form.

**Error scenarios:**

| Failure | User-visible behavior |
|---|---|
| List API 5xx | Skeleton state + retry button. Retry uses exponential backoff up to 3 attempts. |
| Filter returns zero results | Empty state: "No links match this filter. Try a wider range." |

### Click analytics

**Acceptance criteria:**

- A click is any `GET /<short-code>` that returns a 30x response. `HEAD` requests are excluded.
- Bot User-Agents matching the IAB / ABC International Spiders & Bots List are excluded from the displayed count, but raw counts are still stored.
- Click counts on the detail page are accurate within ≤ 60 seconds of real-time (see Click pipeline — ingest SLO and visibility SLO).
- The time-series chart uses UTC-day buckets for the last 30 days.
- Country is derived from the requester IP via MaxMind GeoLite2. When IP is unresolvable, the country bucket is "Unknown".

**Error scenarios:**

| Failure | User-visible behavior |
|---|---|
| Click pipeline ingest failure | The click pipeline durably queues the event; the redirect still succeeds. The click appears in analytics on the next successful flush. |
| Detail page analytics query 5xx | Page renders the link metadata but shows "Analytics temporarily unavailable. Try again in a minute." in the chart slot. |
| Link does not exist | 404 page. |

### Teams (Workspaces)

**Acceptance criteria:**

- Every Member belongs to exactly one Workspace in v1. Workspace switching is out of scope. A signed-in Member who already belongs to a Workspace cannot create an additional Workspace — the create-Workspace option is not surfaced in the UI for existing Members.
- Roles: **Admin** and **Editor**. The Workspace's creator is the first Admin.
- Admins can invite Editors and other Admins by email. Editors can create/edit/delete links but cannot manage Members.
- An invite expires 7 days after creation. Re-inviting a still-pending email replaces the existing invite (resets the 7-day clock). Recipients can accept or decline an invite via links in the invitation email. Declining marks the invite `declined`; the declined email is immediately eligible for re-invite by the Workspace Admin.
- An Admin can remove a Member. Removed Members lose access immediately (active sessions are invalidated at the moment of removal). Their links remain in the Workspace, and the system atomically reassigns `owner_id` to the Admin performing the removal. Any pending invites sent by the removed Member are cancelled immediately. The removed Member's email address is immediately eligible for re-invite.
- A Workspace must have at least 1 Admin at all times. The last Admin cannot remove themselves and cannot demote themselves. This constraint is enforced at the API layer and applies to all surfaces, including operator and support tooling.
- Inviting an email that already has a Snip account in a different Workspace is allowed only if Workspace switching has shipped — for v1, the invite returns an error directing the user to use a different email.

**Error scenarios:**

| Failure | User-visible behavior |
|---|---|
| Invite to email already pending | "That invite is still active. You can resend or cancel it from the Members page." |
| Invite to email already in another Workspace (v1) | "That email is already associated with another Snip account. Ask them to use a different email or sign in." |
| Last-Admin self-removal attempt | "You're the only Admin. Promote another Member to Admin first." |
| Invite link expired | Recipient sees: "This invite has expired. Ask the Workspace Admin to resend it." |
| Recipient declines invite | Invite is marked declined; Workspace inviter sees the declined state in the Members page. Declined email is immediately eligible for re-invite. |
| Member tries to create a second Workspace | "You're already part of a Workspace. Multiple Workspaces are not supported yet." |

### Account

**Acceptance criteria:**

- Sign-up requires email + password. Email verification is required before the user can create any links; until verified, the user can sign in but only sees a "Please verify your email" gate.
- Password policy: minimum 12 characters, no character-class requirement, but each password is checked against the Pwned Passwords k-anonymity API and rejected if found.
- Passwords are stored as Argon2id hashes.
- Password reset is initiated by entering an email; if the email exists, a single-use reset token is mailed. Token TTL: 60 minutes. Token is single-use. The reset link form does not reveal whether the email exists ("If that email is registered, we've sent a reset link").
- Failed-login throttling: 5 failed attempts per email per 15 minutes triggers a 15-minute lockout. Lockout is per-email, not per-IP.
- Sessions: HTTP-only secure cookie, 30-day absolute expiry, 7-day idle expiry.

**Error scenarios:**

| Failure | User-visible behavior |
|---|---|
| Sign-up email already exists | "An account with that email already exists. Sign in or reset your password." |
| Pwned password detected | Inline form error: "This password has appeared in a known data breach. Please choose a different one." |
| Reset token used or expired | Reset page shows: "This reset link is no longer valid. Request a new one." |
| Email-verification link expired | "This link has expired. Sign in and we'll send a fresh one." |

## External integrations

### Mixpanel — analytics export

Mixpanel is used to give Workspace Admins access to advanced reporting that Snip's built-in analytics does not provide. v1 sends a subset of events.

**Transport.** Server-side via Mixpanel's `/track` HTTP API. No client-side SDK.

**Events.**

| Event | When emitted | Required properties |
|---|---|---|
| `link_created` | After a link is durably persisted | `workspace_id`, `member_id`, `short_code`, `destination_host`, `is_custom_slug` (bool) |
| `link_clicked` | After the redirect service emits a click | `workspace_id`, `short_code`, `country_code`, `is_bot` (bool), `referrer_host` |
| `member_invited` | After an invite is sent | `workspace_id`, `inviter_id`, `invite_role` |
| `password_reset_requested` | After a reset email is dispatched | `email_domain` only (no full email) |

**Identity.** Mixpanel `distinct_id` = our `member_id`. Anonymous click events do not carry `distinct_id`.

**Auth.** A single Mixpanel project token, stored as an env var; no per-Workspace projects in v1.

**Failure handling.** Events are queued in-process; failures retry 3× with exponential backoff (1s, 4s, 16s). After exhaustion, events are written to a dead-letter table for ops review. Failures never block the user-visible request that triggered them.

**PII exclusions.** Email addresses (full), passwords, raw IP addresses, and reset tokens are never sent to Mixpanel.

### Pwned Passwords — breach check

The Account password policy requires that every password create / change be checked against [Have I Been Pwned's Pwned Passwords](https://haveibeenpwned.com/Passwords) via the k-anonymity API.

**Transport.** Server-side HTTPS GET to `api.pwnedpasswords.com/range/<5-char-SHA1-prefix>`. The full hash is never sent.
**Timeout.** 500ms per request.
**Retry.** One retry with 100ms backoff on network error.
**Fail-open vs fail-closed.** Fail-**open** — when the API is unreachable or times out twice, the password is accepted; the event is logged with `pwned_check_skipped=true` and reviewed daily. Rationale: rejecting sign-ups on third-party outage is worse than briefly admitting a previously-leaked password.
**Caching.** No local cache of the prefix space in v1 (per-request lookups).
**Auth.** Public API, no auth.

### Email delivery — transactional mail

Email delivery is a hard dependency of Account (verification + reset) and Teams (invites).

**Provider.** AWS SES in v1.
**Sender identity.** All transactional mail from `noreply@snip.io`, signed with DKIM, with SPF and DMARC records published.
**Suppression enforcement.** Before queuing any outbound email, the application checks the internal suppression list; addresses marked suppressed are silently skipped. The SES account-level suppression list is not the primary enforcement point.

**Failure handling.** SES bounces and complaints are routed to an SNS topic consumed by a `mail_events` worker that marks the recipient address as suppressed. The user-visible behavior on failure depends on context:
- **Verification email failed to send:** Sign-up succeeds, banner on next page: "We couldn't send your verification email. We'll retry in 5 minutes — or click here to resend."
- **Reset email failed to send:** Generic "If that email is registered, we've sent a reset link" message (do not reveal failure to the requester; ops alert fires).
- **Invite email failed to send:** Admin sees the invite in `failed` state on the Members page with a "Resend" action.

**Rate limits.** SES sandbox limits apply in non-prod; prod starts at 14 messages/sec on a verified-sender configuration. Limit increases are requested via AWS Support (1–3 business day lead time). While throttled, the application queues outbound emails and retries; the user-visible behavior is governed by the failure path in each mail-triggering flow (verification, reset, invite).
**SLA.** SES standard SLA; no per-Workspace SLA exposed.

### MaxMind GeoLite2 — country lookup

Used by the redirect service to populate the `country_code` on click events.

**Transport.** Local `.mmdb` file distributed to each edge POP at deploy time. No hosted-API lookups (latency budget on the redirect path forbids it).
**Update cadence.** Twice weekly (GeoLite2 release schedule). A scheduled job pulls the latest DB from MaxMind, signs it, and pushes to all POPs via the same artifact-distribution pipeline used for service binaries.
**Fallback.** When the local DB is missing, stale by > 30 days, or returns no match, the `country_code` is recorded as `"Unknown"`. Stale-DB events trigger an ops alert at the 21-day mark.
**License.** GeoLite2 free tier; attribution requirement satisfied in the public Privacy page.

### Click pipeline — internal ingest bus

The redirect service publishes a click event to the click ingest service immediately after emitting the 302 response. The click ingest service writes to the analytics store.

**Transport.** Async queue (SQS or equivalent). The redirect service is the sole producer; the click ingest service is the sole consumer.
**Message schema.** Each event carries: `short_code`, `workspace_id`, `link_id`, `country_code`, `is_bot` (bool), `referrer_host`, `clicked_at` (RFC 3339 UTC).
**Durability.** At-least-once delivery. The ingest consumer is idempotent on `(link_id, clicked_at)`.
**Ordering.** Best-effort; out-of-order delivery is acceptable for a time-series use case.
**Ingest SLO.** Click written to the durable queue ≤ 2 seconds after the 302 response.
**Visibility SLO.** Analytics store reflects all queued clicks within 60 seconds of ingest. This is the ≤ 60-second freshness budget referenced in Flows B and C and the Click analytics AC.
**Throughput.** Sized for redirect p95 traffic × 2 headroom.
**Failure.** If the queue is unavailable at emit time, the redirect service falls back to local durable buffering and retries when the queue recovers. See "Click pipeline ingest failure" in Click analytics error scenarios.

## Non-functional requirements

- **Performance.** Redirect p95 < 100ms server-side globally; dashboard initial-render p95 < 2s on mid-tier mobile over 4G (Lighthouse "Slow 4G" throttle profile, Moto G Power-class device).
- **Availability.** Redirect endpoint ≥ 99.95% monthly. Dashboard ≥ 99.5% monthly.
- **Security.** TLS 1.2+ everywhere. Passwords hashed with Argon2id. Email addresses encrypted at rest (AES-256-GCM at the application layer; keys managed via AWS KMS). Sessions in HTTP-only, Secure, SameSite=Lax cookies. CSRF protection on all mutating endpoints. OWASP Top-10 2021 baseline, verified by SAST tooling on every release.
- **Data retention.** Click events: 13 months rolling. Audit fields (`created_at`, `updated_at`): indefinite. Deleted links: soft-delete for 30 days, then hard-delete.

## Out of scope for v1

The following are explicitly **excluded** from v1. They appear in this list so build decisions and architectural choices do not silently include them:

- Billing UI, paid plans, plan selection, seat limits.
- Stripe integration. (Future intention only — see "Future considerations" below for a billing-shape constraint.)
- Multiple Workspaces per user, Workspace switching.
- SSO / SAML / OIDC / Google sign-in.
- Audit logs visible to Admins.
- Custom branded domains.
- A/B testing of Destination URLs.
- Password-protected links.
- Link expiration (per-link TTL).
- Public REST/GraphQL API for programmatic link creation.
- Mobile app (iOS / Android).
- GDPR self-serve data export and delete (handled manually via support in v1).
- Webhooks out to customer systems.
- Roles beyond Admin and Editor.

## Future considerations

Capabilities we plan to address after v1 — listed here only so we don't paint ourselves into a corner.

- **Stripe billing.** Plan/seat model is assumed: one Stripe Customer per Workspace, one Subscription per Workspace, seat = active Member count. v1 schema should make `workspace_id` the canonical billing-grain key.
- **Branded domains.** Will require Workspace-scoped short-code uniqueness instead of global; out-of-scope decision above is final for v1.
- **Public API.** Will require API keys scoped to Workspace.

## Notes

- The platform is web-only for v1 (no mobile app).
- The redirect service is deployed at the edge (POPs world-wide); the dashboard, link API, and Mixpanel forwarder are deployed regionally.
