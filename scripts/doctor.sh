#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
fail=0
ok(){ printf '\033[32m[OK]\033[0m %s\n' "$*"; }
bad(){ printf '\033[31m[FAIL]\033[0m %s\n' "$*"; fail=1; }
info(){ printf '\033[36m[INFO]\033[0m %s\n' "$*"; }

[[ -e /dev/fuse ]] && ok "/dev/fuse exists" || bad "/dev/fuse is missing"
[[ -d /mnt/youtubarr ]] && ok "/mnt/youtubarr exists" || bad "/mnt/youtubarr does not exist"
prop="$(findmnt -n -o PROPAGATION --target /mnt/youtubarr 2>/dev/null || true)"
[[ "$prop" == *shared* ]] && ok "/mnt/youtubarr propagation is $prop" || bad "/mnt/youtubarr is not shared/rshared (reported: ${prop:-none})"
if docker compose config --services 2>/dev/null | grep -qx youtubarr && [[ "$(docker compose config --services 2>/dev/null | wc -l)" -eq 1 ]]; then ok "Compose contains exactly one service/container"; else bad "Compose must contain exactly one service: youtubarr"; fi
if docker compose ps --status running --services 2>/dev/null | grep -qx youtubarr; then ok "Youtubarr container is running"; else info "Youtubarr container is not running yet"; fi
if [[ -r /mnt/youtubarr/.youtubarr.json ]]; then ok "Youtubarr FUSE marker is visible on the host"; else info "FUSE marker is not visible (expected until the container starts)"; fi
if command -v curl >/dev/null && curl -fsS "http://127.0.0.1:${YOUTUBARR_PORT:-8788}/api/bootstrap" >/dev/null 2>&1; then ok "Youtubarr web API responds"; else info "Web API not reachable on localhost:${YOUTUBARR_PORT:-8788}"; fi
exit "$fail"
