"""Check the ELF interpreter, ARM ABI, shared objects and dynamic imports in a target root."""
import argparse
import re
from pathlib import Path

from inventory import readelf


def verify(binary, root):
    info = readelf(binary, "-h", "-l", "-d", "-A")
    for expected in ("ELF32", "little endian", "Machine:                           ARM", "Version5 EABI"):
        if expected not in info:
            raise ValueError("ELF: missing " + expected)
    interp = re.search(r"Requesting program interpreter: (.*?)\]", info)
    if not interp or interp[1] not in ("/lib/ld-uClibc.so.0", "/lib/ld-uClibc.so.1"):
        raise ValueError("Unsupported GarlicOS interpreter")
    loader = root / interp[1][1:]
    todo = [binary, loader]
    seen, exports, imports = set(), set(), set()
    while todo:
        obj = todo.pop().resolve(strict=True)
        if obj in seen:
            continue
        seen.add(obj)
        data = readelf(obj, "-h", "-d", "-A")
        if "hard-float ABI" in data or "Tag_ABI_VFP_args: VFP registers" in data:
            raise ValueError("VFP calling convention: " + obj.name)
        for lib in re.findall(r"\(NEEDED\).*?\[(.*?)\]", data):
            paths = [root / folder / lib for folder in ("lib", "usr/lib")]
            match = next((p for p in paths if p.is_file()), None)
            if not match:
                raise ValueError(f"{obj.name}: missing {lib}")
            todo.append(match)
        for line in readelf(obj, "--dyn-syms").splitlines():
            cols = line.split()
            if len(cols) < 8 or not cols[0].rstrip(":").isdigit():
                continue
            bind, vis, index, sym = cols[4:8]
            if index == "UND" and bind == "GLOBAL":
                imports.add(sym)
            elif index != "UND" and bind in ("GLOBAL", "WEAK", "UNIQUE") and vis in ("DEFAULT", "PROTECTED"):
                exports.add(sym.replace("@@", "@"))
                if "@@" in sym:
                    exports.add(sym.split("@")[0])
    missing = sorted(imports - exports)
    if missing:
        raise ValueError("Unresolved strong imports: " + ", ".join(missing))
    return info + "\nDependency closure:\n" + "\n".join(sorted(p.name for p in seen)) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary", type=Path)
    ap.add_argument("sysroot", type=Path)
    a = ap.parse_args()
    print(verify(a.binary, a.sysroot))
