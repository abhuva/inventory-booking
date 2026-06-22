# Security Review Workflow

## Baseline Threats

Review every API/database change against these risks:

- unauthenticated access to protected endpoints
- unauthorized mutation by a normal user
- admin-only action reachable by user role
- booking conflict bypass
- stock quantity underflow or overbooking
- SQL injection through filters/search/sort parameters
- mass assignment of protected fields
- insecure direct object reference between users/resources
- CSRF on browser-triggered mutations
- stored XSS in notes, names, descriptions, or event text
- secrets or tokens in logs
- destructive actions without audit events

## Required Review For New Endpoints

- [ ] Endpoint requires authentication unless explicitly public.
- [ ] Authorization rule is documented in router or service tests.
- [ ] Browser mutation endpoints enforce CSRF protection.
- [ ] Request schema rejects unexpected fields where needed.
- [ ] Service validates state transitions server-side.
- [ ] Mutation writes audit/event records.
- [ ] Tests include at least one invalid/malicious request.
- [ ] No raw SQL is built from user-controlled strings.
- [ ] Errors do not leak secrets or stack traces.

## Automated Checks Target

Backend:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

Frontend:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
npm.cmd --prefix .\frontend audit --audit-level=moderate
```

Planned additions:

- Python dependency audit
- Semgrep or Bandit for security-oriented static checks
- API abuse tests for auth, permissions, booking conflicts, stock underflow, and admin overrides
