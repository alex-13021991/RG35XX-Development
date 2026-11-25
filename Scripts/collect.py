"""Read a Linux/CFW snapshot over ADB. All output files are on the host."""
import argparse
import base64
import gzip
import hashlib
import io
import json
import shlex
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from device import BUSY, ROOT, Device

PRE = r'''
B=/system/bin/busybox
files() { for p do [ -f "$p" ] || continue; echo "--- $p"; "$B" cat "$p"; echo; done; }
dirs() { for p do [ -d "$p" ] || continue; echo "--- $p"; "$B" ls -1 "$p/"; done; }
hex() { for p do [ -f "$p" ] || continue; echo "--- $p"; "$B" hexdump -v -e '1/1 "%02x"' "$p"; echo; done; }
cfw() { "$B" chroot /cfw /bin/busybox env PATH=/bin:/sbin:/usr/bin:/usr/sbin "$@"; }
'''
PROBES = {
    "cpu": """files /proc/cpuinfo /sys/devices/system/cpu/possible /sys/devices/system/cpu/present
        files /sys/devices/system/cpu/online /sys/devices/system/cpu/cpu0/cpufreq/*freq*
        files /sys/devices/system/cpu/cpu0/cpufreq/scaling_* /sys/devices/system/cpu/cpufreq/interactive/target_loads""",
    "memory": """files /proc/meminfo /proc/iomem /sys/kernel/debug/memblock/memory /sys/kernel/debug/memblock/reserved
        hex /proc/device-tree/memory/reg /proc/device-tree/reserved/*/*_size""",
    "kernel": """files /proc/version /proc/cmdline /proc/modules /proc/filesystems
        dirs /lib/modules /misc/modules /cfw/lib/modules
        if [ -r /proc/config.gz ]; then "$B" zcat /proc/config.gz; else echo '/proc/config.gz unavailable'; fi""",
    "storage": """files /proc/partitions /proc/mounts /sys/block/loop0/loop/backing_file
        "$B" df -k; dirs / /cfw /mnt/mmc /mnt/SDCARD /mnt/mmc/CFW""",
    "graphics": """files /proc/fb /sys/class/graphics/fb*/name /sys/class/graphics/fb*/bits_per_pixel /sys/class/graphics/fb*/stride /sys/class/graphics/fb*/virtual_size /sys/class/graphics/fb*/mode /sys/class/graphics/fb*/modes
        for p in /dev/fb* /dev/graphics/* /dev/dri/* /dev/pvrsrvkm /proc/pvr/* /sys/bus/platform/drivers/*gpu*; do [ ! -e "$p" ] || "$B" ls -ld "$p"; done
        hex /proc/device-tree/gpu@*/compatible /proc/device-tree/gpu@*/status
        dirs /sys/devices/platform /sys/kernel/debug/owl""",
    "audio": """files /proc/asound/version /proc/asound/cards /proc/asound/devices /proc/asound/pcm /sys/class/volume/value
        dirs /dev/snd /sys/kernel/debug/asoc; cfw /usr/bin/aplay -l; cfw /usr/bin/aplay -L""",
    "input": """files /proc/bus/input/devices /sys/class/input/input*/name /sys/class/input/input*/capabilities/*
        dirs /dev/input; /system/bin/getevent -p -c 0 </dev/null & p=$!; "$B" sleep 1; kill "$p" 2>/dev/null; wait "$p" 2>/dev/null
        cfg=/mnt/mmc/CFW/retroarch/.retroarch/retroarch.cfg
        "$B" grep -E '^input_player1_.*_(btn|axis) =' "$cfg"; :""",
    "usb": """files /sys/class/android_usb/android0/functions /sys/class/android_usb/android0/enable /sys/class/android_usb/android0/state /sys/class/android_usb/android0/idVendor /sys/class/android_usb/android0/idProduct
        dirs /sys/class/android_usb /sys/class/udc
        "$B" ps | "$B" grep -E '[m]tp-server|[a]dbd'; files /misc/usb.sh /mnt/mmc/CFW/autostart/mtp.sh""",
    "power": """files /sys/class/power_supply/*/uevent /sys/class/power_supply/battery/moto /sys/power/state /sys/class/thermal/thermal_zone*/type /sys/class/thermal/thermal_zone*/temp /sys/class/backlight/*/actual_brightness
        dirs /sys/class/timed_output /sys/class/power_supply/battery""",
    "garlic": """files /cfw/etc/cfw-info /cfw/usr/lib/os-release /cfw/etc/profile /mnt/mmc/CFW/start /misc/dmenu.bin
        dirs /mnt/mmc/CFW/autostart /mnt/mmc/CFW/config
        "$B" strings /mnt/mmc/CFW/main | "$B" grep -E '^GarlicOS|^1[.]4[.][0-9]+$'
        for pid in $("$B" pidof main); do "$B" readlink /proc/$pid/root; "$B" readlink /proc/$pid/cwd
          "$B" tr '\\000' '\\n' </proc/$pid/environ | "$B" grep -E '^(HOME|SDL_[A-Z_]+|LD_LIBRARY_PATH|PATH)='
          "$B" cat /proc/$pid/maps | "$B" awk 'NF>=6 {print $6}' | "$B" sort -u
        done""",
    "diagnostics": """ "$B" dmesg | "$B" grep -iE 'EXT4-fs error|checksum invalid|Memory:|reserved memory|PowerVR|pvrsrvkm' | "$B" tail -100""",
}


def archive(dev, out, paths):
    args = " ".join(map(shlex.quote, paths))
    # shell v1 allocates a PTY. ASCII armour survives CR/LF translation.
    # fd 3 carries data, stderr stays separate including tar's completion status.
    script = f"""B={BUSY}; cd / || exit 1; exec 3>&1
msg=$( {{ {{ "$B" tar -cf - {args}; echo TAR_RC=$? >&2; }} | "$B" gzip -1 | "$B" uuencode -m dump >&3; }} 2>&1 )
echo "$msg"
"""
    body = dev.raw(script, timeout=600).replace(b"\r", b"")
    header, found, rest = body.partition(b"\n")
    data, end, notes = rest.partition(b"\n====\n")
    if not found or header != b"begin-base64 666 dump" or not end:
        raise RuntimeError("Неполный поток архива: " + repr(body[:150]))
    packed = base64.b64decode(b"".join(data.splitlines()), validate=True)
    unpacked = gzip.decompress(packed)
    with tarfile.open(fileobj=io.BytesIO(unpacked)) as tar:
        members = tar.getmembers()
    if not members or not unpacked.endswith(bytes(1024)):
        raise RuntimeError("Неполный tar")
    out.write_bytes(packed)
    return dict(sha256=hashlib.sha256(packed).hexdigest(), members=len(members),
                sources=paths, report=notes.decode().strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--libraries", action="store_true")
    args = parser.parse_args()
    dev = Device()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = ROOT / "HardwareDump" / stamp
    target.mkdir(parents=True)
    for name, commands in PROBES.items():
        result = dev.shell(PRE + commands + "\n:", timeout=60)
        (target / (name + ".txt")).write_text(result)
    print(target, flush=True)
    if args.libraries:
        lib = ROOT / "SystemLibraries"
        lib.mkdir(exist_ok=True)
        bundles = {"garlic": ["cfw/lib", "cfw/usr/lib"],
                   "base": ["lib", "usr/lib", "system/lib", "system/usr/lib", "system/usr/local/lib"],
                   "boot": ["misc/uImage", "misc/kernel.dtb", "misc/modules", "mnt/mmc/CFW/main"]}
        metadata = {}
        for name, paths in bundles.items():
            path = (target if name == "boot" else lib) / (stamp + "-" + name + ".tar.gz")
            metadata[name] = archive(dev, path, paths)
            (target / "archives.json").write_text(json.dumps(metadata, indent=2) + "\n")
            print(name, metadata[name]["members"], metadata[name]["report"], flush=True)


if __name__ == "__main__":
    main()
