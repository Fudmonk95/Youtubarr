# Youtubarr

**YouTube acquisition for an Arr-managed media library.**

Youtubarr is a self-hosted companion for **Sonarr**, **Lidarr** and optional **Radarr**. It is designed to look and operate like another application in the Arr family while using YouTube as an additional source for media that is difficult to obtain through normal torrent or Usenet workflows.

The interface deliberately follows the familiar Arr information architecture: poster libraries, `Add New`, `Library Import`, `Calendar`, `Activity`, `Wanted`, Arr-style settings pages, root mappings, queues, history and system status. The visual identity is different on purpose: **YouTube red** is used for the top/action chrome and Youtubarr branding.

> Youtubarr does not replace Sonarr, Lidarr or Radarr. Those applications remain the source of truth for media identity, metadata, monitoring state, seasons, episodes, albums, tracks, filenames and library paths.

## What Youtubarr is for

Youtubarr is aimed mainly at **older television series and music** that are already known to Sonarr or Lidarr but are difficult to source elsewhere. Movies are optional and disabled by default.

Typical workflow:

```text
Sonarr says S01E03 is missing
        ↓
Youtubarr reads the Sonarr metadata
        ↓
Interactive YouTube search / playlist mapping
        ↓
Choose a suitable YouTube source
        ↓
Youtubarr creates a virtual media asset through FUSE
        ↓
A normal Linux symlink is placed in the mapped Youtubarr library
        ↓
Jellyfin / Sonarr / Lidarr can access the media through the shared mount
```

Youtubarr supports both common YouTube delivery patterns:

- a progressive stream containing video and audio;
- separate video and audio streams, remuxed with `ffmpeg` into a bounded transient cache when required;
- audio-focused sources for Lidarr/music;
- seekable byte-range reads through the FUSE filesystem;
- Linux symlink library entries rather than permanent duplicate media downloads.

## What is different from the other YouTube/Arr projects

Several existing community projects, including the supplied `yt2radarr` and other Youtubarr-style builds, helped demonstrate that YouTube can be bridged into an Arr workflow. This project is intentionally broader in scope.

Youtubarr is designed around these goals:

- **Arr-style application rather than a downloader wrapper.** The main UI follows Sonarr/Lidarr navigation and workflow patterns.
- **Series and music are first-class.** Sonarr and Lidarr are both core integrations.
- **Movies are optional.** The Movies navigation and Radarr setup are hidden when the feature is disabled.
- **Arr metadata remains authoritative.** Youtubarr does not build a competing metadata database for shows, episodes, artists or albums.
- **Wanted workflow.** Missing items are grouped around their Arr media so series/season context is visible before searching.
- **Activity workflow.** Queue, History and Blocklist expose Youtubarr acquisitions in an Arr-like layout.
- **Target-aware YouTube search.** Episode searches include the Sonarr series title, `SxxEyy` token and episode title instead of relying on a loose title-only query.
- **Manual URL acquisition.** A specific YouTube video URL can be pasted directly against a selected missing episode, track or movie.
- **Playlist mapping.** A YouTube playlist can be associated with a Sonarr season or Lidarr album even when the video titles are unhelpful (`Episode 1`, `Episode 2`, and so on).
- **Virtual filesystem delivery.** The target architecture is a single Youtubarr container running the API, UI, resolver, ffmpeg and FUSE process together.
- **Persistent symlink library.** Library entries point into the Youtubarr virtual mount and can be exposed to Jellyfin and the Arr applications.
- **Portainer-first deployment.** The published GHCR image can be deployed from the normal Portainer Web Editor without cloning/building the repository on the server.

## Interface

The Youtubarr v1 interface follows the same navigation model used by Sonarr/Lidarr, with YouTube-red branding.

### Series

```text
Series
├─ Add New
└─ Library Import
```

The Series page supports an Arr-style poster grid and toolbar actions such as:

- Update Filtered
- RSS Sync
- Select Series
- Test Parsing
- Options
- View
- Sort
- Filter

Series and episode information is loaded from Sonarr, including available poster metadata where Sonarr exposes it.

Open a series to view its Sonarr seasons and episodes. Missing episodes expose a YouTube search button. The query is built from the **series title + SxxEyy + episode title**, and the result page also accepts a manually pasted YouTube video URL.

### Activity

```text
Activity
├─ Queue
├─ History
└─ Blocklist
```

### Wanted

```text
Wanted
├─ Missing
└─ Cutoff Unmet
```

For Sonarr, Missing groups episodes by series and shows the series poster, series title, affected seasons and individual episode rows. Each row can be handed directly to Youtubarr's interactive YouTube search.

### Settings

```text
Settings
├─ Media Management
├─ Profiles
├─ Quality
├─ Custom Formats
├─ Indexers
├─ Download Clients
├─ Import Lists
├─ Connect
├─ Metadata
├─ Metadata Source
├─ Tags
├─ General
└─ UI
```

Youtubarr does not pretend to own settings that properly belong to Sonarr/Lidarr/Radarr. Where appropriate, these pages explain or expose the Youtubarr equivalent while retaining the familiar Arr layout.

### YouTube playlist mapping

Open **Settings → Import Lists**.

For a TV playlist:

1. Select **Series / Sonarr**.
2. Choose the Sonarr series.
3. Choose the season.
4. Paste the YouTube playlist URL.
5. Leave **Only missing targets** enabled if existing Sonarr files should be skipped.
6. Click **Load & Preview Playlist**.
7. Review the ordered mapping.
8. Select the mappings you want and click **Queue Selected Mappings**.

Example:

```text
YouTube playlist item 1  →  Jeopardy S01E01
YouTube playlist item 2  →  Jeopardy S01E02
YouTube playlist item 3  →  Jeopardy S01E03
...
```

The YouTube video titles do not need to contain valid Sonarr episode tokens when ordered playlist mapping is used. Sonarr supplies the canonical episode identity, name, season/episode number and destination path.

For music, select **Music / Lidarr**, choose the artist and album, load the YouTube playlist and preview the playlist-position → Lidarr-track mapping before queuing it.

A playlist can also be started from a series detail page with **Import Playlist**.

### System

```text
System
├─ Status
├─ Tasks
├─ Logs
├─ Updates
└─ Backup
```

---

# Recommended deployment: Portainer Web Editor

The recommended installation method is:

**Portainer → Stacks → Add stack → Web editor → paste Compose → Deploy the stack**

Portainer does **not** need to clone this repository and does **not** need to build Youtubarr locally. GitHub Actions publishes the image to:

```text
ghcr.io/fudmonk95/youtubarr:latest
```

Youtubarr runs as **one stack and one container**.

```text
Youtubarr container
├─ FastAPI backend
├─ Arr integrations
├─ web UI
├─ yt-dlp
├─ ffmpeg / ffprobe
├─ acquisition worker
└─ FUSE filesystem
```

There is no Youtubarr FUSE sidecar container.

## Requirements

The Docker host must provide:

- Docker / Portainer;
- `/dev/fuse`;
- permission for the container to use FUSE (`SYS_ADMIN` and unconfined AppArmor in the supplied Compose);
- a host mount point at `/mnt/youtubarr` with **shared mount propagation**;
- persistent directories for configuration, generated library symlinks and transient cache;
- network connectivity to Sonarr and Lidarr, and optionally Radarr.

The supplied setup uses:

```text
/mnt/appdata/Youtubarr/config
/mnt/appdata/Youtubarr/library
/mnt/appdata/Youtubarr/cache
/mnt/youtubarr
```

## 1. Prepare persistent directories

On the Debian/Docker host:

```bash
mkdir -p /mnt/appdata/Youtubarr/{config,library,cache}
chown -R 1001:1001 /mnt/appdata/Youtubarr
```

Adjust PUID/PGID if your environment uses a different account.

## 2. Prepare `/mnt/youtubarr` for FUSE propagation

The host path must be a shared mount so the nested FUSE filesystem created by the container is visible back on the host.

The repository contains host-preparation helpers under `scripts/`. When the repository is available at `/opt/youtubarr`:

```bash
cd /opt/youtubarr
chmod +x scripts/*.sh
./scripts/install-host.sh
```

Verify:

```bash
systemctl status youtubarr-mount.service --no-pager
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION /mnt/youtubarr
```

Before the Youtubarr container starts, the important result is:

```text
/mnt/youtubarr ... ext4 ... shared
```

After Youtubarr starts, there should be a FUSE layer above it:

```text
/mnt/youtubarr ... ext4         shared
/mnt/youtubarr YoutubarrFS fuse shared
```

Do not create a separate FUSE container.

## 3. Portainer stack

In Portainer:

1. Open **Stacks**.
2. Choose **Add stack**.
3. Enter a name such as `youtubarr`.
4. Choose **Web editor**.
5. Paste the following Compose.
6. Click **Deploy the stack**.

```yaml
services:

  youtubarr:
    container_name: youtubarr
    image: ghcr.io/fudmonk95/youtubarr:latest
    restart: unless-stopped
    stop_grace_period: 30s

    volumes:
      - /mnt/appdata/Youtubarr/config:/config
      - /mnt/appdata/Youtubarr/library:/library
      - /mnt/appdata/Youtubarr/cache:/cache

      # Youtubarr creates its FUSE filesystem inside this single container.
      # rshared propagates the nested mount back to the Debian/LXC host.
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rshared

    environment:
      TZ: Europe/London
      PUID: "1001"
      PGID: "1001"
      YOUTUBARR_LOG_LEVEL: INFO
      YOUTUBARR_MAX_VIDEO_HEIGHT: "1080"
      YOUTUBARR_CACHE_MAX_GB: "20"
      YOUTUBARR_CACHE_TTL_HOURS: "24"

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

If you do not use the `dumb-live_default` network, replace that network section with your own existing Docker network or remove it and use normal IP/hostname connectivity.

## 4. DUMB / Jellyfin / Arr access to the Youtubarr mount

When Sonarr, Lidarr and Jellyfin run inside a DUMB container, DUMB must be able to see both the generated Youtubarr library and the nested Youtubarr FUSE mount.

Add these volumes to the existing `DUMB` service:

```yaml
      # Receive Youtubarr's nested FUSE mount.
      # rslave receives mount events from the host without propagating DUMB's
      # own mount events back into Youtubarr.
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rslave

      # Expose Youtubarr's generated symlink library.
      - /mnt/appdata/Youtubarr/library:/youtube-library
```

The intended path flow is:

```text
/youtube-library/tv/Example Show/Season 01/Example Show - S01E01.mp4
                   ↓ Linux symlink
/mnt/youtubarr/tv/<asset-id>.mp4
                   ↓ FUSE
YouTube source
```

## 5. Verify container and FUSE state

After deployment:

```bash
docker ps --filter "name=youtubarr"
findmnt -R -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
docker logs --tail=100 youtubarr
```

Expected container state: `Up ... (healthy)`.

---

# First-run setup

Open `http://YOUR_DOCKER_HOST:8788`.

A fresh configuration does not use default credentials. The setup wizard asks you to create the administrator account, select media modules, connect the Arr applications and generate root mappings.

Defaults:

```text
Series  ON
Music   ON
Movies  OFF
```

When Youtubarr and DUMB share `dumb-live_default`, typical service URLs are:

```text
Sonarr: http://DUMB-live:8989
Lidarr: http://DUMB-live:8686
Radarr: http://DUMB-live:7878
```

# Interactive YouTube acquisition

For an individual missing episode:

1. Open **Series** and choose the series, or use **Wanted → Missing**.
2. Click the magnifying-glass button beside the missing episode.
3. Youtubarr searches with the series/episode context.
4. Review the YouTube title, channel, duration and match indicator.
5. Click **Grab** on the selected result.

If you already know the correct source, paste its YouTube URL into **Or paste a YouTube video URL** and click **Grab URL**.

The acquisition then appears under **Activity → Queue** and later **History** or **Blocklist**.

---

# Updating Youtubarr

```bash
docker pull ghcr.io/fudmonk95/youtubarr:latest
```

Then use **Portainer → Stacks → youtubarr → Editor → Update the stack**. If Portainer has trouble pulling a public GHCR image with stored credentials, pull the image from Docker on the host first and redeploy without forcing Portainer to re-pull it.

Persistent data remains in `/mnt/appdata/Youtubarr`.

# Diagnostics

```bash
docker ps --filter "name=youtubarr"
docker logs --tail=200 youtubarr
ls -l /dev/fuse
findmnt -R -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
```

When the repo exists at `/opt/youtubarr`:

```bash
cd /opt/youtubarr
./scripts/doctor.sh
```

# Security

- No baked-in default administrator credentials.
- Arr API keys are stored encrypted in persistent configuration.
- Do not commit live `/config`, databases, credentials or API keys.
- Use normal authentication/reverse-proxy protections if exposing Youtubarr remotely.

# Development validation

```bash
PYTHONPATH=backend pytest -q
python -m compileall -q backend/youtubarr
node --check backend/youtubarr/web/assets/app.js
node --check backend/youtubarr/web/assets/app-arr-shell.js
node --check backend/youtubarr/web/assets/app-arr-pages.js
node --check backend/youtubarr/web/assets/app-youtube-fixes.js
```

# Licence

See `LICENSE`.
