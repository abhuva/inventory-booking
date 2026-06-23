# Linux Server Access Basics

You do not need to install Linux on your laptop.

The server runs Linux. You connect to it remotely from Windows with SSH:

```powershell
ssh username@server-address
```

After login, the terminal is running commands on the server, not on your laptop.

## What To Ask IT For

- Server hostname or IP address.
- Username.
- Login method: password or SSH key.
- Whether VPN is required.
- Whether the user has `sudo` rights.
- Where project files should live, for example `/srv/inventory-booking`.

## First Safe Test

From Windows PowerShell:

```powershell
ssh username@server-address
```

Then on the server:

```bash
whoami
pwd
ls
docker --version
docker compose version
```

These commands only inspect the environment.

## Minimal Linux Commands

```bash
pwd          # show current directory
ls           # list files
ls -la       # list files including hidden files
cd folder    # enter folder
cd ..        # go one folder up
mkdir name   # create folder
cat file     # print file contents
less file    # read file, press q to quit
nano file    # simple terminal editor
```

Be careful with delete commands:

```bash
rm file
```

Do not use recursive delete commands unless you are certain what they do.

## Likely App Commands Later

These are examples only. We will document the final production commands separately.

```bash
cd /srv/inventory-booking
git pull
docker compose ps
docker compose logs -f
docker compose up -d --build
```

