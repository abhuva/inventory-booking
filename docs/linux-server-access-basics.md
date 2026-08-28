# Linux Server Access From Windows

This is a short SSH primer for Marc. The complete live-server reference is
`docs/server-operations.md`.

## Connect

From Windows PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\inventory_nica_ed25519" Marc@nica.network
```

SSH password typing shows no dots or cursor movement. Key-based login should not
ask for the server password unless the private key is unavailable or rejected.

After login, the prompt changes to something like:

```text
Marc@nica:~$
```

Commands now run on the server, not the Windows computer. Enter `exit` to close
the connection.

## Application Directory

```bash
cd /opt/docker/inventory
pwd
git status --short --branch
docker compose -f docker-compose.prod.yml ps
```

The live checkout follows `origin/main`. Do not edit source files there; make
changes locally, commit them, and use the manual deployment flow.

## Useful Read-Only Commands

```bash
pwd                                      # current directory
ls -la                                   # files, including hidden names
git log -5 --oneline                     # recent deployed history
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

Use `less filename` to read a non-secret text file; press `q` to quit.

Do not display `.env`, private keys, or credential files. Do not use recursive
delete commands, `docker compose down -v`, database restore commands, or direct
database writes while exploring.

## Run One Remote Command

You do not need an interactive shell for a single check:

```powershell
$serverKey = "$env:USERPROFILE\.ssh\inventory_nica_ed25519"
$statusCommand = "cd /opt/docker/inventory && git status --short --branch"
ssh -i $serverKey Marc@nica.network $statusCommand
```

PowerShell environment variables have no space after the colon. The correct
form is `$env:USERPROFILE`, not `$env: USERPROFILE`.
