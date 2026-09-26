# Upgrade notes

Youtubarr v1.0.0 is a clean-break deployment from the old 0.2 alpha stack. Do not deploy the old `youtubarr-fuse` sidecar with v1.

Stop/remove the old alpha stack before starting v1 so `/mnt/youtubarr` is no longer occupied by the old FUSE process. Keep any old config/library data until the new stack is confirmed working if you want an easy rollback.

Run the v1 host installer before deploying the Portainer Git stack. It replaces the old `youtubarr-fuse-prep.service` with `youtubarr-mount.service` and preserves unrelated mounts/Zurg.
