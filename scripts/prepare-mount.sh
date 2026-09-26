#!/usr/bin/env bash
set -Eeuo pipefail
MOUNT_DIR="${YOUTUBARR_MOUNT_DIR:-/mnt/youtubarr}"
HOST_MARKER="$MOUNT_DIR/.youtubarr-host-mount"
FUSE_MARKER="$MOUNT_DIR/.youtubarr.json"

if [[ -r "$FUSE_MARKER" ]] && grep -q '"product"[[:space:]]*:[[:space:]]*"Youtubarr"' "$FUSE_MARKER" 2>/dev/null; then
  echo "Youtubarr FUSE is already mounted at $MOUNT_DIR; leaving the live read-only mount untouched."
  exit 0
fi

mkdir -p "$MOUNT_DIR"

if mountpoint -q "$MOUNT_DIR"; then
  fstype="$(findmnt -n -o FSTYPE --target "$MOUNT_DIR" 2>/dev/null || true)"
  if [[ "$fstype" == fuse* ]]; then
    echo "ERROR: An unrelated FUSE filesystem occupies $MOUNT_DIR." >&2
    echo "Stop/unmount it before using this path for Youtubarr." >&2
    exit 1
  fi
  if [[ ! -e "$HOST_MARKER" ]]; then
    echo "ERROR: $MOUNT_DIR is already a mountpoint and was not prepared by Youtubarr." >&2
    echo "Refusing to alter an unrelated mount." >&2
    exit 1
  fi
else
  touch "$HOST_MARKER"
  mount --bind "$MOUNT_DIR" "$MOUNT_DIR"
fi

mount --make-rshared "$MOUNT_DIR"
prop="$(findmnt -n -o PROPAGATION --target "$MOUNT_DIR" 2>/dev/null || true)"
echo "Prepared $MOUNT_DIR (propagation: ${prop:-unknown})."
