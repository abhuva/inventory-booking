$ErrorActionPreference = 'Stop'

if (-not $env:ADMIN_EMAIL -or -not $env:ADMIN_PASSWORD) {
  throw 'Set ADMIN_EMAIL and ADMIN_PASSWORD before running this script.'
}

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $docker) {
  $dockerPath = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
  if (-not (Test-Path $dockerPath)) {
    throw 'Docker CLI not found. Start Docker Desktop and make sure docker is on PATH.'
  }
  & $dockerPath compose exec -T `
    -e ADMIN_EMAIL=$env:ADMIN_EMAIL `
    -e ADMIN_PASSWORD=$env:ADMIN_PASSWORD `
    -e ADMIN_DISPLAY_NAME=$env:ADMIN_DISPLAY_NAME `
    backend uv run python -m inventory_booking_api.users.seed_admin
} else {
  docker compose exec -T `
    -e ADMIN_EMAIL=$env:ADMIN_EMAIL `
    -e ADMIN_PASSWORD=$env:ADMIN_PASSWORD `
    -e ADMIN_DISPLAY_NAME=$env:ADMIN_DISPLAY_NAME `
    backend uv run python -m inventory_booking_api.users.seed_admin
}
