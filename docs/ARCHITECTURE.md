# Architecture

Youtubarr v1 is intentionally a **single-container** application.

The `youtubarr` container runs both the FastAPI web/API process and the FUSE daemon. Docker receives `/dev/fuse`, `SYS_ADMIN`, and an `rshared` bind for `/mnt/youtubarr`.

The exported library contains real Linux symlinks whose targets are absolute `/mnt/youtubarr/...` paths. Media servers therefore need the exported library plus `/mnt/youtubarr` mounted at the same absolute path.

Sonarr, Lidarr and optional Radarr remain the metadata authorities. Their root paths are mapped to writable `/library/...` paths; Youtubarr never writes into a remote or read-only Zurg root.

Progressive MP4/M4A sources are served through byte-range reads. Split video/audio sources are stream-copied by ffmpeg into a bounded transient cache to provide stable random-access semantics without turning the cache into permanent media storage.
