# Portainer deployment

Youtubarr v1 uses **one stack, one Compose service and one container**.

The recommended deployment is the same style as a normal Portainer application stack: open the **Web editor**, paste the supplied Compose YAML and deploy it. Portainer does not need to clone or build the Git repository.

GitHub publishes the container image to:

```text
ghcr.io/fudmonk95/youtubarr:latest
```

The FUSE daemon runs as a process **inside the main `youtubarr` container**. Do not create a separate `youtubarr-fuse` service.

## 1. Host prerequisite

If Docker is inside a Proxmox LXC, confirm `/dev/fuse` exists inside that LXC:

```bash
ls -l /dev/fuse
```

Youtubarr also requires `/mnt/youtubarr` to be a shared bind mount on the Docker host. Run the host installer once:

```bash
git clone https://github.com/Fudmonk95/Youtubarr.git /opt/youtubarr
cd /opt/youtubarr
./scripts/install-host.sh
```

The host installer installs `youtubarr-mount.service` so the shared mount preparation survives reboot.

## 2. Create persistent directories

Recommended DUMB-style paths:

```bash
mkdir -p /mnt/appdata/Youtubarr/{config,library,cache}
chown -R 1001:1001 /mnt/appdata/Youtubarr
```

Use the PUID/PGID appropriate for your own server.

## 3. Create the Portainer stack

Go to:

```text
Portainer -> Stacks -> Add stack -> Web editor
```

Name the stack:

```text
youtubarr
```

Paste the contents of `docker-compose.portainer.yml` from this repository, or use:

```yaml
services:

  youtubarr:
    container_name: youtubarr
    image: ghcr.io/fudmonk95/youtubarr:latest
    restart: unless-stopped
    stop_grace_period: 30s
    init: true

    environment:
      TZ: Europe/London
      PUID: "1001"
      PGID: "1001"
      YOUTUBARR_LOG_LEVEL: INFO
      YOUTUBARR_MAX_VIDEO_HEIGHT: "1080"
      YOUTUBARR_CACHE_MAX_GB: "20"
      YOUTUBARR_CACHE_TTL_HOURS: "24"

    volumes:
      - /mnt/appdata/Youtubarr/config:/config
      - /mnt/appdata/Youtubarr/library:/library
      - /mnt/appdata/Youtubarr/cache:/cache

      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rshared

    ports:
      - "8788:8788"

    devices:
      - /dev/fuse:/dev/fuse:rwm

    cap_add:
      - SYS_ADMIN

    security_opt:
      - apparmor:unconfined

    networks:
      - dumb-live-network

networks:

  dumb-live-network:
    external: true
    name: dumb-live_default
```

The external `dumb-live_default` network is optional. It is useful when Youtubarr should communicate with services reachable through the existing DUMB network. Remove the `networks:` sections if your installation does not have that network.

## 4. Confirm the deployment

Portainer should show one container only:

```text
youtubarr
```

Then open:

```text
http://YOUR-SERVER-IP:8788
```

Complete the first-run wizard to create the administrator and connect Sonarr, Lidarr and optional Radarr.

## 5. DUMB / Jellyfin symlink visibility

Youtubarr library entries are real Linux symlinks whose targets live under `/mnt/youtubarr`.

Any container that needs to follow those symlinks must therefore see `/mnt/youtubarr` at that exact absolute path.

For a DUMB container, add this volume to the DUMB stack:

```yaml
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rslave
```

`rslave` is intentional for consumers: they receive Youtubarr's nested FUSE mount but cannot propagate their own mount changes back to the host.

If the Youtubarr library itself also needs to be visible inside DUMB/Jellyfin, either bind it directly or place it under a host path already mounted into DUMB.

Example direct bind:

```yaml
      - /mnt/appdata/Youtubarr/library:/youtube-library:ro
```

## 6. Diagnostics

```bash
cd /opt/youtubarr
./scripts/doctor.sh
```

Expected healthy state after deployment:

```text
[OK] /dev/fuse exists
[OK] /mnt/youtubarr propagation is shared
[OK] Compose contains exactly one service/container
[OK] Youtubarr container is running
[OK] Youtubarr FUSE marker is visible on the host
[OK] Youtubarr web API responds
```

Use the main README for setup, root mapping, DUMB/Zurg architecture and troubleshooting.
