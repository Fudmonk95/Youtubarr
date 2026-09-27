# Youtubarr

**YouTube acquisition for an Arr-managed media library.**

Youtubarr is a self-hosted companion for **Sonarr**, **Lidarr** and optional **Radarr**. It is designed to look and operate like another application in the Arr family while using YouTube as an additional source for media that is difficult to obtain through normal torrent or Usenet workflows.

The interface follows the familiar Arr information architecture: poster libraries, `Add New`, `Library Import`, `Calendar`, `Activity`, `Wanted`, Arr-style settings pages, root mappings, queues, history and system status. The visual identity is intentionally different: **YouTube red** is used for the top/action chrome and Youtubarr branding.

> Sonarr, Lidarr and Radarr remain authoritative for media identity, metadata, monitoring, seasons, episodes, albums, tracks and normal Arr state. Youtubarr additionally tracks whether it has successfully created a verified virtual file of its own.

## What Youtubarr is for

Youtubarr is aimed mainly at **older television series and music** that are already known to Sonarr or Lidarr but are difficult to source elsewhere. Movies are optional and disabled by default.

Typical workflow:

```text
Sonarr says S01E03 is missing
        ↓
Youtubarr reads Sonarr metadata
        ↓
Interactive YouTube search / playlist mapping
        ↓
Choose a suitable YouTube source
        ↓
Youtubarr creates a virtual media asset through FUSE
        ↓
A Linux symlink is placed in the mapped Youtubarr library
        ↓
Jellyfin / Sonarr / Lidarr can access the media through the shared mount
```

Youtubarr supports:

- progressive video streams containing video and audio;
- separate video/audio streams remuxed through a bounded transient cache when required;
- audio-focused sources for Lidarr/music;
- seekable byte-range reads through the FUSE filesystem;
- Linux symlink library entries instead of permanent duplicate media downloads;
- individual target-aware YouTube search;
- direct YouTube URL acquisition;
- ordered YouTube playlist mapping to Sonarr seasons and Lidarr albums.

## Availability states

Youtubarr v1.0.4 no longer treats the connected Arr application's `hasFile` flag as the only source of truth for the Youtubarr interface.

A media item can now be shown as:

```text
Missing
Found by Youtubarr
Registered
```

**Missing** means neither the Arr app nor Youtubarr has a usable file.

**Found by Youtubarr** means a Youtubarr acquisition completed and its library symlink still resolves to a live FUSE asset. The item is therefore usable by Jellyfin even if Sonarr/Lidarr has not rescanned or registered it yet.

**Registered** means the connected Arr application itself reports `hasFile=true`.

Completed and verified Youtubarr media is removed from Youtubarr's **Wanted → Missing** view immediately. This avoids repeatedly searching for media Youtubarr already has while still keeping the difference between local Youtubarr availability and Arr registration visible.

## What is different from other YouTube/Arr projects

Youtubarr is designed around these goals:

- **Arr-style application rather than a downloader wrapper.**
- **Series and music are first-class.** Sonarr and Lidarr are core integrations.
- **Movies are optional.** Radarr/Movies is hidden when disabled.
- **Arr metadata remains authoritative.**
- **Wanted workflow** with series/season context and poster artwork.
- **Activity workflow** with Queue, History and Blocklist.
- **Target-aware YouTube search** using series title + `SxxEyy` + episode title.
- **Manual URL acquisition** for a known YouTube source.
- **Playlist mapping** for Sonarr seasons and Lidarr albums, including playlists with generic titles such as `Episode 1`.
- **Virtual filesystem delivery** from one Youtubarr container.
- **Persistent symlink library** pointing into `/mnt/youtubarr`.
- **Verified local availability overlay** so completed Youtubarr media is not shown as missing while Arr catches up.
- **Portainer-first deployment** using the published GHCR image.

# Interface

## Series

```text
Series
├─ Add New
└─ Library Import
```

The Series page uses an Arr-style poster grid and toolbar including:

- Update Filtered
- RSS Sync
- Select Series
- Test Parsing
- Options
- View
- Sort
- Filter

Open a series to view its Sonarr seasons and episodes. Missing episodes expose a YouTube search button. Completed Youtubarr episodes display **Found by Youtubarr** and count as present in the Youtubarr season total. Once Sonarr registers them they display **Registered**.

## Music

Music uses Lidarr metadata. Album track tables use the same availability model:

- Missing
- Found by Youtubarr
- Registered

A missing track can be searched individually or mapped from a YouTube playlist.

## Activity

```text
Activity
├─ Queue
├─ History
└─ Blocklist
```

## Wanted

```text
Wanted
├─ Missing
└─ Cutoff Unmet
```

For Sonarr, Missing groups episodes by series and shows poster artwork, series title, affected seasons and episode rows. Media with a verified completed Youtubarr acquisition is excluded from Missing even before Sonarr updates its own `hasFile` state.

## Settings

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

## YouTube playlist mapping

Open **Settings → Import Lists**.

For TV:

1. Select **Series / Sonarr**.
2. Choose the Sonarr series.
3. Choose the season.
4. Paste the YouTube playlist URL.
5. Leave **Only missing targets** enabled if existing media should be skipped.
6. Click **Load & Preview Playlist**.
7. Review the ordered mapping.
8. Select the desired mappings.
9. Click **Queue Selected Mappings**.

Example:

```text
YouTube item 1  →  Jeopardy S01E01
YouTube item 2  →  Jeopardy S01E02
YouTube item 3  →  Jeopardy S01E03
...
```

For music, select **Music / Lidarr**, choose the artist and album, load the YouTube playlist, review playlist-position → Lidarr-track mapping, and queue the selected tracks.

# Recommended deployment: Portainer Web Editor

The recommended installation method is:

**Portainer → Stacks → Add stack → Web editor → paste Compose → Deploy the stack**

Portainer does not need to clone this repository or build Youtubarr locally. GitHub Actions publishes:

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
├─ acquisition workers
└─ FUSE filesystem
```

There is no Youtubarr FUSE sidecar.

## Requirements

The Docker host must provide:

- Docker / Portainer;
- `/dev/fuse`;
- `SYS_ADMIN` and unconfined AppArmor for the Youtubarr container;
- `/mnt/youtubarr` with **shared mount propagation**;
- persistent config/library/cache directories;
- network connectivity to Sonarr and Lidarr, and optionally Radarr.

The example uses:

```text
/mnt/appdata/Youtubarr/config
/mnt/appdata/Youtubarr/library
/mnt/appdata/Youtubarr/cache
/mnt/youtubarr
```

## 1. Prepare persistent directories

```bash
mkdir -p /mnt/appdata/Youtubarr/{config,library,cache}
chown -R 1001:1001 /mnt/appdata/Youtubarr
```

The container repairs `/library` permissions at startup, so no host ACL package is required for the normal deployment.

## 2. Prepare `/mnt/youtubarr`

The path must be a shared mount so the nested FUSE filesystem created inside Youtubarr propagates back to the Docker/LXC host.

When the repo is available at `/opt/youtubarr`:

```bash
cd /opt/youtubarr
chmod +x scripts/*.sh
./scripts/install-host.sh
```

Verify before container startup:

```bash
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION /mnt/youtubarr
```

Expected backing mount:

```text
/mnt/youtubarr ... ext4 ... shared
```

After Youtubarr starts:

```text
/mnt/youtubarr ... ext4           shared
/mnt/youtubarr YoutubarrFS fuse  shared
```

## 3. Portainer stack

In Portainer choose **Stacks → Add stack → Web editor** and paste:

```yaml
services:

  youtubarr:
    container_name: youtubarr
    image: ghcr.io/fudmonk95/youtubarr:latest
    restart: unless-stopped
    stop_grace_period: 30s

    environment:
      TZ: Europe/London

      # Youtubarr's library owner
      PUID: "1001"
      PGID: "1001"

      # Sonarr / Lidarr / Radarr user/group inside DUMB
      ARR_UID: "1000"
      ARR_GID: "1000"

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

### PUID/PGID versus ARR_UID/ARR_GID

These values serve different purposes.

```text
PUID / PGID       owner identity used by Youtubarr
ARR_UID / ARR_GID user/group used by Sonarr/Lidarr/Radarr
```

On the documented DUMB setup:

```text
Youtubarr: 1001:1001
Arr user:   1000:1000 (ubuntu)
```

At every startup Youtubarr repairs the complete `/library` tree. Directories become group `ARR_GID` with mode `2775`; regular files become `0664`; Youtubarr symlinks remain symlinks and only their link ownership is adjusted. New directories are also repaired when Youtubarr creates media paths.

The setgid directory bit ensures newly-created child folders inherit the Arr group. This applies across:

```text
/library/tv
/library/music
/library/movies
```

and every mapped subfolder beneath them.

`/mnt/youtubarr` itself remains a read-only FUSE filesystem. Arr applications and Jellyfin only need to read those virtual targets; the writable area is the symlink library.

## 4. DUMB / Jellyfin / Arr access

When Sonarr, Lidarr and Jellyfin run inside DUMB, add these mounts to the existing DUMB service:

```yaml
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rslave

      - /mnt/appdata/Youtubarr/library:/youtube-library
```

The intended path flow is:

```text
/youtube-library/tv/Example Show/Season 01/Example Show - S01E01.mp4
                   ↓ symlink
/mnt/youtubarr/tv/<asset-id>.mp4
                   ↓ FUSE
YouTube
```

The equivalent generated roots are:

```text
/youtube-library/tv      → Sonarr
/youtube-library/music   → Lidarr
/youtube-library/movies  → optional Radarr
```

## 5. Verify container and FUSE state

```bash
docker ps --filter "name=youtubarr"
findmnt -R -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
docker logs --tail=100 youtubarr
```

Expected container state: `Up ... (healthy)`.

To verify the shared library as the Arr user in DUMB:

```bash
docker exec -u ubuntu DUMB-live sh -lc '
  id
  touch /youtube-library/tv/.arr-write-test
  rm -f /youtube-library/tv/.arr-write-test
  touch /youtube-library/music/.arr-write-test
  rm -f /youtube-library/music/.arr-write-test
'
```

# First-run setup

Open:

```text
http://YOUR_DOCKER_HOST:8788
```

A fresh install asks you to:

1. create an administrator username/password;
2. enable Series and/or Music;
3. optionally enable Movies;
4. connect Sonarr/Lidarr/optional Radarr;
5. generate root mappings.

Defaults:

```text
Series  ON
Music   ON
Movies  OFF
```

When Youtubarr and DUMB share `dumb-live_default`:

```text
Sonarr: http://DUMB-live:8989
Lidarr: http://DUMB-live:8686
Radarr: http://DUMB-live:7878
```

# Interactive YouTube acquisition

For an individual missing episode:

1. Open **Series** or **Wanted → Missing**.
2. Click the magnifying-glass button beside the episode.
3. Youtubarr searches with series + season/episode + episode title context.
4. Review the result title/channel/duration/match score.
5. Click **Grab**.

Or paste a known YouTube URL into **Or paste a YouTube video URL** and click **Grab URL**.

The acquisition appears under **Activity → Queue**, then **History** when the FUSE asset and symlink are complete.

# Arr registration

Youtubarr's local availability and Arr registration are intentionally separate.

A completed virtual media file is immediately shown as **Found by Youtubarr** and removed from Youtubarr Wanted/Missing. To have Sonarr/Lidarr display it as one of their own files, the corresponding `/youtube-library/...` root/path must also be visible and configured in that Arr application, then scanned/imported according to that Arr application's normal workflow.

This distinction prevents Youtubarr from incorrectly claiming that Sonarr/Lidarr registered a file when only the Youtubarr/Jellyfin path is known to work.

# Updating Youtubarr

```bash
docker pull ghcr.io/fudmonk95/youtubarr:latest
```

Then use **Portainer → Stacks → youtubarr → Editor → Update the stack**. If Portainer has trouble pulling the public GHCR image with stored credentials, pull on the Docker host first and redeploy without forcing Portainer to re-pull.

Persistent data remains under `/mnt/appdata/Youtubarr`.

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
node --check backend/youtubarr/web/assets/app-availability.js
```

# Licence

See `LICENSE`.
