# DUMB / Zurg coexistence

Youtubarr does not depend on DUMB or Zurg, but is designed not to conflict with them.

- Youtubarr reads Sonarr/Lidarr/Radarr metadata through their APIs.
- Paths such as `/zurg_mnt/zurg/__magic__/...` are treated as remote Arr root identities only.
- Youtubarr does not write into those roots.
- Local Youtubarr mappings live under `/library` inside the Youtubarr container.
- The host location backing `/library` is set by `YOUTUBARR_LIBRARY_DIR`.
- Virtual Youtubarr assets live under `/mnt/youtubarr`; this mount is separate from Zurg.

For media servers, bind the Youtubarr library and `/mnt/youtubarr` into the media-server container. The `/mnt/youtubarr` target path must remain identical so Linux symlinks resolve correctly.
