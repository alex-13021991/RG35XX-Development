#!/usr/bin/env bash
# Read-only ELF inspection; does not execute target binaries.
set -euo pipefail
export LC_ALL=C
if [[ $# != 2 ]]; then echo "Usage: $0 INPUT_DIRECTORY OUTPUT_DIRECTORY" >&2; exit 2; fi
in=$(realpath "$1"); mkdir -p "$2"; out=$(realpath "$2")
[[ "$in" != "$out" ]] || { echo 'Choose separate output directory' >&2; exit 2; }
for tool in file readelf sha256sum strings; do command -v "$tool" >/dev/null || exit 3; done
shopt -s nullglob
files=("$in"/*)
((${#files[@]})) || { echo 'No files' >&2; exit 4; }
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  readelf -h "$f" >/dev/null 2>&1 || continue
  n=${f##*/}
  {
    file "$f"
    sha256sum "$f"
    for flag in -h -A -l -S -d -V -Ws; do echo "==== readelf $flag ===="; readelf "$flag" "$f"; done
    readelf -p .comment "$f" 2>&1 || true
  } > "$out/$n.txt"
  if [[ "$n" == libSDL* ]]; then
    strings "$f" | grep -E '/opt/miyoo|buildroot-2018|GCC:|hg-[0-9]+' | sort -u > "$out/$n.build-strings.txt" || true
    if command -v llvm-objdump >/dev/null; then
      llvm-objdump -d --disassemble-symbols=SDL_Linked_Version,SDL_GetVersion_REAL,SDL_GetNumVideoDrivers_REAL,SDL_GetNumAudioDrivers_REAL,SDL_GetNumRenderDrivers_REAL "$f" > "$out/$n.disassembly.txt" 2>&1 || true
    fi
  fi
done
