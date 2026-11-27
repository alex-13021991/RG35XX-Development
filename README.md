# Разработка для Anbernic RG35XX с GarlicOS 1.4.9

Профиль объединяет измерения 25 и 26 ноября 2026 года на оригинальной RG35XX владельца. За 25 ноября сохранены два ADB-снимка, библиотеки, sysroot и результаты тестов на железе. За 26 ноября добавлены журналы после ремонта, семь ELF с приставки и их разбор. [Сводный технический профиль](TechnicalProfile/README.md) · [Материалы за 26 ноября](HardwareDump/Published/20261126-research/)

### 26 ноября рабочая копия `rootfs.img` восстановлена и загружается на RG35XX

25 ноября в двух установщиках GarlicOS 1.4.9 обнаружили один и тот же дефект. Вложенный `CFW/rootfs.img` из **`RG35XX-MicroSDCardImage/garlic.img`** побайтно совпал с образом из комплекта `CopyPasteOnTopOfStock`. В обоих повреждены метаданные `/usr/lib/libintl.so` (inode 817) и `/usr/lib/libjson-c.so` (inode 818). На приставке до замены эти записи давали `Input/output error`. [Проверка установщиков и SHA-256 исходного образа](TechnicalProfile/Stock.md)

26 ноября в рабочей копии исправили метаданные ext4 и счётчик `overhead_blocks`, восстановили ссылки на `libintl.so.8.1.5` и `libjson-c.so.3.0.1`. По выписке оператора, итоговые `e2fsck -fvn` и сравнение `rsync` завершились кодом 0. При сравнении исключили две восстановленные ссылки, единственным оставшимся отличием была дата изменения каталога `usr/lib/`. Владелец загрузил исправленный образ на приставке. Журнал ADB показывает обе цели ссылок и смонтированную `/cfw`. Для восстановления в Git сохранён точный файл до первого запуска после ремонта. Его SHA-256 совпадает с манифестом владельца, состояние ext4 — `clean`. Для MTP-снимка с работающей приставки сохранён отдельный протокол. [Скачать исправленный rootfs.img в ZIP](Firmware/GarlicOS-1.4.9-Repaired/rootfs.img.zip) · [SHA-256 и независимая проверка файла](Firmware/GarlicOS-1.4.9-Repaired/) · [История ремонта](HardwareDump/Published/20261126-research/docs/02-rootfs-repair.md) · [Выписка проверок](HardwareDump/Published/20261126-research/evidence/logs/chat-results.txt) · [Журнал ADB](HardwareDump/Published/20261126-research/evidence/logs/adb-chroot.txt)

Обе **версионные библиотеки** читаются и побайтно совпадают с файлами на приставке. GarlicOS успешно загрузила их при проверке. В репозиторий приложены [libintl.so.8.1.5](SystemLibraries/Stock/libintl.so.8.1.5) и [libjson-c.so.3.0.1](SystemLibraries/Stock/libjson-c.so.3.0.1). [Методика, SHA-256 и протокол](TechnicalProfile/Stock.md)

| Материал | Что в нём |
|---|---|
| [Технический профиль](TechnicalProfile/README.md) | CPU, память, ядро, загрузка, накопители, графика, звук, USB и питание |
| [Карта физических кнопок](TechnicalProfile/Controls.md) | События 17 кнопок, проверенных с владельцем, и отдельный канал Power |
| [Сравнение со стоком](TechnicalProfile/Stock.md) | Ошибки двух inode в обоих установщиках и побайтовая сверка версионных библиотек с приставкой |
| [Компиляторы](Toolchains/README.md) | История сборок и измерения одинаковой программы на GCC 7.3, GCC 9.4 и Zig 0.13 |
| [Инструкция по SDK](Documentation/SDK.md) | Получение снимка, сборка C/C++ в WSL, проверка ABI, запуск по ADB и создание ZIP |
| [Исходные данные](HardwareDump/README.md) | Снимки, список библиотек, таблицы символов и журналы |
| [Библиотеки](SystemLibraries/README.md) и [sysroot](Sysroot/README.md) | Границы сред исполнения, происхождение заголовков и двух ссылок для линковщика |
| [Программы](TestPrograms/) и [скрипты](Scripts/) | Исходники воспроизводимых проверок |

Для первого порта на C подойдёт профиль `gcc7` с библиотеками из GarlicOS. Для графического вывода ориентиром служит главное меню, которое использует SDL 1.2 и открытый `fb0`. Для C++ базовая комбинация — GCC 7.3, заголовки libstdc++ 7.3 и системная `libstdc++.so.6`.

## Восстановление после переустановки компьютера

Обычный `git clone` скачивает исправленный образ, снимок библиотек, готовый sysroot и весь опубликованный комплект от 26 ноября, включая пять обезличенных журналов и ZIP с семью ELF. Исходный ZIP исследования для восстановления этого набора не требуется. [Библиотеки GarlicOS](SystemLibraries/20261125T155126Z-garlic.tar.gz) · [Sysroot для C и C++](Sysroot/20261125T155126Z-sysroot.tar.gz) · [Состав private/](HardwareDump/Published/20261126-research/private/)

Проверка в Linux или WSL после клонирования

```sh
git clone https://github.com/alex-13021991/RG35XX-Development.git
cd RG35XX-Development
sha256sum -c SHA256SUMS
(cd HardwareDump/Published/20261126-research && sha256sum -c SHA256SUMS.txt)
(cd Firmware/GarlicOS-1.4.9-Repaired && unzip rootfs.img.zip && sha256sum -c SHA256SUMS)
```

На чистом компьютере установите инструменты WSL и выбранный кросс-компилятор. Для первой сборки используйте архив sysroot из клона. Подключение приставки потребуется для запуска теста на железе. [Инструкция по сборке](Documentation/SDK.md) · [Журналы и реестр ELF](HardwareDump/Published/)

## QEMU для тестирования портов

[Среда QEMU и инструкция на русском](README-QEMU.md): ARM Cortex-A9, библиотеки GarlicOS, программная модель framebuffer и ввода. Ограничения аппаратной эмуляции описаны явно.
