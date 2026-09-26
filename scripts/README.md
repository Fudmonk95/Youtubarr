# Host scripts

These scripts are intended to be run on the Docker host (or inside the Debian LXC when Docker itself runs there).

- `install-host.sh` prepares persistent host mount propagation and installs the boot-time systemd unit.
- `prepare-mount.sh` safely prepares `/mnt/youtubarr` and never modifies a live Youtubarr FUSE mount or unrelated mount.
- `doctor.sh` checks FUSE, propagation, Compose and application reachability.
- `uninstall-host.sh` removes only Youtubarr's host preparation and does not delete config/library media data.
- `youtubarr` is a convenience wrapper around common Compose operations.
