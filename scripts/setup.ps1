$ErrorActionPreference = 'Stop'

uv sync --directory .\backend
npm.cmd --prefix .\frontend install

if (-not (Test-Path .\backend\.env)) {
  Copy-Item .\backend\.env.example .\backend\.env
}

if (-not (Test-Path .\frontend\.env)) {
  Copy-Item .\frontend\.env.example .\frontend\.env
}
