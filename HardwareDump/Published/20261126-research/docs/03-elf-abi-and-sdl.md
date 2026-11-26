# 03. ELF, ABI, SDL и оригинальный SDK

Источник — семь файлов из `private/profile.zip`, считанных пользователем с работающей приставки через ADB pull. В этой редакции повторно запущены file, readelf -h/-A/-l/-S/-d/-V/-Ws/-p .comment; результаты целиком в `evidence/elf/`. Для SDL дополнительно использованы strings и llvm-objdump. Образцы не исполнялись на компьютере.

## 1. Идентичная базовая ABI всех семи файлов

ELF32, little endian, ARM, EABI version 5, e_flags 0x05000200 (soft-float ABI). `.ARM.attributes`: CPU_name ARM926EJ-S, CPU_arch v5TEJ, ARM_ISA_use Yes, THUMB_ISA_use Thumb-1, wchar_t 4, enum int, 8-byte alignment needed, IEEE754 FP model. Нет заявленного hard-float PCS или NEON. Это характеристики бинарников, а не ограничение аппаратной части Cortex-A9.

| Файл | Байты | Тип / символы | DT_NEEDED | SONAME / PT_INTERP |
|---|---:|---|---|---|
| busybox | 719316 | executable, stripped | libc.so.0 | interpreter /lib/ld-uClibc.so.0 |
| ld-uClibc-1.0.28.so | 32656 | shared, not stripped | — | ld-uClibc.so.1 |
| libuClibc-1.0.28.so | 489384 | shared, stripped | ld-uClibc.so.1 | libc.so.0; interpreter /lib/ld-uClibc.so.1 |
| libgcc_s.so.1 | 132640 | shared, stripped | libc.so.0 | libgcc_s.so.1 |
| libstdc++.so.6.0.24 | 1021456 | shared, stripped | libc.so.0, ld-uClibc.so.1, libgcc_s.so.1 | libstdc++.so.6 |
| libSDL-1.2.so.0.11.4 | 1198220 | shared, debug_info, not stripped | libiconv.so.2, libc.so.0 | libSDL-1.2.so.0 |
| libSDL2-2.0.so.0.8.0 | 988400 | shared, debug_info, not stripped | libts.so.0, libc.so.0 | libSDL2-2.0.so.0 |

Хеши каждого образца: `evidence/elf/manifest.csv`. Не путать loader в выводе ldd с прямым DT_NEEDED самой SDL. Наличие вызовов/реализаций __aeabi_fadd, __aeabi_fsub, __aeabi_dadd, __aeabi_dmul, __aeabi_ddiv, __aeabi_d2f в SDL 1.2 согласуется с программной арифметикой. Для конкретных участков кода проверять дизассемблирование; soft-float ABI сам по себе не запрещает аппаратные инструкции (softfp).

## 2. SDK и provenance

В обеих SDL `.comment` содержит:

```
GCC: (GNU) 3.3.2 20031005 (Debian prerelease)
GCC: (Buildroot 2018.02.9) 7.3.0
```

Присутствие старой строки GCC 3.3.2 не означает, что весь бинарник собран им; она может относиться к отдельному объекту/ассемблерному компоненту. GCC 7.3.0 подтверждён путями отладки:

```
/opt/miyoo/arm-miyoo-linux-uclibcgnueabi/sysroot/usr/include
/opt/miyoo/arm-miyoo-linux-uclibcgnueabi/sysroot/usr/lib
/opt/miyoo/lib/gcc/arm-miyoo-linux-uclibcgnueabi/7.3.0/include
/home/steward/Downloads/buildroot-2018.02.9/output/build/host-gcc-final-7.3.0/build/arm-miyoo-linux-uclibcgnueabi/libgcc
```

Итак, происхождение SDL — Miyoo SDK, Buildroot 2018.02.9, GCC 7.3.0, target `arm-miyoo-linux-uclibcgnueabi`, libc uClibc-ng 1.0.28, ARM926EJ-S/soft. /etc/os-release сообщает 2018.02 (серия, не точная patch-версия). Компилятор ядра другой — Linaro 4.7.3. Не доказано, что все компоненты GarlicOS были собраны одной версией SDK.

## 3. C++ runtime

Версионные определения libstdc++.so.6.0.24: GLIBCXX_3.4.24, CXXABI_1.3.11, CXXABI_ARM_1.3.3, CXXABI_TM_1. libgcc_s.so.1: GCC_7.0.0 (верхняя числовая версия в определениях). Совпадает с поколением GCC 7. Проверять именно нужные версии символов готовой игры, а не только имя libstdc++.so.6. Новый компилятор может потребовать GLIBCXX/CXXABI, которых здесь нет.

## 4. Точные версии SDL и драйверы

SDL 1.2.15: `SDL_Linked_Version` по адресу 0x5218 возвращает указатель на три байта 01 02 0f (вычисление в SDL1-version-proof.txt). SDL2 2.0.8: `SDL_GetVersion_REAL` по адресу 0xe3fc записывает 2,0,8. Строка ревизии `hg-11914:f1084c419f33`. В SDL2 функции возвращают константы: SDL_GetNumVideoDrivers_REAL @ 0x771d8 = 2; SDL_GetNumAudioDrivers_REAL @ 0x10aec = 4; SDL_GetNumRenderDrivers_REAL @ 0x32d24 = 1. Имена bootstrap подтверждены таблицей символов; запуск драйверов на приставке ещё не проверялся.

| Бэкенд | SDL 1.2.15 | SDL 2.0.8 |
|---|---|---|
| fbcon | FBCON_bootstrap | нет в исследованной сборке |
| X11 | не найден | X11_bootstrap |
| dummy video | DUMMY_bootstrap | DUMMY_bootstrap |
| ALSA | ALSA_bootstrap | ALSA_bootstrap |
| OSS/DSP | DSP_bootstrap | DSP_bootstrap |
| DMA audio (SDL1) | DMA_bootstrap | не найден |
| disk audio | DISKAUD_bootstrap | DISKAUDIO_bootstrap |
| dummy audio | DUMMYAUD_bootstrap | DUMMYAUDIO_bootstrap |
| renderer | API SDL1 surface | SW_RenderDriver, единственный |

Наличие ALSA/X11 может обеспечиваться dlopen: отсутствие libasound и libX11 в DT_NEEDED не означает отсутствие бэкенда. SDL2 без fbcon — существенное ограничение для портов: SDL_VIDEODRIVER=fbcon сам по себе не создаст отсутствующий драйвер. Проверить реальный вывод SDL_GetCurrentVideoDriver, SDL_CreateWindow/Renderer и окружение конкретного порта. Не заменять системные SDL вслепую.

## 5. Системная инвентаризация SDL

| Компонент | Имя файла | Байты |
|---|---|---:|
| SDL 1.2 | libSDL-1.2.so.0.11.4 | 1198220 |
| SDL 2 | libSDL2-2.0.so.0.8.0 | 988400 |
| SDL_image | libSDL_image-1.2.so.0.8.4 | 52200 |
| SDL2_image | libSDL2_image-2.0.so.0.2.1 | 130492 |
| SDL_ttf | libSDL_ttf-2.0.so.0.10.1 | 32108 |
| SDL2_ttf | libSDL2_ttf-2.0.so.0.14.0 | 36976 |
| SDL_mixer | libSDL_mixer-1.2.so.0.12.1 | 163760 |
| SDL_mixer альтернативный | libSDL_mixer-1.2.so.0.12.0 | 81272 |
| SDL_gfx | libSDL_gfx.so.13.9.1 | 100948 |
| SDL2_gfx | libSDL2_gfx-1.0.so.0.0.1 | 77772 |
| SDL_net | libSDL_net-1.2.so.0.8.0 | 19612 |
| SDL_sound | libSDL_sound-1.0.so.1.0.2 | 175036 |

SDL2_mixer / SDL2_net не обнаружены в инвентаризации /usr/lib. Версии имён файлов не приравнивать к релизным версиям без подтверждения. Важные связи:

```
libSDL.so -> libSDL-1.2.so.0.11.4
libSDL2.so -> libSDL2-2.0.so.0.7.0 -> libSDL2-2.0.so.0.8.0
libSDL2-2.0.so.0 -> libSDL2-2.0.so.0.8.0
libSDL_mixer.so -> libSDL_mixer-1.2.so.0.12.0
libSDL_mixer-1.2.so.0 -> libSDL_mixer-1.2.so.0.12.1
```

Последнее различие — не доказанная ошибка: не менять без теста SONAME и поведения обеих сборок. У SDL1 файла mode 0700 root, остальные перечисленные SDL обычно 0755; это может быть важно при запуске не от root. В исследуемом окружении приложения работают от root.

## 6. Другие библиотеки

Присутствуют libEGL.so.1.0.0, libGL.so.1.2.0, libGLESv1_CM.so.1.1.0, libGLESv2.so.2.0.0, libGLU.so.1.3.1, libdrm, libgbm, libkms, X11, Cairo, Pixman, FreeType, Fontconfig, HarfBuzz, PNG/JPEG/GIF/WebP, Bullet 2.86, ALSA (libasound.so.2.0.0), OpenAL (libopenal.so.1.18.1), libao, Ogg/Vorbis/MP3/Speex, GStreamer 0.10, GLib, Lua 5.1.5, zlib 1.2.11, bzip2 1.0.6, LZ4. Полный список имён, владельцев, размеров, ссылок в CSV и журнале. Наличие файла не является проверкой его API, полной цепочки зависимостей или работоспособности.
