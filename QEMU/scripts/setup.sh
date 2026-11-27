#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for tool in python3 qemu-arm proot tar; do
  command -v "$tool" >/dev/null || { echo "Установите: sudo apt-get update && sudo apt-get install qemu-user proot python3 python3-tk" >&2; exit 1; }
done
archive=${1:-}
if [[ ! -f runtime/lib/ld-uClibc.so.0 ]]; then
  if [[ -z "$archive" ]]; then
    for candidate in ../Sysroot/20261125T155126Z-sysroot.tar.gz ../RG35XX-Development/Sysroot/20261125T155126Z-sysroot.tar.gz; do
      if [[ -f "$candidate" ]]; then archive=$candidate; break; fi
    done
  fi
  [[ -n "$archive" && -f "$archive" ]] || { echo "Укажите архив sysroot: ./scripts/setup.sh /path/to/20261125T155126Z-sysroot.tar.gz" >&2; exit 1; }
  python3 scripts/unpack-runtime.py "$archive"
fi
scripts/build.sh
./rg35xx run --session setup-probe --exec probe --headless --seconds 20
cat state/setup-probe/console.log
