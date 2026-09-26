# Youtubarr v1.0.0

<p align="center">
  <img src="backend/youtubarr/web/assets/logo.svg" alt="Youtubarr" width="420">
</p>

<p align="center"><strong>YouTube, in your media library.</strong></p>

Youtubarr is a self-hosted Arr-style application for using YouTube as an additional source for hard-to-find **TV episodes and music**, while keeping **Sonarr and Lidarr as the metadata source of truth**. Optional movie support is available through Radarr and is disabled by default.

Youtubarr is designed to sit beside Sonarr, Radarr and Lidarr rather than replace them. It uses an Arr-style layout with a dark navigation/header area, light content panels, compact tables and **YouTube-red** branding.

> **v1 is a clean rebuild.** It is not the old 0.2 alpha application repackaged. The deployment model, setup flow, UI and virtual-media architecture were rebuilt around a **single-container FUSE design**.

---

## What Youtubarr is for

Youtubarr exists for media that is difficult or impossible to source through normal torrent/NZB workflows but is available legitimately on YouTube: old TV, regional programmes, archive material, music, concerts, obscure releases and similar media.

The important design choice is that **Youtubarr does not try to become another Sonarr, Lidarr or Radarr**. Those applications remain responsible for canonical metadata, titles, seasons, episodes, albums, tracks, monitoring and library identity. Youtubarr asks those services what the media is and where it belongs, then provides an additional YouTube acquisition path.

### Primary modules

- **Series** — enabled by default and powered by Sonarr.
- **Music** — enabled by default and powered by Lidarr.
- **Movies** — optional, disabled by default and powered by Radarr.

If Movies is disabled, Radarr is not required and the Movies section is not shown in the normal Youtubarr navigation.

---

## Key features

- Arr-style web interface with YouTube-red Youtubarr branding.
- First-run wizard — there are no factory credentials.
- Create the first administrator account on first launch.
- Connect Sonarr, Lidarr and optional Radarr using their normal API URLs and API keys.
- Automatic Arr root discovery.
- One-to-one writable root mapping under `/library`.
- Longest/deepest matching Arr root wins when an item is placed.
- Interactive YouTube search through `yt-dlp`.
- YouTube playlist import.
- Playlist-order mapping to a Sonarr season or Lidarr album.
- **Virtual Symlink** acquisition is the default design.
- Real Linux symlinks are created in the exported library.
- Virtual files are exposed through FUSE at `/mnt/youtubarr`.
- Progressive MP4 virtual reads.
- Split video/audio YouTube streams handled with ffmpeg remux into a bounded disposable cache.
- M4A virtual-audio support for music.
- One Docker Compose service and **one Youtubarr container**.
- Built-in System Status page.
- Host-side `doctor.sh` diagnostics.
- Designed to coexist with DUMB-hosted Arr services and Zurg without modifying Zurg.
- Persistent configuration/database under `/config`.
- Persistent exported symlink library under `/library`.

---

## How this differs from the other projects supplied during development

The other projects are useful, but they solve different problems. This comparison is based on the versions/code supplied while Youtubarr v1 was being designed.

| Capability | **Youtubarr v1** | **yt2radarr** | **Other supplied Youtubarr / Lidarr bridge** |
|---|---|---|---|
| Main focus | TV + music, optional movies | Radarr-oriented YouTube acquisition | YouTube playlist/Lidarr workflow |
| Metadata authority | Sonarr / Lidarr / optional Radarr | Radarr with optional Sonarr-related workflow | Lidarr-oriented |
| Normal media behaviour | Virtual symlink/FUSE | Local media download/import workflow | Import-list/playlist workflow |
| Full media permanently stored by default | **No** | **Yes in its normal download flow** | Not the same virtual-media design |
| TV season/episode workflow | **Yes** | More limited than Youtubarr's Sonarr-first model | No equivalent full TV workflow |
| Music/Lidarr workflow | **Yes** | Not its main purpose | **Yes** |
| Optional Radarr movie mode | **Yes** | **Yes / primary use** | No |
| Playlist order → season episodes | **Yes** | No equivalent workflow in the supplied version | No |
| Playlist order → album tracks | **Yes** | No | Playlist/Lidarr oriented |
| Arr-style application UI | **Yes** | Different UI | Different UI |
| FUSE virtual filesystem | **Yes** | No | No |
| Single Youtubarr container | **Yes** | Application-specific deployment | Supplied project used additional application components |

In practical terms, **yt2radarr** is closer to a downloader/import helper: choose a Radarr item, acquire the source, rename it and place a resulting file where the media library expects it. That is useful when you explicitly want a permanent local media file.

The other supplied **Youtubarr** project is primarily a YouTube/Lidarr playlist integration. It is not trying to provide the Sonarr-style TV acquisition and FUSE-backed virtual-file design used here.

**This Youtubarr v1** behaves more like another member of the Arr stack: it asks Sonarr/Lidarr/Radarr what the target media is, maps that target into a writable Youtubarr library and exposes YouTube media through real Linux symlinks backed by Youtubarr's own virtual filesystem.

---

# Architecture

There is exactly **one Compose service and one Youtubarr container**.

```text
                              ┌─────────────────────────────────────────┐
                              │           Youtubarr container           │
                              │                                         │
Browser ─────────────────────►│ FastAPI + Arr-style web UI             │
Sonarr / Lidarr / Radarr ────►│ Arr API integration                    │
YouTube ─────────────────────►│ yt-dlp resolver                        │
                              │ ffmpeg split-stream remux              │
                              │ FUSE virtual filesystem                │
                              └──────────────────┬──────────────────────┘
                                                 │ rshared bind
                                                 ▼
                                          /mnt/youtubarr
                                                 ▲
                                                 │ absolute symlink
                 /library/tv/.../Episode.mp4 ────┤
                 /library/music/.../Track.m4a ───┘
```

The FUSE daemon is a second **process inside the same container**, not a second container or sidecar.

Your Portainer stack should therefore show one container only:

```text
youtubarr
```

If you see a separate `youtubarr-fuse` container, that is the old alpha deployment and it should not be deployed alongside v1.

---

# Virtual Symlink design

## TV example

```text
/library/tv/kids/Jeopardy (2002)/Season 01/
  Jeopardy (2002) - S01E01 - Pilot.mp4
        │
        └── Linux symlink ──► /mnt/youtubarr/tv/<asset-id>.mp4
                                      │
                                      └── Youtubarr FUSE ──► YouTube
```

## Music example

```text
/library/music/main/Artist/Album/01 - Track.m4a
        │
        └── Linux symlink ──► /mnt/youtubarr/music/<asset-id>.m4a
                                      │
                                      └── Youtubarr FUSE ──► YouTube
```

The symlink is permanent library metadata. The full YouTube media file is **not** permanently stored in Virtual Symlink mode.

### Split video/audio sources

Many normal YouTube videos expose video and audio as separate streams. Youtubarr can resolve a compatible video stream and audio stream and remux them with ffmpeg into a **bounded transient cache** so the virtual file has stable seekable behaviour.

The cache is disposable. It is not the library.

Default limits:

```env
YOUTUBARR_CACHE_MAX_GB=20
YOUTUBARR_CACHE_TTL_HOURS=24
```

---

# Requirements

- Linux Docker host.
- Docker Engine with Compose v2.
- `/dev/fuse` available to Docker.
- Ability to use the `SYS_ADMIN` capability for the Youtubarr container.
- A writable host path for Youtubarr config.
- A writable host path for the Youtubarr exported library.
- Sonarr for Series mode.
- Lidarr for Music mode.
- Radarr only when Movies mode is enabled.

The image includes the Python runtime, FastAPI/Uvicorn, `yt-dlp`, ffmpeg/ffprobe and FUSE3/fusepy.

A Google YouTube Data API key is not required for the normal yt-dlp search/acquisition path.

---

# Proxmox LXC prerequisite

If Docker is running inside a Proxmox LXC, `/dev/fuse` must be visible **inside that LXC** before Youtubarr can work.

Inside the Debian LXC / Docker host:

```bash
ls -l /dev/fuse
```

If `/dev/fuse` does not exist, the LXC must be configured from the **Proxmox host** first.

> `pct` commands are Proxmox-host commands. They do **not** run inside the Debian LXC.

Youtubarr does not attempt to alter the outer Proxmox host from inside a container. Once `/dev/fuse` exists in the Docker host/LXC, the Youtubarr host installer handles the remaining mount preparation.

---

# Recommended deployment: GitHub + Portainer

The repository contains one `docker-compose.yml` and one service. Portainer can pull/build the repository directly, but the host-side FUSE/shared-mount preparation still has to be run on the Docker host once.

## 1. Clone the repository on the Docker host

```bash
sudo git clone https://github.com/Fudmonk95/Youtubarr.git /opt/youtubarr
cd /opt/youtubarr
```

If `/opt/youtubarr` already contains an older clone:

```bash
cd /opt/youtubarr
git pull
```

## 2. Prepare the Docker host

```bash
cd /opt/youtubarr
sudo ./scripts/install-host.sh
```

The installer:

- verifies `/dev/fuse`;
- prepares `/mnt/youtubarr` as Youtubarr's dedicated shared bind mount;
- refuses to replace an unrelated mount;
- never modifies Zurg mounts;
- installs `youtubarr-mount.service`;
- enables the preparation service at boot;
- creates `/opt/youtubarr/.env` from `.env.example` when required;
- remains safe to run again.

Check the host preparation:

```bash
systemctl status youtubarr-mount.service --no-pager
findmnt -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
```

## 3. Create persistent host folders

For Portainer, absolute host paths are recommended:

```bash
sudo mkdir -p /opt/youtubarr-data/config
sudo mkdir -p /opt/youtubarr-data/library
sudo mkdir -p /opt/youtubarr-data/cache
```

Set ownership to the PUID/PGID you intend to use. Check your IDs with:

```bash
id
```

Example for UID/GID 1000:

```bash
sudo chown -R 1000:1000 /opt/youtubarr-data
```

## 4. Create the Portainer Git stack

In Portainer:

1. Open **Stacks**.
2. Select **Add stack**.
3. Name the stack `youtubarr`.
4. Select **Repository / Git repository**.
5. Repository URL:

   ```text
   https://github.com/Fudmonk95/Youtubarr.git
   ```

6. Repository reference:

   ```text
   refs/heads/main
   ```

7. Compose path:

   ```text
   docker-compose.yml
   ```

8. Add the environment variables below.
9. Deploy the stack.

### Recommended Portainer variables

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

Change PUID/PGID and host storage paths for your own server.

## 5. Confirm Portainer created one container

Expected:

```text
youtubarr
```

Not expected:

```text
youtubarr-fuse
```

The FUSE daemon runs inside the same Youtubarr container.

## 6. Open Youtubarr

```text
http://YOUR-SERVER-IP:8788
```

There is no default login. A clean `/config` opens the setup wizard automatically.

---

# Alternative: Docker Compose CLI

After host preparation:

```bash
cd /opt/youtubarr
cp -n .env.example .env
nano .env
docker compose up -d --build
```

Check status:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs -f youtubarr
```

---

# First-run setup wizard

A clean configuration opens the setup wizard automatically.

## Step 1 — Create User

Create the first administrator username and password.

- No factory username.
- No factory password.
- Password must meet the application's minimum requirements.
- Youtubarr generates its own application API key.

## Step 2 — Media Types

Choose the modules you want:

- **Series** — enabled by default.
- **Music** — enabled by default.
- **Movies** — disabled by default.

If Movies remains disabled, Radarr is not required and Movies is omitted from the main navigation.

## Step 3 — Connect Services

Enter the URL and API key for each enabled Arr service.

Typical examples:

```text
Sonarr: http://192.168.1.10:8989
Lidarr: http://192.168.1.10:8686
Radarr: http://192.168.1.10:7878
```

Use addresses that are reachable **from inside the Youtubarr container**. An Arr API key is normally available in that application's **Settings → General** page.

## Step 4 — Library and FUSE

Youtubarr discovers the root folders reported by each connected Arr service and creates local Youtubarr mappings under `/library`.

Example:

```text
Sonarr reports:
/zurg_mnt/zurg/__magic__/tv/kids

Youtubarr local mapping:
/library/tv/kids
```

Another root remains separate:

```text
/zurg_mnt/zurg/__magic__/tv/bbc
        ↓
/library/tv/bbc
```

Multiple Arr roots are intentionally **not** collapsed into one directory.

## Step 5 — Finish

Youtubarr validates the enabled integrations and mappings before opening the normal dashboard.

---

# Arr root mapping behaviour

Youtubarr never treats the remote/read-only Arr root as its own writable output directory. The Arr path is used to work out the corresponding local Youtubarr destination.

Example:

```text
Sonarr root:
/zurg_mnt/zurg/__magic__/tv/kids

Youtubarr mapping:
/zurg_mnt/zurg/__magic__/tv/kids
        ↓
/library/tv/kids
```

A series under:

```text
/zurg_mnt/zurg/__magic__/tv/kids/Jeopardy (2002)
```

therefore maps to:

```text
/library/tv/kids/Jeopardy (2002)
```

and S01E01 can become:

```text
/library/tv/kids/Jeopardy (2002)/Season 01/
Jeopardy (2002) - S01E01 - Pilot.mp4
```

If several configured roots could match a source path, the **deepest/longest matching root** wins.

---

# Series workflow

1. Sonarr already contains the series and canonical episode metadata.
2. Open the series/episode in Youtubarr.
3. Search YouTube or provide the intended YouTube source.
4. Review/select the source.
5. Acquire it.
6. Youtubarr resolves the YouTube media.
7. A virtual asset is registered below `/mnt/youtubarr/tv`.
8. A real Linux symlink is created at the Sonarr-derived Youtubarr library path.
9. Your media server scans the exported Youtubarr library.

Youtubarr uses Sonarr's episode title, season and episode numbering rather than trusting arbitrary YouTube titles when Sonarr already knows the canonical metadata.

---

# Playlist → Sonarr season workflow

This is useful for old programmes whose YouTube playlist is correctly ordered but whose individual video titles are poor.

```text
Playlist item 1 → S01E01
Playlist item 2 → S01E02
Playlist item 3 → S01E03
...
```

For a playlist where YouTube titles are only `Episode 1`, `Episode 2`, etc., Sonarr still supplies the actual episode titles and numbering.

Always review the playlist ordering before bulk acquisition.

---

# Music workflow

1. Lidarr contains the artist/album/track metadata.
2. Select the target in Youtubarr.
3. Search/select the matching YouTube source.
4. Youtubarr resolves a compatible audio stream.
5. The virtual asset is exposed below `/mnt/youtubarr/music`.
6. A real symlink is created under the Lidarr-derived `/library/music/...` path.

Example:

```text
/library/music/main/Artist/Album/01 - Track.m4a
  -> /mnt/youtubarr/music/<asset-id>.m4a
```

---

# Playlist → Lidarr album workflow

A YouTube playlist can be mapped to a Lidarr album by order:

```text
Playlist item 1 → Track 01
Playlist item 2 → Track 02
Playlist item 3 → Track 03
...
```

This is useful when the playlist is correctly ordered but individual YouTube titles do not cleanly match the album metadata.

---

# Optional Movies / Radarr

Movies are deliberately optional because YouTube is not normally a general full-movie source.

When Movies is disabled:

- Radarr is not required.
- Setup does not require a Radarr connection.
- The Movies navigation item is hidden.

When Movies is enabled, Youtubarr can use Radarr metadata and root mappings for manually reviewed sources associated with a Radarr movie entry.

---

# DUMB + Zurg compatibility

Youtubarr does **not** require DUMB or Zurg, but it is designed to coexist with both.

Typical arrangement:

```text
DUMB
 ├─ Sonarr
 ├─ Radarr
 └─ Lidarr
       │
       │ HTTP APIs
       ▼
Youtubarr
       │
       ├─ /library         writable Youtubarr exported library
       └─ /mnt/youtubarr   Youtubarr FUSE virtual media

Zurg
 └─ /zurg_mnt/...         separate existing virtual/remote media roots
```

Youtubarr:

- reads Sonarr/Lidarr/Radarr metadata over HTTP;
- may see Zurg-style root names reported by the Arr services;
- uses those roots only as path identities for mapping;
- does **not** write YouTube files into `/zurg_mnt`;
- does **not** chmod/chown Zurg;
- does **not** remount Zurg;
- does **not** rename or delete Zurg content;
- keeps `/mnt/youtubarr` dedicated to Youtubarr's own virtual filesystem.

See [docs/DUMB-ZURG.md](docs/DUMB-ZURG.md).

---

# Jellyfin / Plex / Emby integration

A media server must be able to see **both**:

1. the Youtubarr exported library; and
2. `/mnt/youtubarr` at the same absolute path used by the symlink.

Example Jellyfin additions:

```yaml
volumes:
  - /opt/youtubarr-data/library:/youtube-library:ro
  - /mnt/youtubarr:/mnt/youtubarr:ro,rslave
```

The media server scans `/youtube-library`, while the symlink inside that directory still resolves because `/mnt/youtubarr` exists at the same absolute target path in the media-server container.

Do not automatically rewrite an existing Jellyfin/Plex/Emby Compose file. Add these mounts deliberately to the relevant media-server container.

---

# Verifying a real symlink

On the Docker host:

```bash
test -L '/path/to/item.mp4' && echo 'real symlink'
readlink '/path/to/item.mp4'
ls -l '/path/to/item.mp4'
```

TV links should point below:

```text
/mnt/youtubarr/tv/
```

Music links should point below:

```text
/mnt/youtubarr/music/
```

---

# Environment variables

| Variable | Default | Purpose |
|---|---:|---|
| `TZ` | `Europe/London` | Container timezone |
| `PUID` | `1000` | Ownership used for exported library/FUSE stat results |
| `PGID` | `1000` | Group ownership |
| `YOUTUBARR_PORT` | `8788` | Published web port |
| `BIND_ADDRESS` | `0.0.0.0` | Host bind address |
| `YOUTUBARR_CONFIG_DIR` | `./config` | Persistent host config/database directory |
| `YOUTUBARR_LIBRARY_DIR` | `./library` | Persistent exported symlink library |
| `YOUTUBARR_CACHE_DIR` | `./cache` | Disposable split-stream cache |
| `YOUTUBARR_MOUNT_DIR` | `/mnt/youtubarr` | Host Youtubarr shared/FUSE mount |
| `YOUTUBARR_MAX_VIDEO_HEIGHT` | `1080` | Maximum selected video height |
| `YOUTUBARR_CACHE_MAX_GB` | `20` | Maximum transient remux cache target |
| `YOUTUBARR_CACHE_TTL_HOURS` | `24` | Cache expiry age |
| `YOUTUBARR_LOG_LEVEL` | `INFO` | Application log level |

For Portainer, use absolute host paths for config/library/cache.

---

# Diagnostics

## Host doctor

```bash
cd /opt/youtubarr
sudo ./scripts/doctor.sh
```

It checks the important host/runtime conditions including `/dev/fuse`, the Youtubarr mount directory, mount propagation, container state, FUSE marker visibility and API reachability.

## UI status

Open:

```text
System → Status
```

The application reports FUSE state, virtual-filesystem state, library/config write access, ffmpeg availability and Arr integration information.

## Logs

CLI deployment:

```bash
cd /opt/youtubarr
docker compose logs -f youtubarr
```

Portainer deployment:

```text
Containers → youtubarr → Logs
```

---

# Common problems

## `/dev/fuse` is missing

Inside the Debian Docker host/LXC:

```bash
ls -l /dev/fuse
```

If it is missing and Docker runs inside Proxmox LXC, fix the LXC configuration from the **Proxmox host** first.

## FUSE works in the container but symlinks are broken on the host

Check propagation:

```bash
findmnt -o TARGET,SOURCE,FSTYPE,PROPAGATION /mnt/youtubarr
```

Then run:

```bash
cd /opt/youtubarr
sudo ./scripts/doctor.sh
```

The shared mount must be prepared before the Portainer stack starts.

## Arr connection fails

The Arr URL must be reachable from the Youtubarr container. `localhost` means Youtubarr itself, not another container or the Docker host.

## Root mapping is wrong

Open **Settings → Media Management** and review the remote Arr root against its local `/library/...` mapping. Youtubarr's writable local destination must not be a read-only Zurg root.

## Split-stream source takes time to begin

Separate video/audio sources need an ffmpeg remux into the bounded transient cache before they can behave as a stable seekable virtual file.

## Existing file blocks acquisition

Youtubarr does not silently overwrite an unrelated existing media file or symlink at the destination path. Resolve the collision rather than deleting library content automatically.

---

# Reboot behaviour

The host service:

```text
youtubarr-mount.service
```

prepares the shared mount before Docker starts. The **single** Youtubarr container starts the FUSE process and application runtime.

There is no second FUSE container and no requirement to manually rerun a FUSE-preparation script after every normal reboot once the host setup has been installed correctly.

---

# Updating

## Portainer Git stack

Update the host-side clone first so host scripts remain current:

```bash
cd /opt/youtubarr
sudo git pull
sudo ./scripts/install-host.sh
```

Then use Portainer's stack update/redeploy option and pull the latest repository version. Do not delete the persistent config/library folders unless you intentionally want a clean installation.

## Docker Compose CLI

```bash
cd /opt/youtubarr
git pull
sudo ./scripts/install-host.sh
docker compose up -d --build
```

---

# Uninstall

Stop/remove the Portainer stack or CLI stack first.

CLI example:

```bash
cd /opt/youtubarr
docker compose down
sudo ./scripts/uninstall-host.sh
```

The host uninstall script does not deliberately delete Youtubarr config data, the exported library, Zurg data, Sonarr/Radarr/Lidarr data or media-server libraries.

Remove persistent Youtubarr data manually only when you really intend to destroy the installation.

---

# Security notes

- Arr API keys are stored by the application rather than being exposed in the public repository.
- Browser sessions use an HTTP-only cookie.
- Youtubarr generates its own application API key during first setup.
- Signed media URLs should not be deliberately emitted to normal logs.
- The container receives `SYS_ADMIN` because Linux FUSE mounting requires it.
- `/dev/fuse` is passed explicitly to the single Youtubarr container.
- The Docker socket is not required and should not be mounted into Youtubarr.
- Do not commit `/config`, database files, secrets or browser cookies to GitHub.

---

# Repository layout

```text
Youtubarr/
├── backend/
│   ├── tests/
│   └── youtubarr/
│       ├── web/
│       ├── acquisition.py
│       ├── arr.py
│       ├── fuse_mount.py
│       ├── virtual.py
│       └── ...
├── docs/
├── scripts/
├── systemd/
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── pyproject.toml
└── README.md
```

---

# Development and tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
PYTHONPATH=backend pytest -q
```

Fixture/unit tests are not treated as proof that a YouTube/FUSE/media-server path works on every Docker, NAS or LXC configuration. Use **System → Status**, `doctor.sh` and an actual playback/seek test on the target server.

---

# Project status

Youtubarr v1.0.0 is the first release of the clean v1 architecture. It is intended to be deployed as a real stack rather than a UI mock-up, but YouTube delivery formats and self-hosted Docker/FUSE environments vary. Report reproducible problems with logs and the relevant System Status/doctor output.

---

# License and project relationship

GPL-3.0.

Youtubarr is an independent project. It is not affiliated with, endorsed by or part of YouTube/Google, Sonarr, Radarr, Lidarr, Jellyfin, Plex, Emby, DUMB or Zurg.

The interface is an original implementation inspired by common interaction patterns in the Arr ecosystem rather than a copy of another project's source code.

Use Youtubarr only with media you are permitted to access and use.
