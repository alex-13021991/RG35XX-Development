# 05. ADB и команды диагностики

Google Platform Tools: https://developer.android.com/tools/releases/platform-tools ; официальный ZIP Windows https://dl.google.com/android/repository/platform-tools-latest-windows.zip . В исследовании использован ADB 1.0.41 / 37.0.3-16887417, C:\ADB\adb.exe, Windows 10.0.19044. Включить ADB на приставке через USB Mode Manager, подключить порт передачи данных.

## PowerShell

```powershell
cd C:\ADB
.\adb.exe version
.\adb.exe devices -l
.\adb.exe shell
```

В базовой оболочке `root@q88_hd:/ #`:

```sh
cat /proc/version
cat /proc/cpuinfo
cat /proc/meminfo
cat /proc/partitions
cat /proc/modules
mount
dmesg | grep -i ext4
cat /sys/block/loop0/loop/backing_file
cat /sys/block/loop7/loop/backing_file
/system/bin/busybox df -k /cfw
ls -l /cfw/usr/lib/libintl.so /cfw/usr/lib/libjson-c.so
/system/bin/busybox chroot /cfw /bin/sh
```

В GarlicOS (`/ #`):

```sh
export PATH=/bin:/sbin:/usr/bin:/usr/sbin
uname -a
busybox | head -n 5
df -k /
cat /etc/os-release
cat /etc/issue
```

Войти сразу из PowerShell: `.\adb.exe shell -t "/system/bin/busybox chroot /cfw /bin/sh"`. Проверено. Для выхода `exit` отдельной строкой; при необходимости повторить до `PS C:\ADB>`. Не выполнять Windows-команды в Linux. Во время исследования многострочная вставка иногда склеивала команды с выводом; вводить по одной строке или запускать отдельные adb shell из PowerShell. BusyBox 1.14.3 не поддерживает --list (без аргументов выводит список). Внутри GarlicOS BusyBox 1.27.2 поддерживает --list.

## Диагностика внутри GarlicOS

```sh
cat /sys/devices/system/cpu/online
for f in /sys/devices/system/cpu/cpu0/cpufreq/*; do if [ -f "$f" ]; then echo "==== $f ===="; cat "$f"; fi; done
cat /proc/fb
cat /sys/class/graphics/fb0/name
cat /sys/class/graphics/fb0/virtual_size
cat /sys/class/graphics/fb0/bits_per_pixel
cat /sys/class/graphics/fb0/stride
cat /sys/class/graphics/fb0/modes
ls -l /dev/graphics /dev/dri /usr/lib/dri
cat /proc/asound/cards
cat /proc/asound/devices
aplay -l
aplay -L
cat /proc/bus/input/devices
ls -l /dev/input /dev/snd
ls -l /lib /usr/lib /usr/bin /usr/sbin
ldd /usr/lib/libSDL2-2.0.so.0
ldd /usr/lib/libSDL-1.2.so.0
gdb --version
strace -V
ps
busybox --list
```

Ошибки отсутствующих путей допустимы при диагностике. `fbset -i` возвращал пустой вывод; amixer/readelf/objdump/file не найдены в PATH. Не использовать devmem, trigger_fs_error, fsck, команды записи sysfs в диагностическом сеансе.

## Извлечение образцов (PowerShell, после выхода из shell)

```powershell
New-Item -ItemType Directory -Force C:\ADB\profile
.\adb.exe pull /cfw/bin/busybox C:\ADB\profile\
.\adb.exe pull /cfw/lib/libuClibc-1.0.28.so C:\ADB\profile\
.\adb.exe pull /cfw/lib/ld-uClibc-1.0.28.so C:\ADB\profile\
.\adb.exe pull /cfw/lib/libgcc_s.so.1 C:\ADB\profile\
.\adb.exe pull /cfw/usr/lib/libstdc++.so.6.0.24 C:\ADB\profile\
.\adb.exe pull /cfw/usr/lib/libSDL2-2.0.so.0.8.0 C:\ADB\profile\
.\adb.exe pull /cfw/usr/lib/libSDL-1.2.so.0.11.4 C:\ADB\profile\
```

WSL: `bash scripts/analyze-elf.sh /mnt/c/ADB/profile ./analysis`. На Ubuntu хосте нужны file, binutils, coreutils, strings; опционально llvm-objdump для ARM disassembly. Не запускать ARM-бинарники на хосте, не использовать ldd на непроверенных чужих ELF.
