"""Build and validate a C or C++ executable with a measured toolchain in WSL."""
import argparse
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from abi import verify
from device import ROOT
from sysroot import DEFAULT_SDK, TRIPLE


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("--tool", choices=["gcc7", "gcc9", "zig"], required=True)
    ap.add_argument("--sysroot", required=True, type=Path, help="Directory or .tar.gz made by sysroot.py")
    ap.add_argument("--sdk", type=Path, help="GCC SDK directory; for Zig use Miyoo GCC 7.3.0 for crt/libgcc")
    ap.add_argument("--zig", default=shutil.which("zig") or "zig")
    ap.add_argument("--lib", action="append", default=[], help="Additional -l library, repeat as needed")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    sdk = (args.sdk or (Path("/opt/miyoo") if args.tool == "gcc9" else DEFAULT_SDK)).resolve()
    gcc = sdk / "bin" / (TRIPLE + "-gcc")
    env = dict(os.environ, LC_ALL="C", LD_LIBRARY_PATH=str(sdk / "lib"))
    version = subprocess.check_output([gcc, "-dumpfullversion"], env=env, text=True).strip()
    expected = "9.4.0" if args.tool == "gcc9" else "7.3.0"
    if version != expected:
        raise SystemExit(f"{gcc}: {version}, expected {expected}")
    gcc_lib = sdk / "lib/gcc" / TRIPLE / version
    log = []
    def command(argv):
        log.append(list(map(str, argv)))
        subprocess.run(argv, check=True, env=env)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        sysroot = args.sysroot.resolve()
        if sysroot.is_file():
            with tarfile.open(sysroot) as archive:
                sysroot = tmp / "root"
                archive.extractall(sysroot, filter="data")
        dest = args.out.resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        cc = [gcc]
        ld = [sdk / "bin" / (TRIPLE + "-ld")]
        if args.tool == "zig":
            zig = str(Path(shutil.which(args.zig) or args.zig).resolve())
            version = subprocess.check_output([zig, "version"], text=True).strip()
            if version != "0.13.0":
                raise SystemExit("Expected Zig 0.13.0")
            cc = [zig, "cc", "-target", "arm-linux-gnueabi", "-mcpu=cortex_a9", "-nostdinc",
                  "-isystem", sysroot / "usr/include", "-isystem", Path(zig).parent / "lib/include"]
            ld = [zig, "ld.lld"]
        else:
            cc += ["-mcpu=cortex-a9"]
        common = ["--sysroot=" + str(sysroot), "-Os", "-marm", "-mfpu=neon-fp16",
                  "-mfloat-abi=softfp", "-ffunction-sections", "-fdata-sections", "-fno-stack-protector",
                  "-fno-pie", "-D_GNU_SOURCE", "-Wall", "-Wextra"]
        objs = []
        cpp_headers = sysroot / "usr/include/c++/7.3.0"
        has_cpp = False
        for i, source in enumerate(args.sources):
            obj = tmp / f"unit{i}.o"
            lang = ["-std=gnu99"]
            if source.suffix in (".cpp", ".cc", ".cxx", ".C"):
                has_cpp = True
                lang = ["-x", "c++", "-std=gnu++11", "-nostdinc++", "-isystem", cpp_headers,
                        "-isystem", cpp_headers / TRIPLE, "-isystem", cpp_headers / "backward"]
            command(cc + common + lang + ["-c", source.resolve(), "-o", obj])
            objs.append(obj)
        lib = sysroot / "usr/lib"
        rt = sysroot / "lib"
        command(ld + ["-s", "--gc-sections", "-m", "armelf_linux_eabi", "--sysroot=" + str(sysroot),
                      "-dynamic-linker", "/lib/ld-uClibc.so.0", "-o", tmp / "program",
                      lib / "crt1.o", lib / "crti.o", gcc_lib / "crtbegin.o", *objs,
                      "-L" + str(lib), "-L" + str(rt), "-L" + str(gcc_lib),
                      "-rpath-link", str(lib), "-rpath-link", str(rt), "--as-needed", "--start-group",
                      *["-l" + name for name in args.lib], *(["-lstdc++", "-lgcc_s"] if has_cpp else []),
                      "-lc", "-lgcc", "--end-group",
                      gcc_lib / "crtend.o", lib / "crtn.o"])
        report = verify(tmp / "program", sysroot)
        shutil.copy2(tmp / "program", dest)
        Path(str(dest) + ".abi.txt").write_text(report)
        Path(str(dest) + ".build.json").write_text(json.dumps(dict(version=version, commands=log), indent=2))
        print(dest, dest.stat().st_size, "bytes; ABI OK")


if __name__ == "__main__":
    main()
