# Portainer deployment

Youtubarr v1 uses **one stack, one Compose service and one container**.

The FUSE daemon runs as a process inside the main `youtubarr` container. Do not create a separate `youtubarr-fuse` service.

## 1. Host prerequisite

If Docker is inside a Proxmox LXC, confirm `/dev/fuse` exists inside that LXC:

```bash
ls -l /dev/fuse
```

If it is missing, fix the LXC from the Proxmox host first. `pct` commands do not run inside the Debian LXC.

## 2. Clone once for host preparation

```bash
sudo git clone https://github.com/Fudmonk95/Youtubarr.git /opt/youtubarr
cd /opt/youtubarr
sudo ./scripts/install-host.sh
```

This prepares `/mnt/youtubarr` as a shared bind and installs the boot-time systemd unit.

## 3. Create persistent data folders

```bash
sudo mkdir -p /opt/youtubarr-data/{config,library,cache}
sudo chown -R 1000:1000 /opt/youtubarr-data
```

Use your own PUID/PGID if different.

## 4. Add the Portainer Git stack

- Stack name: `youtubarr`
- Build method: Git repository
- Repository URL: `https://github.com/Fudmonk95/Youtubarr.git`
- Reference: `refs/heads/main`
- Compose path: `docker-compose.yml`

Recommended environment variables:

```env
TZ=Europe/London
PUID=1000
PGID=1000
YOUTUBARR_PORT=8788
BIND_ADDRESS=0.0.0.0
YOUTUBARR_CONFIG_DIR=/opt/youtubarr-data/config
YOUTUBARR_LIBRARY_DIR=/opt/youtubarr-data/library
YOUTUBARR_CACHE_DIR=/opt/youtubarr-data/cache
YOUTUBARR_MOUNT_DIR=/mnt/youtubarr
YOUTUBARR_MAX_VIDEO_HEIGHT=1080
YOUTUBARR_CACHE_MAX_GB=20
YOUTUBARR_CACHE_TTL_HOURS=24
YOUTUBARR_LOG_LEVEL=INFO
```

Deploy the stack.

## 5. Confirm the deployment

Portainer should show one container only:

```text
youtubarr
```

Then open:

```text
http://YOUR-SERVER-IP:8788
```

Complete the first-run wizard to create the user and connect Sonarr/Lidarr/optional Radarr.

## 6. Media-server requirement

Your media server must see both the exported Youtubarr library and `/mnt/youtubarr` at that exact absolute path so the Linux symlinks resolve.

Example Jellyfin additions:

```yaml
volumes:
  - /opt/youtubarr-data/library:/youtube-library:ro
  - /mnt/youtubarr:/mnt/youtubarr:ro,rslave
```

## 7. Diagnostics

```bash
cd /opt/youtubarr
sudo ./scripts/doctor.sh
```

Use the main README for the full setup, root-mapping, DUMB/Zurg and troubleshooting guide.
