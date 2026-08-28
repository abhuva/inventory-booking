# Authenticated QR Scan Feature Plan

## Status

- State: planned next feature
- Target branch: `feature/qr-scan-route`
- Base branch: updated `main` after PR 1 is merged
- Public route: `/qr/[token]`
- Database migration: not expected
- Infrastructure change: not expected

## Goal

A user scans an existing asset QR code with the phone's native camera, opens the
HTTPS link, signs in when necessary, and sees the asset assigned to that label.
An already authenticated user should reach the asset without another login.

Current labels already contain the intended URL shape:

```text
https://inventory.nica.network/qr/<opaque-token>
```

The feature must make those existing labels work without regeneration.

## Current Gap

QR creation, assignment, and authenticated backend resolution already work.
The frontend generates `/qr/<token>` links, but SvelteKit has no matching route.
The result is a frontend `404` before the token reaches the resolver.

The backend endpoint is:

```text
GET /qr-codes/{token}/resolve
```

It intentionally requires an authenticated session. Calling it directly is not
a usable scan experience because it returns JSON and unauthenticated phones
receive `401`.

## Architecture Fitness

| Concern | Current fit | Plan |
| --- | --- | --- |
| QR identity | Good | Keep opaque tokens and existing URLs. |
| Authentication | Good | Reuse secure session and CSRF cookies. |
| Mobile route | Missing | Add focused `/qr/[token]` route. |
| Asset data | Good | Reuse authenticated asset APIs. |
| Server routing | Good | Apache already forwards `/qr/*` to SvelteKit. |
| Operability | Good | No migration or proxy change; use normal deploy. |

The design is intentionally small. It reuses existing APIs and avoids a public
inventory endpoint, a second authentication system, or a separate mobile app.

## Security Decisions

- A QR token identifies a label; it does not authorize access.
- No inventory information is shown before authentication.
- The existing secure, HTTP-only session cookie remains the authority.
- Login happens on the same `/qr/<token>` URL, so no arbitrary return URL or
  open-redirect parameter is needed.
- The frontend must not log QR tokens, credentials, or API response details.
- Invalid and unassigned tokens receive controlled UI states after login.
- Existing login throttling remains in effect.
- State-changing asset actions are outside the first scan page scope.

## User Flows

### Phone Without A Session

```text
camera scans label
  -> browser opens /qr/<token>
  -> page checks GET /auth/me
  -> API returns 401
  -> page shows email/password login
  -> POST /auth/login sets secure cookies
  -> page resolves the original token
  -> page loads and displays the assigned asset
```

The path does not change during login, so refreshing or correcting credentials
does not lose the scanned token.

### Phone With A Valid Session

```text
camera scans label
  -> browser opens /qr/<token>
  -> GET /auth/me succeeds
  -> page resolves token immediately
  -> page displays assigned asset
```

### Expired Session

If an authenticated API request later returns `401`, the page returns to the
login state while retaining the current token. Successful login retries the
resolution and asset load.

## Route State Model

The page should use explicit states instead of independent booleans:

```text
checking-session
login-required
authenticating
resolving
loading-asset
ready
unassigned
not-found
error
```

Expected transitions:

- `checking-session -> login-required` on `401`.
- `checking-session -> resolving` when a session exists.
- `authenticating -> resolving` after successful login.
- `resolving -> not-found` when the QR token does not exist.
- `resolving -> unassigned` when the label has no current asset.
- `resolving -> loading-asset` when an asset ID is returned.
- `loading-asset -> ready` after the full asset record loads.
- authenticated requests returning `401` go back to `login-required`.
- network and server failures go to `error` with a retry action.

## Data Loading

After authentication:

1. Resolve the token with `GET /qr-codes/{token}/resolve`.
2. If assigned, load the full asset with `GET /assets/{asset_id}`.
3. Load the asset image metadata/content when present.
4. Load categories and locations to display names instead of IDs.
5. For stock assets, load and filter stock levels for the resolved asset.
6. Optionally load recent item events for useful field history.

The QR resolver should remain a small identity lookup. The scan page should use
the same asset read model as the main inventory workspace rather than creating a
second, eventually inconsistent QR-specific asset model.

User display names are admin-only through the current user API. The first scan
view should not weaken that rule. For normal users it can show holder state
without exposing an unresolved user identifier. A future audited read model can
add a safe display name if field usage requires it.

## Mobile Asset View

The ready state should be a focused phone layout containing:

- asset photo or a stable placeholder;
- asset name;
- tracked or stock type;
- status and condition;
- current and home location;
- manufacturer and model;
- serial number and asset tag;
- description and notes;
- stock quantities by location for stock assets;
- clear warning treatment for damaged, maintenance, lost, or retired states.

The first version is read-only. It should include:

- refresh;
- logout or account access;
- `Open in inventory` for the complete workspace record.

Controls must remain usable at narrow phone widths and must not reproduce the
desktop tab workspace inside a small viewport.

## Frontend Scope

### Route

Add:

```text
frontend/src/routes/qr/[token]/+page.svelte
```

The route performs browser-side API calls after mount because the current API
client reads browser cookies for CSRF handling. Initial server rendering should
produce a stable loading shell without trying to access `document`.

### API Client

Add a domain client such as:

```text
frontend/src/lib/api/qr.ts
```

It should expose token resolution through the existing typed API helper. Asset,
location, category, image, and stock requests stay in their existing clients.

### Components

Add focused components under a QR domain folder:

```text
frontend/src/lib/components/qr/QrLoginForm.svelte
frontend/src/lib/components/qr/QrAssetView.svelte
frontend/src/lib/components/qr/QrRouteNotice.svelte
```

If practical, extract the current Account login form into a shared component so
login validation and error behavior are not duplicated. Do not couple the QR
route to the full workspace auth state.

### Workspace Deep Link

Support this optional transition:

```text
/?tab=inventory&asset=<asset-id>
```

The root workspace should validate the requested tab and asset after its normal
authenticated data load, then select the inventory tab and asset. Invalid IDs
must fall back safely without breaking workspace startup.

## Backend Scope

No production API behavior or schema change is expected. Keep the resolver
authenticated and preserve its current assigned/unassigned response.

Add or tighten tests only where the existing contract is not explicit:

- unauthenticated resolution returns `401`;
- assigned tracked asset resolves to the correct asset ID;
- assigned stock asset resolves to the correct asset ID;
- unassigned label returns `assigned: false`;
- unknown token returns `404` after authentication;
- deleted target is treated as unassigned.

If implementation reveals that the existing response cannot identify the asset
reliably, stop and review the contract before extending it. Do not make QR
resolution public as a shortcut.

## Implementation Sequence

1. Create `feature/qr-scan-route` from updated `main`.
2. Record baseline backend and frontend quality-gate results.
3. Add the typed QR frontend API client.
4. Add the route state model and authenticated session check.
5. Add the in-place login flow and automatic post-login retry.
6. Resolve the token and load the full asset record.
7. Build the responsive read-only asset view and controlled error states.
8. Add the optional workspace asset deep link.
9. Add missing backend contract tests and frontend checks.
10. Verify locally at desktop and narrow phone viewports.
11. Open a focused pull request; do not mix unrelated inventory work into it.
12. Deploy manually after review and merge.
13. Test an existing production QR with a physical phone camera.

## Validation

Run the standard checks:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
npm.cmd --prefix .\frontend run build
```

Browser verification must cover:

- authenticated desktop request to a real local QR route;
- narrow phone viewport without a session;
- failed login followed by successful login;
- already authenticated phone flow;
- invalid token;
- unassigned label;
- tracked asset;
- stock asset;
- missing image;
- expired session and retry;
- workspace deep link.

Production smoke testing must use an existing label and confirm:

1. the native phone camera recognizes the QR;
2. the HTTPS route returns `200`, not SvelteKit `404`;
3. login succeeds on a phone without a session;
4. the same URL continues to the assigned asset after login;
5. a phone with a valid session skips login;
6. no inventory data appears before authentication.

## Acceptance Criteria

- Existing generated and printed QR codes work without regeneration.
- `/qr/<valid-token>` renders a branded application page with HTTP `200`.
- Unauthenticated users see login and remain on the scanned URL.
- Successful login automatically displays the assigned asset.
- Authenticated users see the asset without another login.
- The displayed asset matches the QR assignment in PostgreSQL.
- Tracked and stock assets have useful phone-readable detail views.
- Invalid and unassigned labels show deliberate, recoverable states.
- Session expiry returns to login without losing the token.
- The QR token alone never reveals protected inventory data.
- No Apache, TLS, Docker volume, or database migration change is required.

## Out Of Scope

- A browser camera scanner inside the application. The phone's native camera is
  sufficient for printed labels.
- Public or anonymous asset pages.
- Offline/PWA scan queues.
- QR targets other than assets.
- Checkout, return, transfer, or damage mutations directly from the scan page.
- Bulk QR printing and label layout changes.

Those workflows can build on this route after the read-only authenticated scan
path proves reliable in production.
