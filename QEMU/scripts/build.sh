#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
toolchain=${RG_TOOLCHAIN:-"$HOME/RG35XX/RG35XX-SDK/miyoo-gcc-7.3.0"}
export LD_LIBRARY_PATH="$toolchain/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cc="$toolchain/bin/arm-miyoo-linux-uclibcgnueabi-gcc"
flags=(--sysroot="$PWD/runtime" -mcpu=cortex-a9 -mfpu=neon -mfloat-abi=softfp -O2 -Wall -Wextra)
mkdir -p build
"$cc" "${flags[@]}" -fPIC -shared src/devices.c -ldl -o build/devices.so
"$cc" "${flags[@]}" src/demo.c -o build/demo -Wl,-dynamic-linker,/lib/ld-uClibc.so.0
"$cc" "${flags[@]}" tests/probe.c -o build/probe -ldl -Wl,-dynamic-linker,/lib/ld-uClibc.so.0
