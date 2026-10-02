# Youtubarr

**YouTube acquisition for an Arr-managed media library.**

Youtubarr is a self-hosted companion for **Sonarr**, **Lidarr** and optional **Radarr**. It is designed to feel like another Arr application while using YouTube as an additional source for old, rare or otherwise difficult-to-find media.

The interface follows familiar Arr patterns: poster libraries, `Add New`, `Library Import`, `Calendar`, `Activity`, `Wanted`, Arr-style settings pages, queues, history and system status. Youtubarr uses **YouTube red** for its own identity while preserving the general Arr information architecture.

> Sonarr, Lidarr and Radarr remain authoritative for media identity, metadata, monitoring, seasons, episodes, albums and tracks. Youtubarr additionally tracks whether it has successfully created a verified virtual media file of its own.

## Current release

```text
v1.0.7
```

Highlights in v1.0.7:

- Arr-style toolbar menus are mutually exclusive: opening `View`, `Sort`, `Options` or `Filter` closes the previous menu.
- Series poster cards show a real episode-availability progress bar instead of the old monitored-corner marker.
- Season headers show a Sonarr-style count and progress bar.
- Progress includes both Arr-registered files and verified Youtubarr files.
- Series-level and season-level YouTube playlist hard search.
- `Use Playlist` carries the selected series, season scope and playlist URL into Import Lists.
- `All Seasons (x-y)` mapping for complete-series playlists.
- Youtubarr library permissions are repaired on every container start for Sonarr/Lidarr/Radarr access.

# What Youtubarr is for

Youtubarr is aimed mainly at **series and music** already known to Sonarr or Lidarr but difficult to source through normal torrent or Usenet workflows. Movies are optional and disabled by default.

Typical flow:

```text
Sonarr reports an episode missing
        ↓
Youtubarr reads Sonarr metadata
        ↓
Search YouTube / search playlists / paste a URL
        ↓
Choose or map a source
        ↓
Youtubarr creates a virtual media asset through FUSE
        ↓
A Linux symlink is created in the Youtubarr library
        ↓
Jellyfin / Sonarr / Lidarr read the media through the shared mount
```

Youtubarr supports:

- progressive YouTube formats containing audio and video;
- separate video/audio streams through a bounded transient remux cache where needed;
- audio-focused sources for Lidarr;
- seekable byte-range reads through the FUSE filesystem;
- Linux symlink library entries instead of permanently duplicating media;
- individual target-aware YouTube searches;
- direct YouTube URL acquisition;
- ordered playlist mapping to Sonarr episodes and Lidarr tracks;
- complete-series playlist mapping across multiple seasons;
- series/season playlist hard search;
- verified local availability independent of Arr registration state.

# Availability states

Youtubarr does not rely only on the connected Arr application's `hasFile` flag.

An episode/track/movie can be shown as:

```text
Missing
Found by Youtubarr
Registered
```

**Missing** means neither the Arr application nor Youtubarr has a usable file.

**Found by Youtubarr** means a Youtubarr acquisition completed and its library symlink still resolves to a live FUSE asset. Jellyfin can use the media even if Sonarr/Lidarr has not registered it yet.

**Registered** means the connected Arr application itself reports the file as present.

Verified Youtubarr media is removed from **Wanted → Missing** so Youtubarr does not repeatedly search for content it already has.

## Progress bars

Series poster cards and season headers use the combined Youtubarr view.

Example:

```text
Sonarr registered:      0 / 13
Youtubarr verified:    13 / 13
Youtubarr UI progress: 13 / 13
```

Youtubarr preserves Sonarr's original count separately and does not write fake values back to Sonarr.

# Interface

## Series

```text
Series
├─ Add New
└─ Library Import
```

The Series toolbar includes:

- Update Filtered
- RSS Sync
- Select Series
- Test Parsing
- Options
- View
- Sort
- Filter

Only one toolbar popover is displayed at a time. Clicking elsewhere or pressing `Escape` closes it.

Poster cards show a horizontal availability bar at the bottom of the artwork plus an `available / total` count. The old red monitored corner is not used as a progress indicator.

Open a series to see seasons and episodes. Every season shows:

```text
Season 1       13 / 13
████████████████████
```

The count treats both **Registered** and **Found by Youtubarr** episodes as available.

## Series playlist hard search

From a series page use **Search Playlists** to search YouTube specifically for playlists for the whole programme.

Each season also has a playlist-search button for a season-specific search.

Examples:

```text
Wolfblood full series complete episodes playlist
Wolfblood season 3 full episodes playlist
```

Search results can be opened on YouTube or sent directly into Import Lists with **Use Playlist**.

When `Use Playlist` is selected, Youtubarr carries:

- the Sonarr series;
- `All Seasons` or the selected season;
- the playlist URL.

into the playlist mapper automatically.

## Music

Music uses Lidarr metadata and the same availability model:

```text
Missing
Found by Youtubarr
Registered
```

Tracks can be searched individually or mapped from a YouTube playlist.

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

For Sonarr, Missing groups episodes by series and displays poster artwork, series title, season/episode information and search actions.

Verified Youtubarr media is excluded from Youtubarr's Missing view even if Sonarr is still waiting for a scan.

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

# YouTube playlist mapping

Open **Settings → Import Lists**.

## Single season

1. Select **Series / Sonarr**.
2. Choose the Sonarr series.
3. Choose the season.
4. Paste the YouTube playlist URL.
5. Optionally keep **Only missing targets** enabled.
6. Click **Load & Preview Playlist**.
7. Review every mapping.
8. Select the desired rows.
9. Click **Queue Selected Mappings**.

Example:

```text
YouTube item 1 → Jeopardy S01E01
YouTube item 2 → Jeopardy S01E02
YouTube item 3 → Jeopardy S01E03
```

## Complete-series playlist

When Sonarr reports more than one regular season, Youtubarr dynamically adds an All Seasons option.

Example for Wolfblood:

```text
All Seasons (1–5)
Season 0 (Specials)
Season 1
Season 2
Season 3
Season 4
Season 5
```

`All Seasons` deliberately excludes Season 0/Specials.

Targets are ordered by:

```text
Season number
    ↓
Episode number
```

so a complete-series playlist maps sequentially from `S01E01` through the final regular-season episode.

When **Only missing targets** is enabled, existing episodes are skipped **in place**. Later playlist items are not shifted onto the wrong Sonarr episodes.

Always review the preview before queuing, especially when the YouTube playlist item count differs from Sonarr's episode count.

## Music playlist mapping

Select **Music / Lidarr**, choose the artist and album, load the YouTube playlist, review playlist-position → Lidarr-track mapping, then queue the selected tracks.

# Recommended deployment: Portainer Web Editor

The recommended installation method is:

**Portainer → Stacks → Add stack → Web editor → paste Compose → Deploy the stack**

Portainer does not need to clone or build the repository. GitHub Actions publishes:

```text
ghcr.io/fudmonk95/youtubarr:latest
```

Youtubarr is **one stack and one container**.

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

# Requirements

The Docker host must provide:

- Docker / Portainer;
- `/dev/fuse`;
- `SYS_ADMIN`;
- unconfined AppArmor for the Youtubarr container;
- `/mnt/youtubarr` with shared mount propagation;
- persistent config/library/cache directories;
- network connectivity to Sonarr and Lidarr, and optionally Radarr.

Recommended host paths:

```text
/mnt/appdata/Youtubarr/config
/mnt/appdata/Youtubarr/library
/mnt/appdata/Youtubarr/cache
/mnt/youtubarr
```

# 1. Prepare persistent directories

```bash
mkdir -p /mnt/appdata/Youtubarr/{config,library,cache}
chown -R 1001:1001 /mnt/appdata/Youtubarr
```

The container repairs `/library` permissions itself at startup; no host ACL package is required for the normal deployment.

# 2. Prepare `/mnt/youtubarr`

The path must be a shared mount so the nested FUSE filesystem created inside Youtubarr propagates back to the Docker/LXC host.

When the repository exists at `/opt/youtubarr`:

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
/mnt/youtubarr ... ext4          shared
/mnt/youtubarr YoutubarrFS fuse shared
```

# 3. Portainer stack

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

      # Youtubarr library owner
      PUID: "1001"
      PGID: "1001"

      # Sonarr / Lidarr / Radarr user and group inside DUMB
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

## PUID/PGID versus ARR_UID/ARR_GID

```text
PUID / PGID       owner identity used by Youtubarr
ARR_UID / ARR_GID user/group used by Sonarr/Lidarr/Radarr
```

On the documented DUMB installation:

```text
Youtubarr: 1001:1001
Arr user:   1000:1000 (ubuntu)
```

At **every Youtubarr container start**, the complete `/library` tree is repaired automatically.

Directories are assigned the Arr group and mode:

```text
2775
```

Regular files use:

```text
0664
```

Youtubarr symlinks remain symlinks. New directories also inherit the shared Arr group through the setgid directory bit.

This applies to:

```text
/library/tv
/library/music
/library/movies
```

and every mapped subfolder underneath them.

`/mnt/youtubarr` remains a read-only FUSE filesystem. Arr applications and Jellyfin only need to read the virtual targets; `/library` is the writable symlink tree.

# 4. DUMB / Jellyfin / Arr access

Add these mounts to the existing **DUMB** service:

```yaml
      # Receive Youtubarr's propagated FUSE filesystem.
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rslave

      # Youtubarr's generated symlink library.
      - /mnt/appdata/Youtubarr/library:/youtube-library
```

Path flow:

```text
/youtube-library/tv/Example Show/Season 01/Example Show - S01E01.mp4
                   ↓ symlink
/mnt/youtubarr/tv/<asset-id>.mp4
                   ↓ FUSE
YouTube
```

Recommended Arr roots:

```text
/youtube-library/tv      → Sonarr
/youtube-library/music   → Lidarr
/youtube-library/movies  → optional Radarr
```

Youtubarr automatically understands these equivalent container paths:

```text
Arr / DUMB                         Youtubarr
/youtube-library/tv/...      →     /library/tv/...
/youtube-library/music/...   →     /library/music/...
/youtube-library/movies/...  →     /library/movies/...
```

No separate saved root mapping is required for media already under `/youtube-library`.

# 5. Verify container and FUSE state

```bash
docker ps --filter "name=youtubarr"
findmnt -R -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
docker logs --tail=100 youtubarr
```

Expected container state:

```text
Up ... (healthy)
```

Verify the shared library as the actual Arr user inside DUMB:

```bash
docker exec -u ubuntu DUMB-live sh -lc '
  id
  touch /youtube-library/tv/.arr-write-test
  rm -f /youtube-library/tv/.arr-write-test
  touch /youtube-library/music/.arr-write-test
  rm -f /youtube-library/music/.arr-write-test
  touch /youtube-library/movies/.arr-write-test
  rm -f /youtube-library/movies/.arr-write-test
'
```

# First-run setup

Open:

```text
http://YOUR_DOCKER_HOST:8788
```

A fresh installation asks you to:

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

# Individual YouTube acquisition

For an individual missing episode:

1. Open **Series** or **Wanted → Missing**.
2. Click the magnifying-glass button beside the episode.
3. Youtubarr searches using series + season/episode + episode-title context.
4. Review the result.
5. Click **Grab**.

Or paste a known YouTube video URL and use **Grab URL**.

The acquisition appears under **Activity → Queue** and moves to History after the FUSE asset and symlink are complete.

# Arr registration

Youtubarr local availability and Arr registration are intentionally separate.

A completed virtual media file is immediately shown as **Found by Youtubarr**. To have Sonarr/Lidarr display it as one of their own files, the corresponding `/youtube-library/...` root/path must also be configured in the Arr application and scanned/imported using that application's normal workflow.

This keeps the UI truthful: Youtubarr does not claim Sonarr/Lidarr registered a file merely because Jellyfin can already play it.

# Updating Youtubarr

Pull the latest image on the Docker host:

```bash
docker logout ghcr.io 2>/dev/null || true
docker pull ghcr.io/fudmonk95/youtubarr:latest
```

Then use:

**Portainer → Stacks → youtubarr → Editor → Update the stack**

If the image was pulled manually, do not force Portainer to re-pull it when Portainer has stored/invalid GHCR credentials.

Persistent configuration and database data remain under:

```text
/mnt/appdata/Youtubarr
```

After an update verify:

```bash
curl -s http://127.0.0.1:8788/api/bootstrap
docker logs --tail=100 youtubarr
```

Then hard-refresh the browser (`Ctrl+F5`) when the release includes frontend changes.

# Diagnostics

```bash
docker ps --filter "name=youtubarr"
docker logs --tail=200 youtubarr
ls -l /dev/fuse
findmnt -R -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
```

When the repository exists at `/opt/youtubarr`:

```bash
cd /opt/youtubarr
./scripts/doctor.sh
```

# Security

- No baked-in administrator credentials.
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
node --check backend/youtubarr/web/assets/app-v105-fixes.js
node --check backend/youtubarr/web/assets/app-playlist-all-seasons.js
node --check backend/youtubarr/web/assets/app-series-playlist-search.js
node --check backend/youtubarr/web/assets/app-v107-ui-fixes.js
```

# Licence

See `LICENSE`.
