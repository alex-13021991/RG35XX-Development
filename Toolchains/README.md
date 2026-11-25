# Три цепочки сборки

## Что уже использовалось

| Инструмент | Проверяемый след в предыдущих проектах |
|---|---|
| Miyoo GCC 7.3.0 | В журнале Dingux Commander Dark RU указаны `arm-miyoo-linux-uclibcgnueabi-g++.br_real (Buildroot 2018.02.9) 7.3.0`, загрузчик, ELF-атрибуты и подтверждение владельца. В Garlic Menu Settings сценарий проверяет число 7.3.0. [Журнал](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/Dingux-Commander-RU/verification.txt) · [Сценарий](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/Garlic-Menu-Settings/build.sh) |
| Buildroot GCC 9.4.0 | Для OpenJazz в `~/openjazz/build-rg35xx/CMakeFiles/3.28.3/CMakeCXXCompiler.cmake` сохранена версия 9.4.0. В ELF релизного ZIP v1.1 есть строка `GCC: (Buildroot -g2f2fa438) 9.4.0`. Вариант Jazz Jackrabbit занимает 282156 байт, SHA-256 `eb26df150f309adb978f09aa6789ce9b0673d9b0fa04adaea07040c568f0eb74`. [Описание порта](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/OpenJazz_RG35XX/README_RG35XX.md) · [Архив](https://github.com/alex-13021991/Anbernic-RG35XX/releases/download/openjazz-rg35xx-v1.1/OpenJazz_RG35XX_v1.1.zip) |
| Zig 0.13.0 | Screenshot Manager 0.1.0 компилируется фронтендом Clang из Zig и компонуется `zig ld.lld` со стартовыми объектами Miyoo. SHA-256 файла `Roms/APPS/ScreenshotManager/manager` в релизе совпал с инструкцией, размер 12588 байт. В прежних проектах также сохранились Zig-сценарии для System Info RU и Dingux Commander RU. [Инструкция](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/Screenshot-Manager/Сборка.txt) · [Сценарий](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/Screenshot-Manager/build.py) |

На этом компьютере актуальный путь к GCC 7.3.0 — `~/rg35xx-sdk/miyoo-gcc-7.3.0`. Под `/opt/miyoo` установлен GCC 9.4.0 с uClibc 1.0.41 в его собственном sysroot. У Miyoo 7.3.0 в SDK uClibc 1.0.28. Сценарий идентифицирует компилятор по выводу команды, а для обеих версий передаёт общий sysroot с библиотеками приставки.

## Измерения на одном устройстве

Один исходник на C, одинаковый алгоритм, `-Os -marm -mcpu=cortex-a9 -mfpu=neon-fp16 -mfloat-abi=softfp` (у Zig написание CPU `cortex_a9`), удаление неиспользуемых секций и символов. GNU GCC использует свой ld, Zig использует LLD. Запуски последовательные, порядок вариантов меняется каждый раунд. По три запуска на компилятор, штатный governor `interactive`, частота свободно менялась.

| Компилятор | ELF, байты | 16 млн итераций xorshift32, мс | memcpy, МиБ/с | SDL blit 640×480 RGB565, операций/с |
|---|---:|---:|---:|---:|
| Miyoo GCC 7.3.0 | 5304 | 133,975 | 271,28 | 547,66 |
| Buildroot GCC 9.4.0 | 5300 | 134,136 | 276,53 | 582,43 |
| Zig 0.13.0 | 4592 | 133,980 | 250,28 | 571,10 |

В таблице медианы. На одно измерение памяти приходится 128 МиБ копирования блоками по 4 МиБ. Графический тест делает 200 программных копирований между поверхностями в RAM. Это измерение не даёт частоту обновления LCD или скорость GPU. Медианы CPU отличаются менее чем на 0,2 мс. Для этого теста Zig дал самый маленький ELF, а три запуска с меняющейся частотой не позволяют надёжно ранжировать компиляторы по скорости игр.

Все девять запусков завершились кодом 0 и дали `checksum=7cdc70ec byte=1 pixel=07e0`. Прямые зависимости теста — `libSDL-1.2.so.0` и `libc.so.0`. В транзитивном наборе присутствуют libiconv и загрузчик uClibc. ABI конкретных будущих портов проверяется отдельно. [Исходник теста](../TestPrograms/bench.c) · [Медианы, размеры и SHA-256](../HardwareDump/Published/20261125T155454Z/benchmark/medians.tsv)
