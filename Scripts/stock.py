"""Compare CFW/rootfs.img in both local installers with the device library index, read-only."""
import argparse
import csv
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from pathlib import Path


def at(f, offset, size):
    f.seek(offset)
    data = f.read(size)
    if len(data) != size:
        raise ValueError("Truncated image")
    return data


def extract_rootfs(disk, output):
    table = json.loads(subprocess.check_output(["sfdisk", "--json", disk]))["partitiontable"]
    part, = [p for p in table["partitions"] if p.get("name") == "ROMS"]
    base = part["start"] * table["sectorsize"]
    with disk.open("rb") as f:
        boot = at(f, base, 512)
        if boot[82:90] != b"FAT32   ":
            raise ValueError("Expected FAT32 ROMS partition")
        bps, spc, reserved, copies = struct.unpack_from("<HBHB", boot, 11)
        fat_size, = struct.unpack_from("<I", boot, 36)
        root, = struct.unpack_from("<I", boot, 44)
        fat = at(f, base + reserved * bps, fat_size * bps)
        first = base + (reserved + copies * fat_size) * bps
        size = bps * spc

        def clusters(n):
            seen = set()
            while n < 0x0ffffff8:
                if n < 2 or n >= len(fat)//4 or n in seen:
                    raise ValueError("Invalid FAT chain")
                yield n
                seen.add(n)
                n = struct.unpack_from("<I", fat, 4*n)[0] & 0x0fffffff

        def entry(start, name):
            for n in clusters(start):
                block = at(f, first + (n-2)*size, size)
                for i in range(0, size, 32):
                    e = block[i:i+32]
                    if e[0] == 0:
                        raise FileNotFoundError(name)
                    if e[11] != 0x0f and e[:11] == name:
                        return (int.from_bytes(e[20:22], "little") << 16 |
                                int.from_bytes(e[26:28], "little")), int.from_bytes(e[28:32], "little")
            raise FileNotFoundError(name)

        cfw, _ = entry(root, b"CFW        ")
        start, remaining = entry(cfw, b"ROOTFS  IMG")
        chain = list(clusters(start))
        with output.open("wb") as dst:
            i = 0
            while i < len(chain) and remaining:
                j = i+1
                while j < len(chain) and chain[j] == chain[j-1]+1 and j-i < 1024:
                    j += 1
                count = min(remaining, (j-i)*size)
                dst.write(at(f, first + (chain[i]-2)*size, count))
                remaining -= count
                i = j
        if remaining:
            raise ValueError("Short FAT file")


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def examine(img, hashes):
    env = {**os.environ, "LC_ALL": "C"}
    def debug(command, raw=False):
        return subprocess.run(["debugfs", *(["-n"] if raw else []), "-R", command, img],
                              capture_output=True, env=env, check=True)
    fsck = subprocess.run(["e2fsck", "-fn", img], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    result = dict(fsck_exit=fsck.returncode, fsck=fsck.stdout.decode().replace(str(img), "rootfs.img"), entries={})
    for name in ("libintl.so", "libjson-c.so", "libintl.so.8.1.5", "libjson-c.so.3.0.1"):
        path = "/usr/lib/" + name
        stat = debug("stat " + path)
        checked = (stat.stdout + stat.stderr).decode()
        item = dict(stat=checked)
        if path in hashes:
            data = debug("cat " + path).stdout
            if not data.startswith(b"\x7fELF"):
                raise ValueError("Failed to read ELF: " + path)
            item.update(bytes=len(data), stock_sha256=hashlib.sha256(data).hexdigest(), device_sha256=hashes[path])
            item["matches_device"] = item["stock_sha256"] == item["device_sha256"]
        else:
            item["unchecked_stat"] = debug("stat " + path, raw=True).stdout.decode()
        result["entries"][name] = item
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("installers", type=Path)
    ap.add_argument("inventory", type=Path)
    ap.add_argument("report", type=Path)
    a = ap.parse_args()
    files = a.installers / "RG35XX-CopyPasteOnTopOfStock/roms/CFW/rootfs.img"
    disk = a.installers / "RG35XX-MicroSDCardImage/garlic.img"
    with a.inventory.open() as f:
        hashes = {r["path"]: r["sha256"] for r in csv.DictReader(f, delimiter="\t")
                  if r["root"] == "garlic" and r["type"] == "ELF"}
    with tempfile.TemporaryDirectory() as tmp:
        inner = Path(tmp) / "rootfs.img"
        extract_rootfs(disk, inner)
        report = dict(copy_paste_sha256=sha(files), micro_sd_sha256=sha(inner))
        report["copy_paste"] = examine(files, hashes)
        if report["copy_paste_sha256"] != report["micro_sd_sha256"]:
            report["micro_sd"] = examine(inner, hashes)
        a.report.write_text(json.dumps(report, indent=2) + "\n")
        print(report["copy_paste_sha256"], report["micro_sd_sha256"], a.report)
