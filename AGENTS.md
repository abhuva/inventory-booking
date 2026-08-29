# Agent Entry Point

This file is the mandatory starting point for agent work in this repository.

## Startup Protocol

1. Read this file first.
2. Read `README.md` for setup, commands, and current status.
3. Read `ARCHITECTURE.md` before changing backend, frontend, database, or deployment structure.
4. Check `docs/implementation-plan.md` for current phase context before larger changes.
5. Create or update task-specific docs when decisions affect future implementation.
6. Before any production-server work, read `docs/server-operations.md` and
   `docs/production-runbook.md`.

## Project Direction

Build a PostgreSQL-backed FastAPI + SvelteKit web application for internal inventory booking, QR-based item lookup, reservations, checkouts, returns, transfer workflows, and audit history.

Operational state belongs in PostgreSQL. Markdown is documentation only, not source-of-truth application data.

## Branching and Git Workflow

- Do not make direct code changes on `main` for feature work once the initial setup is complete.
- Create a feature branch for every scoped change.
- Do not commit or push changes unless the user explicitly asks for that action.
- Leave completed work uncommitted on its feature branch while implementation or review work may still continue.
- Do not open pull requests automatically.
- Ask the user before creating a pull request.
- Never rewrite history or amend commits unless explicitly requested.

## Quality Gates

For backend changes:

```powershell
uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
```

For frontend changes:

```powershell
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
```

For environment/deployment changes:

```powershell
docker compose config
```

If a tool is unavailable locally, state that clearly in the final response and still validate what can be validated.

## Engineering Rules

- Keep business rules in the FastAPI backend and database constraints, not only in the UI.
- Treat availability and checkout/return logic as high-risk code; add tests before or with implementation.
- Preserve explicit audit/event history for state-changing operations.
- Prefer boring, well-supported dependencies over clever abstractions.
- Keep frontend screens mobile-friendly from the start because QR workflows are phone-first.

## Shell Notes

- Use PowerShell-compatible commands in examples.
- Prefer `rg` for searching and plain text or JSON output for automated inspection.
- Set explicit timeouts for long-running commands.
- Treat server access as read-only unless the user explicitly requests a
  production change.
- Never print, download, replace, or commit the production `.env` or private SSH
  keys.
