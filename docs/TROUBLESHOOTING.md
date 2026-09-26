# Troubleshooting quick reference

Run `sudo ./scripts/doctor.sh` from the cloned repository first. Check `/dev/fuse`, `/mnt/youtubarr` shared propagation, the single `youtubarr` container, and the FUSE marker before debugging Arr mappings.

For failed acquisitions, separate source-resolution/remux errors from root-mapping errors. A correct mapping should produce an output below `/library/...`; the final library item should be a Linux symlink into `/mnt/youtubarr/...`.

Use `docker compose logs -f youtubarr` or Portainer's container logs. Do not expose signed YouTube media URLs or Arr API keys when sharing logs publicly.
