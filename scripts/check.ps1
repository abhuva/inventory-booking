$ErrorActionPreference = 'Stop'

uv run --directory .\backend ruff check .
uv run --directory .\backend pytest
npm.cmd --prefix .\frontend run check
npm.cmd --prefix .\frontend run lint
