# Youtubarr

**YouTube acquisition for an Arr-managed media library.**

Youtubarr is a self-hosted companion for **Sonarr**, **Lidarr** and optional **Radarr**. It is designed to behave like another Arr application while using YouTube as an additional source for old, rare or otherwise difficult-to-find media.

Sonarr, Lidarr and Radarr remain the source of truth for media identity, metadata, monitoring, seasons, episodes, albums and tracks. Youtubarr adds YouTube discovery, playlist mapping, virtual FUSE media and a symlink library without replacing the Arr applications.

## Current release

```text
v1.0.8
```

### v1.0.8 highlights

- Series opens in an **Incomplete** working view by default.
- Fully available series can still be shown with **Filter → Complete** or **Filter → All**.
- Complete poster/season progress bars are green; incomplete progress keeps the YouTube-red identity.
- `All Seasons` playlist mapping no longer assumes a playlist starts at Season 1.
- Youtubarr recognises common episode tokens including `S03E01`, `3x01`, `Season 3 Episode 1` and `Series 3 Episode 1`.
- When every playlist item exposes an episode token, mapping is by the exact Sonarr season/episode number rather than playlist position.
- Partial/non-contiguous playlists are therefore supported when their titles contain season/episode numbering.
- When titles are ambiguous, `All Seasons` exposes **Start mapping at season** and **Start mapping at episode** so a playlist beginning at Season 3 can be mapped from `S03E01` instead of `S01E01`.
- The playlist preview tells you whether exact-token mapping or sequential fallback is being used.
- Existing Youtubarr availability, FUSE, permissions and Arr-style UI behaviour remain intact.

# What Youtubarr does

Typical TV workflow:

```text
Sonarr reports an episode missing
        ↓
Youtubarr reads Sonarr metadata
        ↓
Search YouTube / search playlists / paste a URL
        ↓
Review or map the source
        ↓
Youtubarr exposes a virtual media file through FUSE
        ↓
A Linux symlink is created in the Youtubarr library
        ↓
Jellyfin / Sonarr / Lidarr can read the media
```

Youtubarr supports:

- Series through Sonarr.
- Music through Lidarr.
- Optional Movies through Radarr.
- Individual YouTube searches.
- Direct YouTube URL acquisition.
- Series-level and season-level playlist search.
- Ordered YouTube playlist mapping.
- Multi-season playlist mapping.
- Partial multi-season playlist mapping.
- Progressive MP4 sources.
- Split audio/video remux when required.
- Music-focused audio sources.
- FUSE virtual media.
- Linux symlink libraries.
- Persistent acquisition history.
- Combined Arr + Youtubarr availability reporting.

# Availability states

Youtubarr does not rely only on an Arr application's `hasFile` flag.

Media can be shown as:

```text
Missing
Found by Youtubarr
Registered
```

**Missing** means neither the Arr application nor Youtubarr has a usable file.

**Found by Youtubarr** means the Youtubarr acquisition completed and the generated library symlink still resolves to a live FUSE asset.

**Registered** means the connected Arr application itself reports the media as present.

Verified Youtubarr media is excluded from Youtubarr's Wanted/Missing view so it is not repeatedly searched for.

## Series progress

Series poster cards and season headers use the combined availability view.

Example:

```text
Sonarr registered:      0 / 13
Youtubarr verified:    13 / 13
Youtubarr UI progress: 13 / 13
```

Complete series use a green progress bar.

The default Series filter is **Incomplete**, so a fully available show drops out of the normal working list. It remains available under:

```text
Filter
├─ Incomplete
├─ Complete
├─ All
├─ Monitored
└─ Unmonitored
```

# Interface

## Series

```text
Series
├─ Add New
└─ Library Import
```

The Series toolbar follows Arr-style controls:

- Update Filtered
- RSS Sync
- Select Series
- Test Parsing
- Options
- View
- Sort
- Filter

Only one toolbar popover can be open at a time. Opening another menu closes the previous one; clicking outside or pressing `Escape` closes the menu.

Open a series to see seasons and episodes. Season headers show combined availability:

```text
Season 1       13 / 13
████████████████████
```

Each season also has a YouTube playlist search action.

## Playlist hard search

From a series page, use **Search Playlists** to search YouTube for playlists for the whole programme.

A season-level playlist search can search for a specific season.

Examples:

```text
Wolfblood full series complete episodes playlist
Wolfblood season 3 full episodes playlist
```

**Use Playlist** carries the selected series, season scope and playlist URL into Import Lists.

# YouTube playlist mapping

Open:

**Settings → Import Lists**

## Single season

1. Select **Series / Sonarr**.
2. Choose the Sonarr series.
3. Choose a season.
4. Paste the YouTube playlist URL.
5. Set **Start mapping at episode** if required.
6. Keep **Only missing targets** enabled when appropriate.
7. Click **Load & Preview Playlist**.
8. Review every mapping.
9. Queue the selected rows.

## All Seasons

If Sonarr exposes more than one regular season, Youtubarr dynamically adds an All Seasons option.

Example:

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

### Important: Sonarr's season range is not the playlist's season range

`All Seasons (1–21)` means **Sonarr knows the show has Seasons 1 through 21**. It does **not** mean the selected YouTube playlist necessarily contains Seasons 1 through 21.

A playlist may contain only:

```text
Season 3 → Season 21
```

or even a non-contiguous subset.

Youtubarr v1.0.8 handles this in two ways.

### Exact-token mapping

When every YouTube title contains season/episode information, Youtubarr maps by that token instead of playlist position.

Recognised examples include:

```text
Show Name S03E01
Show Name 3x01
Show Name Season 3 Episode 1
Show Name Series 3 Episode 1
```

So:

```text
YouTube: Series 3 Episode 1 → Sonarr: S03E01
YouTube: Series 3 Episode 2 → Sonarr: S03E02
...
YouTube: Series 21 Episode 8 → Sonarr: S21E08
```

No fake Season 1 or Season 2 mapping is introduced just because Sonarr has those seasons.

### Sequential fallback

Some old YouTube playlists use generic titles such as:

```text
Episode 1
Episode 2
Episode 3
```

When Youtubarr cannot reliably determine season/episode numbers from every playlist item, it refuses to silently guess that the playlist begins at Season 1.

For **All Seasons**, use:

```text
Start mapping at season:  3
Start mapping at episode: 1
```

The preview will then begin at:

```text
S03E01
```

and continue through Sonarr's ordered episode list.

Always review the preview before queuing. The preview states whether Youtubarr is using **detected episode tokens** or **sequential mapping**.

### Only missing targets

When **Only missing targets** is enabled, existing episodes are skipped in place. Their removal does not shift every later YouTube item onto the wrong Sonarr episode.

# Music playlist mapping

Select **Music / Lidarr**, choose an artist and album, paste/load the playlist, review playlist-position → Lidarr-track mappings and queue the selected tracks.

# Activity

```text
Activity
├─ Queue
├─ History
└─ Blocklist
```

# Wanted

```text
Wanted
├─ Missing
└─ Cutoff Unmet
```

For Sonarr, Missing groups episodes by series and shows series artwork, episode information and search actions.

Verified Youtubarr media is excluded from Youtubarr's Missing view even if Sonarr has not registered the file yet.

# Settings

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

# Recommended deployment: Portainer Web Editor

The recommended deployment is:

**Portainer → Stacks → Add stack → Web editor → paste Compose → Deploy the stack**

GitHub Actions publishes:

```text
ghcr.io/fudmonk95/youtubarr:latest
```

Youtubarr is **one stack and one container**. There is no FUSE sidecar.

## Requirements

The Docker host needs:

- Docker / Portainer.
- `/dev/fuse`.
- `SYS_ADMIN`.
- Unconfined AppArmor for the Youtubarr container.
- `/mnt/youtubarr` with shared propagation.
- Persistent config/library/cache folders.
- Network connectivity to Sonarr and Lidarr and optional Radarr.

Recommended host paths:

```text
/mnt/appdata/Youtubarr/config
/mnt/appdata/Youtubarr/library
/mnt/appdata/Youtubarr/cache
/mnt/youtubarr
```

## Host preparation

```bash
mkdir -p /mnt/appdata/Youtubarr/{config,library,cache}
chown -R 1001:1001 /mnt/appdata/Youtubarr
```

When the repository exists at `/opt/youtubarr`:

```bash
cd /opt/youtubarr
chmod +x scripts/*.sh
./scripts/install-host.sh
```

Verify:

```bash
findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS,PROPAGATION /mnt/youtubarr
```

The backing mount should be shared.

# Portainer stack

```yaml
services:

  youtubarr:
    container_name: youtubarr
    image: ghcr.io/fudmonk95/youtubarr:latest
    restart: unless-stopped
    stop_grace_period: 30s

    environment:
      TZ: Europe/London

      PUID: "1001"
      PGID: "1001"

      # Sonarr / Lidarr / Radarr identity inside DUMB
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

# DUMB / Jellyfin / Arr mounts

Add these mounts to the existing DUMB service:

```yaml
      - type: bind
        source: /mnt/youtubarr
        target: /mnt/youtubarr
        bind:
          propagation: rslave

      - /mnt/appdata/Youtubarr/library:/youtube-library
```

This gives DUMB/Jellyfin/Arr applications:

```text
/youtube-library/tv
/youtube-library/music
/youtube-library/movies
```

and the propagated virtual targets under:

```text
/mnt/youtubarr/tv
/mnt/youtubarr/music
/mnt/youtubarr/movies
```

Recommended roots:

```text
Sonarr: /youtube-library/tv
Lidarr: /youtube-library/music
Radarr: /youtube-library/movies
```

Youtubarr automatically understands the equivalent container paths:

```text
Arr / DUMB                         Youtubarr
/youtube-library/tv/...      →     /library/tv/...
/youtube-library/music/...   →     /library/music/...
/youtube-library/movies/...  →     /library/movies/...
```

# Permissions

Youtubarr repairs its complete `/library` tree **every time the container starts**.

With the documented values:

```text
Youtubarr owner: 1001:1001
Arr user/group:  1000:1000
```

Directories are repaired with the Arr group and setgid mode:

```text
2775
```

Regular files use:

```text
0664
```

This applies to:

```text
/library/tv
/library/music
/library/movies
```

and every subfolder Youtubarr creates later.

`/mnt/youtubarr` remains a read-only FUSE filesystem. Arr applications and Jellyfin only need to read those targets; `/library` is the writable symlink tree.

# First-run setup

Open:

```text
http://YOUR_DOCKER_HOST:8788
```

A fresh installation asks you to:

1. Create an administrator username/password.
2. Enable Series and/or Music.
3. Optionally enable Movies.
4. Connect Sonarr/Lidarr/optional Radarr.
5. Generate root mappings.

Defaults:

```text
Series  ON
Music   ON
Movies  OFF
```

On the documented DUMB network:

```text
Sonarr: http://DUMB-live:8989
Lidarr: http://DUMB-live:8686
Radarr: http://DUMB-live:7878
```

# Verify installation

```bash
docker ps --filter "name=youtubarr"
findmnt -R -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
cat /mnt/youtubarr/.youtubarr.json
docker logs --tail=100 youtubarr
```

Verify the actual Arr user can use the library:

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

# Updating Youtubarr

If Portainer cannot pull GHCR anonymously, pull the image first on the Docker host:

```bash
docker logout ghcr.io 2>/dev/null || true
docker pull ghcr.io/fudmonk95/youtubarr:latest
```

Then:

**Portainer → Stacks → youtubarr → Editor → Update the stack**

Do not force a Portainer re-pull when you already pulled the image manually.

Verify:

```bash
curl -s http://127.0.0.1:8788/api/bootstrap
docker logs --tail=100 youtubarr
```

After an interface update, hard-refresh the browser (`Ctrl+F5`).

# Important design rule

Youtubarr is not intended to replace Sonarr or Lidarr.

The Arr services remain responsible for metadata and library identity. Youtubarr provides an additional YouTube acquisition route and a virtual media layer for content that is otherwise difficult to obtain.
