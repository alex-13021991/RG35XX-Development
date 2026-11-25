#!/bin/sh
set -eu
archive=$(realpath "${1:?Укажите архив zig-linux-x86_64-0.13.0.tar.xz}")
cache=${XDG_CACHE_HOME:-"$HOME/.cache"}/rg35xx-development
printf '%s  %s\n' d45312e61ebcc48032b77bc4cf7fd6915c11fa16e4aad116b66c9468211230ea "$archive" | sha256sum -c -
mkdir -p "$cache"
if [ ! -x "$cache/zig-linux-x86_64-0.13.0/zig" ]; then
    tar -xJf "$archive" -C "$cache"
fi
"$cache/zig-linux-x86_64-0.13.0/zig" version
