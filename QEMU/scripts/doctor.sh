#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
qemu-arm --version | head -1
proot --version | tail -5
python3 --version
test -f build/devices.so
test -f runtime/lib/ld-uClibc.so.0
readelf -h build/demo | head -20
sha256sum runtime/lib/libuClibc-1.0.28.so
printf 'DISPLAY=%s WAYLAND_DISPLAY=%s\n' "${DISPLAY:-}" "${WAYLAND_DISPLAY:-}"
if command -v qemu-system-arm >/dev/null; then
  echo 'RG35XX/Actions/Owl board matches (normally none):'
  qemu-system-arm -machine help | grep -Ei 'rg35|actions|owl|gs705|atm7039' || true
fi
