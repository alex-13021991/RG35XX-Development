"""Host-side connection to GarlicOS, including legacy adbd without shell_v2."""
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSY = "/system/bin/busybox"


class Device:
    def __init__(self):
        adb = os.environ.get("ADB") or shutil.which("adb") or "/mnt/c/ADB/adb.exe"
        rows = subprocess.check_output([adb, "devices"], text=True).splitlines()[1:]
        devices = [r.split()[0] for r in rows if r.split()[1:] == ["device"]]
        serial = os.environ.get("ANDROID_SERIAL")
        if serial is None and len(devices) == 1:
            serial = devices[0]
        if serial not in devices:
            raise SystemExit("Проверьте adb devices и при необходимости задайте ANDROID_SERIAL.")
        self.adb = [adb, "-s", serial]
        identity = self.shell("cat /proc/cpuinfo; ls -d /cfw/lib /mnt/mmc/CFW/start")
        if not re.search(r"Hardware\s*:\s*gs705a\b", identity) or "/cfw/lib" not in identity:
            raise SystemExit("Не подтверждены gs705a и файловая система GarlicOS.")

    def raw(self, script, timeout=90):
        cmd = self.adb + ["shell", BUSY + " sh -c " + shlex.quote(script)]
        return subprocess.check_output(cmd, timeout=timeout)

    def shell(self, script, timeout=90):
        script += '\nrc=$?; printf "\\n__RG_EXIT=%s\\n" "$rc"'
        data = self.raw(script, timeout).replace(b"\r", b"").decode("utf-8", "replace")
        body, marker, status = data.rpartition("__RG_EXIT=")
        if not marker or status.strip() != "0":
            raise RuntimeError(body[-700:] + " " + status)
        return re.sub(r"\x1b\[[0-9;]*m", "", body).rstrip() + "\n"
