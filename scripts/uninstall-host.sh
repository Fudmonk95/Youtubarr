#!/usr/bin/env bash
set -Eeuo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run as root." >&2; exit 1; fi
systemctl disable --now youtubarr-mount.service 2>/dev/null || true
rm -f /etc/systemd/system/youtubarr-mount.service
systemctl daemon-reload
if [[ -r /mnt/youtubarr/.youtubarr.json ]]; then
  echo "A live Youtubarr FUSE mount is still present. Stop the Youtubarr container first." >&2
  exit 1
fi
if mountpoint -q /mnt/youtubarr && [[ -e /mnt/youtubarr/.youtubarr-host-mount ]]; then
  mount --make-private /mnt/youtubarr 2>/dev/null || true
  umount /mnt/youtubarr
fi
rm -f /mnt/youtubarr/.youtubarr-host-mount 2>/dev/null || true
echo "Host mount preparation removed. Config and library data were not deleted."
