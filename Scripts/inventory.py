"""Index paths, symlinks, ELF attributes, dependencies and symbols from the acquisition."""
import argparse
import csv
import gzip
import hashlib
import os
import re
import subprocess
import tarfile
import tempfile
import zlib
from pathlib import Path

from device import ROOT


def readelf(path, *flags):
    return subprocess.check_output(["readelf", "-W", *flags, path], text=True,
                                   errors="replace", env={**os.environ, "LC_ALL": "C"})


def kernel(archive, out):
    with tarfile.open(archive) as tar:
        raw = tar.extractfile("misc/uImage").read()
    images = [raw]
    for match in re.finditer(b"\x1f\x8b\x08", raw):
        try:
            images.append(zlib.decompress(raw[match.start():], wbits=31))
        except zlib.error:
            continue
    for blob in images:
        start = blob.find(b"IKCFG_ST\x1f\x8b")
        if start >= 0:
            config = zlib.decompress(blob[start + 8:], wbits=31)
            (out / "kernel.config").write_bytes(config)
            return
    print("В uImage и его gzip-потоках секция IKCONFIG не обнаружена.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("snapshot", type=Path)
    args = ap.parse_args()
    out = args.snapshot.resolve()
    with (out / "libraries.tsv").open("w", newline="") as table, \
            gzip.open(out / "elf-symbols.txt.gz", "wt") as symbols, tempfile.TemporaryDirectory() as tmp:
        writer = csv.writer(table, delimiter="\t", lineterminator="\n")
        writer.writerow(["root", "path", "type", "link", "bytes", "sha256", "SONAME", "NEEDED", "ARM float ABI"])
        for scope in ("garlic", "base"):
            bundle = ROOT / "SystemLibraries" / f"{out.name}-{scope}.tar.gz"
            with tarfile.open(bundle) as tar:
                for member in tar:
                    if member.isdir():
                        continue
                    path = "/" + member.name.removeprefix("cfw/") if scope == "garlic" else "/" + member.name
                    row = [scope, path]
                    if not member.isfile():
                        writer.writerow(row + ["link", member.linkname, "", "", "", "", ""])
                        continue
                    data = tar.extractfile(member).read()
                    elf = data.startswith(b"\x7fELF")
                    info = ""
                    if elf:
                        copy = Path(tmp) / "object"
                        copy.write_bytes(data)
                        info = readelf(copy, "-h", "-d", "-A")
                        symbols.write(f"\n## {scope} {path}\n{info}\n" + readelf(copy, "--dyn-syms", "-V"))
                    so = re.findall(r"\(SONAME\).*?\[(.*?)\]", info)
                    needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", info)
                    abi = re.findall(r"(soft|hard)-float ABI", info)
                    writer.writerow(row + ["ELF" if elf else "file", "", len(data), hashlib.sha256(data).hexdigest(),
                                           ",".join(so), ",".join(needed), ",".join(abi)])
    kernel(out / f"{out.name}-boot.tar.gz", out)


if __name__ == "__main__":
    main()
