"""Assemble C development files from Miyoo 7.3.0 and runtime objects from one device snapshot."""
import argparse
import hashlib
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

from device import ROOT

DEFAULT_SDK = Path.home() / "rg35xx-sdk/miyoo-gcc-7.3.0"
TRIPLE = "arm-miyoo-linux-uclibcgnueabi"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("runtime", type=Path)
    ap.add_argument("--sdk", type=Path, default=DEFAULT_SDK)
    args = ap.parse_args()
    sdk = args.sdk / TRIPLE / "sysroot"
    out = ROOT / "Sysroot" / args.runtime.name.replace("-garlic.", "-sysroot.")
    if out.name == args.runtime.name:
        raise SystemExit("Expected *-garlic.tar.gz")
    out.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        with tarfile.open(args.runtime) as tar:
            for m in tar:
                rel = Path(m.name).relative_to("cfw")
                if ".." in rel.parts or rel.is_absolute() or ".so" not in rel.name or "modules" in rel.parts:
                    continue
                p = target / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                if m.issym():
                    link = Path(m.linkname)
                    if link.is_absolute():
                        link = Path(os.path.relpath(target / link.relative_to("/"), p.parent))
                    (p.parent / link).resolve().relative_to(target)
                    p.symlink_to(link)
                elif m.isfile():
                    p.write_bytes(tar.extractfile(m).read())
                    p.chmod(0o755)
        libc = Path("lib/libuClibc-1.0.28.so")
        if not (target / libc).is_file() or not (sdk / libc).is_file():
            raise SystemExit("Требуются uClibc 1.0.28 на устройстве и в SDK.")
        headers = target / "usr/include"
        shutil.copytree(sdk / "usr/include", headers, symlinks=False)
        cpp = args.sdk / TRIPLE / "include/c++/7.3.0"
        shutil.copytree(cpp, headers / "c++/7.3.0", symlinks=False, dirs_exist_ok=True)
        dev = target / "usr/lib"
        for src in sorted((sdk / "usr/lib").glob("*.so")):
            dest = dev / src.name
            if src.is_symlink() and not os.path.lexists(dest):
                link = Path(os.readlink(src))
                if len(link.parts) == 1 and (dev / link).is_file():
                    dest.symlink_to(link)
                    print("SDK linker alias:", dest.name, "->", link)
        names = ("*.o", "*nonshared.a", "libdl.a", "libm.a", "libpthread.a", "librt.a", "libc.so")
        for pattern in names:
            for src in (sdk / "usr/lib").glob(pattern):
                dest = dev / src.name
                if not os.path.lexists(dest):
                    shutil.copy2(src, dest)
        with tarfile.open(out.with_suffix(".partial"), "w:gz", compresslevel=3) as archive:
            for folder in ("lib", "usr"):
                archive.add(target / folder, arcname=folder)
        out.with_suffix(".partial").replace(out)
        print("libc target/SDK SHA-256:")
        for p in (target / libc, sdk / libc):
            print(hashlib.sha256(p.read_bytes()).hexdigest())
        print(out)


if __name__ == "__main__":
    main()
