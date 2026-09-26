#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${YOUTUBARR_INSTALL_DIR:-/opt/youtubarr}"
LEGACY_UNIT="/etc/systemd/system/youtubarr-fuse-prep.service"

if [[ $EUID -ne 0 ]]; then
  echo "Run this installer as root (sudo)." >&2
  exit 1
fi

if [[ ! -e /dev/fuse ]]; then
  cat >&2 <<'EOF'
ERROR: /dev/fuse is missing on this Docker host.
If Docker is running inside a Proxmox LXC, enable FUSE on the PROXMOX HOST first.
Do not run pct commands inside the Debian LXC.
EOF
  exit 1
fi

mkdir -p "$INSTALL_DIR"

if [[ "$ROOT" != "$INSTALL_DIR" ]]; then
  echo "Installing Youtubarr files to $INSTALL_DIR"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude config \
      --exclude library \
      --exclude cache \
      "$ROOT/" "$INSTALL_DIR/"
  else
    echo "rsync not found; using cp fallback (existing config/library/cache are preserved)."
    cp -a "$ROOT/." "$INSTALL_DIR/"
  fi
fi

cd "$INSTALL_DIR"
[[ -f .env ]] || cp .env.example .env

# Fresh v1 replaces the old alpha sidecar-prep unit. Remove it so only the new
# shared-mount preparation runs on boot. This does not unmount or touch Zurg.
legacy_present=0
if [[ -e "$LEGACY_UNIT" ]] || systemctl list-unit-files youtubarr-fuse-prep.service --no-legend 2>/dev/null | grep -q youtubarr-fuse-prep; then
  legacy_present=1
  systemctl disable --now youtubarr-fuse-prep.service >/dev/null 2>&1 || true
  rm -f "$LEGACY_UNIT"
fi

# Adopt the safe self-bind created by Youtubarr alpha after the old container has
# been stopped. An active FUSE mount is never chmod/chowned or replaced here.
if [[ $legacy_present -eq 1 ]] && mountpoint -q /mnt/youtubarr 2>/dev/null && [[ ! -r /mnt/youtubarr/.youtubarr.json ]]; then
  fstype="$(findmnt -n -o FSTYPE --target /mnt/youtubarr 2>/dev/null | tail -n1 || true)"
  if [[ "$fstype" != fuse* ]]; then
    touch /mnt/youtubarr/.youtubarr-host-mount
    echo "Adopted existing Youtubarr alpha shared bind mount."
  fi
fi

# If PUID/PGID were left at defaults, prefer the invoking user's ids where available.
if grep -q '^PUID=1000$' .env && [[ -n "${SUDO_UID:-}" ]]; then
  sed -i "s/^PUID=.*/PUID=${SUDO_UID}/" .env
fi
if grep -q '^PGID=1000$' .env && [[ -n "${SUDO_GID:-}" ]]; then
  sed -i "s/^PGID=.*/PGID=${SUDO_GID}/" .env
fi

# Ensure packaged helper scripts are executable. Do not try to install a file over
# itself when the repository already lives at /opt/youtubarr.
chmod 0755 scripts/prepare-mount.sh \
           scripts/install-host.sh \
           scripts/uninstall-host.sh \
           scripts/doctor.sh \
           scripts/youtubarr

install -m 0644 systemd/youtubarr-mount.service /etc/systemd/system/youtubarr-mount.service
systemctl daemon-reload
systemctl enable --now youtubarr-mount.service

echo
echo "Host preparation complete."
echo "Youtubarr v1 uses ONE Compose service and ONE container."
echo "Deploy it with:"
echo "  cd $INSTALL_DIR && docker compose up -d --build"
echo "Then open: http://<server-ip>:$(grep '^YOUTUBARR_PORT=' .env | cut -d= -f2 || echo 8788)"
