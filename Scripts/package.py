"""Make a GarlicOS APPS ZIP from a validated ELF. Save output in its app folder."""
import argparse
import re
import tarfile
import tempfile
import zipfile
from pathlib import Path

from abi import verify


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary", type=Path)
    ap.add_argument("name", help="ASCII app directory and menu entry")
    ap.add_argument("--sysroot", required=True, type=Path)
    ap.add_argument("--zip", required=True, type=Path)
    args = ap.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.name):
        raise ValueError("Недопустимое имя приложения")
    with tempfile.TemporaryDirectory() as tmp:
        root = args.sysroot
        if root.is_file():
            with tarfile.open(root) as archive:
                root = Path(tmp)
                archive.extractall(root, filter="data")
        verify(args.binary, root)
    folder = "Roms/APPS/" + args.name
    launcher = f'#!/bin/sh\ncd "$(dirname "$0")/{args.name}" || exit 1\nexec ./program >run.log 2>&1\n'
    args.zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip, "x", zipfile.ZIP_DEFLATED) as z:
        z.write(args.binary, folder + "/program")
        z.writestr(folder + ".sh", launcher)
        if z.testzip():
            raise ValueError("Ошибка CRC в ZIP")
    print(args.zip)


if __name__ == "__main__":
    main()
