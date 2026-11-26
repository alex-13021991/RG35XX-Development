# 01. Технический профиль устройства

Это показания сеанса 26 ноября. Снимки за 25 ноября дополняют их измеренными битовыми полями fb0, картой кнопок, результатами ALSA и данными библиотек внешней системы. [Сводка за два дня](../../../../TechnicalProfile/README.md)

## Идентификация и ядро

| Параметр | Значение |
|---|---|
| Модель | Anbernic RG35XX Original (2022), GarlicOS 1.4.9 |
| Hardware | gs705a |
| CPU | ARM Cortex-A9, 4 ядра; implementer 0x41, part 0xc09, variant 0x4, revision 1 |
| ISA | ARMv7-A, ARMv7l, 32-bit little-endian |
| CPU features | swp half thumb fastmult vfp edsp thumbee neon vfpv3 tls |
| Ядро | Linux 3.10.37 #116 SMP PREEMPT |
| Сборка ядра | Thu Apr 6 20:31:58 CEST 2023, blackseraph@Pandemonium |
| Компилятор ядра | GCC 4.7.3 prerelease 20130328, Linaro 2013.04, crosstool-NG linaro-1.13.1-4.7-2013.04-20130415 |
| Buildroot userspace | 2018.02 (`/etc/os-release`), строка Welcome to Miyoo (`/etc/issue`) |
| ADB | product Demo_7051H, model ToyCloud, device q88_hd, root |

Наличие каталога `/lib/modules/4.14.0-miyoo` НЕ означает, что устройство использует Linux 4.14. Реально запущено ядро 3.10.37. Связь с Miyoo подтверждают файлы окружения и пути SDK, но не реконструирована полная история сборки GarlicOS.

## CPUFreq

Измерено при открытом меню/ADB: online `0-3`, affected_cpus и related_cpus `0 1 2 3`. Драйвер `owl_cpu0`, governor `interactive`, текущие cpuinfo_cur_freq и scaling_cur_freq = 720000 кГц, scaling_max_freq = 720000, scaling_min_freq = 240000. Аппаратный диапазон по таблице драйвера 240000–1488000 кГц. Доступные частоты (МГц): 240, 504, 720, 840, 1008, 1104, 1200, 1296, 1392, 1488. Governors: conservative, ondemand, userspace, powersave, interactive, performance. Transition latency 300350 нс = 300.35 мкс. scaling_setspeed unsupported при текущем governor. Чтение stats как файла закономерно даёт Is a directory.

**Вывод:** 720 МГц — текущее ограничение, не максимальная характеристика CPU. Возможное изменение частот в играх пока не измерено. 1488 МГц — верхний пункт таблицы, а не доказанная стабильная частота для длительной работы. Не менять вручную до контрольных измерений.

## RAM

| /proc/meminfo | КиБ |
|---|---:|
| MemTotal | 237624 |
| MemFree | 68988 |
| CmaFree | 20980 |
| Buffers | 52664 |
| Cached | 40960 |
| Slab | 28268 |
| SReclaimable | 23160 |
| SwapTotal / SwapFree | 0 / 0 |

MemTotal = 232.055 МиБ, видимых ядру. Физический номинал 256 МиБ согласуется с наблюдением, но прямой замер установленного объёма не проводился. MemFree — снимок, не общий запас памяти: часть кешей может освобождаться. Не суммировать CMA с MemFree без проверки учёта.

## Карты памяти и точки монтирования

Размеры из `/proc/partitions` в блоках по 1024 байта:

| Устройство | КиБ | Назначение |
|---|---:|---|
| mmcblk0 (TF1, 64 GB) | 60324864 | системная карта, 57.53 ГиБ |
| mmcblk0p1 | 10240 | MISC, /misc, vfat ro, alias actb |
| mmcblk0p2 | 524288 | SYSTEM, /system, ext4 ro, alias actc |
| mmcblk0p3 | 52224 | DATA, /mnt/data, ext4 rw, alias actk |
| mmcblk0p4 | 59728896 | ROMS, /mnt/mmc, vfat rw |
| mmcblk1 (TF2, 32 GB) | 30931968 | карта игр |
| mmcblk1p1 | 30929920 | /mnt/SDCARD, vfat rw, 29.50 ГиБ |
| loop7 | 204800 | backing_file = /mnt/mmc/CFW/rootfs.img |
| loop0 | 204800 | backing_file = /dev/block/loop7 |

Цепочка загрузки окружения:

```text
Linux 3.10.37 (одно ядро для обоих окружений)
  /system + /misc + /mnt/data (базовая система)
  /mnt/mmc/CFW/rootfs.img -> loop7 -> loop0 -> /cfw (ext4 rw)
    chroot /cfw -> /bin/sh (BusyBox ash, uClibc)
    /dev, /proc, /sys и обе карты доступны внутри /cfw
```

Процессы в снимке: `/system/bin/adbd`, `/system/dmenu/dmenu_ln`, `/misc/dmenu.bin`, `/misc/hdmi.bin`, `/bin/sh /mnt/mmc/CFW/start`, `sh ./run.sh`, `./mtp-server`, `./main`. Детальное назначение и цепочку запуска каждого процесса нужно сверить со скриптами. Xorg в этом снимке не работает.

## Два окружения

| | Базовое | GarlicOS |
|---|---|---|
| Корень при ADB | / | /cfw (в chroot — /) |
| Shell | /system/bin/sh -> mksh | /bin/sh -> busybox |
| BusyBox | 1.14.3, 1993232 байта, 2013-09-30 | 1.27.2, 719316 байт, 2019-01-15 |
| libc | Для Android-компонентов в этом сеансе не определена. Внешний реестр от 25 ноября содержит также glibc 2.15 в `/lib/arm-linux-gnueabihf/` | uClibc-ng 1.0.28 |
| Динамический загрузчик | /system/bin/linker | /lib/ld-uClibc.so.0 / .1 |

`/system/bin/busybox chroot /cfw /bin/sh` проверен и работает. Прямой запуск `/cfw/bin/busybox` из базового окружения не работает (ENOENT), поскольку интерпретатор `/lib/ld-uClibc.so.0` ищется относительно базового корня. В chroot он доступен. Это подтверждено readelf.

## Графика

| Параметр | Результат |
|---|---|
| Framebuffer | /dev/fb0 -> /dev/graphics/fb0, /dev/fb1 -> /dev/graphics/fb1 |
| Драйвер | owlfb |
| Виртуальная геометрия fb0 | 640 × 1440 |
| Экран | 640 × 480 (известная конфигурация, active mode ioctl ещё не снят) |
| bpp | 16 |
| stride | 1280 байт |
| Права /dev/graphics/fb* | crw-rw---- root:1003 major 29 minors 0,1 |
| /dev/dri | отсутствует |
| /usr/lib/dri | swrast_dri.so (3107824 байта) |
| dmesg GPU filter | совпадений по gpu/powervr/pvr/sgx/mali/vivante нет |

Режимы sysfs: U:1024x896p-28, U:320x200d-69, U:8x8p-5408, U:640x480p-75, U:640x480p-56. Список не равен текущему режиму/частоте обновления.

Один кадр 640×480×2 = 614400 байт = 600 КиБ; виртуальная область 640×1440×2 = 1843200 байт = 1.758 МиБ. Это совместимо с тройной буферизацией, но фактическая стратегия переключения буферов и `smem_len` не измерены. RGB565 вероятен; точные bitfields нужно снять через FBIOGET_VSCREENINFO. `fbset -i` и явный `-fb /dev/graphics/fb0 -i` не дали вывода.

Библиотеки EGL, GL, GLES1/2, GLU, GBM, DRM/KMS, X11, Xorg присутствуют. Единственный обнаруженный DRI — программный swrast. Аппаратное ускорение не подтверждено, отсутствие /dev/dri не доказывает невозможность закрытого GPU API. Для портов использовать программный renderer/fbcon до проверки.

## Звук и ввод

ALSA card 0 `atm7059link` / `atm7059_link`:

| PCM | Имя |
|---|---|
| hw:0,0 | ATC2603C PCM atc2603c-dai-0 |
| hw:0,1 | HDMI PCM atm7059-hdmi-dai-1 |
| hw:0,2 | BLUETOOTH PCM bluetooth-pcm-dai-2 |

Каждое playback-устройство: 1/1 subdevice. Capture 0 и 2 присутствуют в `/proc/asound/devices`. Также control и timer. `aplay -L`: null, default:CARD=atm7059link, sysdefault:CARD=atm7059link. Наличие PCM Bluetooth не подтверждает наличие физического радиомодуля; capture не подтверждает физический микрофон. `amixer` отсутствует в PATH. Реальные параметры микшера и поддерживаемые форматы не сняты.

| Узел | Устройство | Интерфейс |
|---|---|---|
| /dev/input/event0 | atc260x_onoff | кнопка питания, evdev |
| /dev/input/event1 | RG35XX Gamepad | evdev |
| /dev/input/js0 | RG35XX Gamepad | joystick API |

Gamepad: Bus=0019 Vendor=0001 Product=0001 Version=0100; gpio-keys-polled; EV=b, ABS=3003f. Устройства root:1004, major 13. Загруженные модули: atc260x_cap_gauge (26067 байт), gpio_keys_polled (6924 байта). Коды кнопок и осей ещё не записаны. Датчики батареи/вибрация не исследовались в этом сеансе.

## Инструменты и библиотеки

GDB 8.0 (`arm-linux`, 43712100 байт), strace 4.20 (460396 байт), ltrace, ldd, strings, hexdump, xxd, nano, vi, Lua/luac, aplay, arecord, Xorg, sha256sum, BusyBox chroot. `readelf`, `objdump`, `file` не обнаружены в PATH (не исключено наличие вне PATH), `amixer` не найден. В `/etc/ld.so.conf` файла нет. Полная инвентаризация в CSV и исходном журнале. Не следует путать наличие утилит с доступностью полного SDK/заголовков.
