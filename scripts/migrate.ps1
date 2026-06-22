$ErrorActionPreference = 'Stop'

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $docker) {
  $dockerPath = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
  if (-not (Test-Path $dockerPath)) {
    throw 'Docker CLI not found. Start Docker Desktop and make sure docker is on PATH.'
  }
  & $dockerPath compose exec -T backend uv run alembic upgrade head
} else {
  docker compose exec -T backend uv run alembic upgrade head
}
