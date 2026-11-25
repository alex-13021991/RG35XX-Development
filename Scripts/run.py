"""Run a local ARM executable in a unique RAM directory; stream a log to the PC."""
import argparse
import os
import shlex
import subprocess
import uuid
from pathlib import Path

from device import BUSY, Device


def run(binary, log):
    dev = Device()
    mounts = dev.shell("cat /proc/mounts").splitlines()
    if not any(row.split()[1:3] == ["/cfw/dev", "tmpfs"] for row in mounts):
        raise SystemExit("Ожидался tmpfs в /cfw/dev.")
    folder = "/dev/shm/rg35xx-" + uuid.uuid4().hex
    remote = "/cfw" + folder
    winadb = dev.adb[0].lower().endswith(".exe") and os.name == "posix"
    local = subprocess.check_output(["wslpath", "-w", binary.resolve()], text=True).strip() if winadb else str(binary)
    dev.shell(f"umask 077; mkdir {remote}")
    try:
        subprocess.run(dev.adb + ["push", local, remote + "/program"], check=True, stdout=subprocess.DEVNULL)
        script = (f"chmod 700 {remote}/program && cd {remote} && "
                  f"{BUSY} chroot /cfw /bin/busybox env HOME={folder} TMPDIR={folder} "
                  f"PATH=/bin:/usr/bin:/sbin:/usr/sbin LD_LIBRARY_PATH=/lib:/usr/lib SDL_NOMOUSE=1 "
                  f"LD_BIND_NOW=1 {folder}/program")
        cmd = dev.adb + ["shell", BUSY + " sh -c " + shlex.quote(script + '; echo __RG_EXIT=$?')]
        log.parent.mkdir(parents=True, exist_ok=True)
        status = None
        with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc, log.open("w") as stream:
            for raw in proc.stdout:
                line = raw.replace(b"\r", b"").decode("utf8", "replace")
                stream.write(line)
                stream.flush()
                print(line, end="", flush=True)
                if line.startswith("__RG_EXIT="):
                    status = line.strip().split("=")[1]
            if proc.wait() or status != "0":
                raise RuntimeError("Ошибка выполнения; см. " + str(log))
    finally:
        dev.shell(f"rm -f {remote}/program && rmdir {remote}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("binary", type=Path)
    ap.add_argument("log", type=Path)
    a = ap.parse_args()
    run(a.binary, a.log)
