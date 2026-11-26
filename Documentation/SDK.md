# Сборка и проверка в WSL Ubuntu 24.04

Все команды ниже выполняются из каталога `RG35XX-Development` в Ubuntu. На этом ПК работает Windows-клиент ADB из `C:\ADB`. Скрипты рассчитаны на Python 3.12, GNU binutils и стандартные библиотеки Ubuntu 24.04. Для сравнения установочных образов также нужны `sfdisk`, `debugfs` и `e2fsck`.

## Использование готового снимка

После клонирования проверьте снимок командой `sha256sum -c SHA256SUMS`. Готовый sysroot с заголовками и библиотеками лежит по пути из примера ниже. Для первой сборки установите Miyoo GCC 7.3.0 и укажите каталог SDK через `--sdk`, если он отличается от `~/rg35xx-sdk/miyoo-gcc-7.3.0`. Ссылка и SHA-256 дистрибутива приведены в [инструкции Miyoo SDK](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/System-Info-RU/BUILD.md).

```sh
export ADB=/mnt/c/ADB/adb.exe
SYSROOT=Sysroot/20261125T155126Z-sysroot.tar.gz
python3 Scripts/build.py --tool gcc7 --sysroot "$SYSROOT" --lib SDL \
  --out build/gcc7/bench TestPrograms/bench.c
python3 Scripts/run.py build/gcc7/bench build/bench-device.log
```

Для проекта с несколькими единицами трансляции передайте все исходные файлы после параметров. Для каждой дополнительной библиотеки добавьте `--lib ИМЯ`. C++-файлы получают заголовки libstdc++ 7.3, стандарт C++11 и компоновку с libstdc++. Пример проверенного запуска на приставке:

```sh
python3 Scripts/build.py --tool gcc7 --sysroot "$SYSROOT" \
  --out build/gcc7/cpp TestPrograms/cpp.cpp
python3 Scripts/run.py build/gcc7/cpp build/cpp-device.log
```

Рядом с бинарником появятся `.build.json` с версиями и точными командами и `.abi.txt` с ELF, ARM-атрибутами и транзитивными зависимостями. Перед сохранением результата скрипт проверяет ARM ELF32 little-endian, EABI5, загрузчик, соглашение о передаче float, присутствие требуемых библиотек и сильные динамические импорты, включая версии символов. Для вызовов через `dlopen`, подключаемых модулей и аппаратных интерфейсов используются отдельные проверки на устройстве.

Для другого пути установки компилятора задайте `--sdk /путь/к/miyoo`. Для Zig дополнительно передайте путь к самому Zig. В комплекте Screenshot Manager указаны архив x86_64 Linux версии 0.13.0 и его SHA-256. [Предыдущая инструкция по Zig](https://github.com/alex-13021991/Anbernic-RG35XX/blob/29129e515f13813864ae15a9cf7fa7ca2d1970d0/Screenshot-Manager/Сборка.txt)

```sh
sh Toolchains/prepare-zig.sh /путь/к/zig-linux-x86_64-0.13.0.tar.xz
ZIG="$HOME/.cache/rg35xx-development/zig-linux-x86_64-0.13.0/zig"
python3 Scripts/build.py --tool gcc9 --sysroot "$SYSROOT" --lib SDL \
  --out build/gcc9/bench TestPrograms/bench.c
python3 Scripts/build.py --tool zig --zig "$ZIG" --sysroot "$SYSROOT" --lib SDL \
  --out build/zig/bench TestPrograms/bench.c
python3 Scripts/compare.py "build/measurements-$(date -u +%Y%m%dT%H%M%SZ)"
```

Скрипт сравнения ожидает три `build/<компилятор>/bench`. Каждый лог выводится на экран и сохраняется на ПК. Сводка содержит размеры, SHA-256 и медианы. Для проверки framebuffer, SDL, микшера, PCM и EGL используйте отдельную программу:

```sh
python3 Scripts/build.py --tool gcc7 --sysroot "$SYSROOT" --lib SDL --lib asound --lib dl \
  --out build/gcc7/interfaces TestPrograms/interfaces.c
python3 Scripts/run.py build/gcc7/interfaces build/interfaces-device.log
python3 Scripts/package.py build/gcc7/interfaces RG35XX-Interfaces \
  --sysroot "$SYSROOT" --zip build/RG35XX-Interfaces-release.zip
```

`run.py` проверяет идентичность платформы и тип монтирования, передаёт исполняемый файл в уникальный каталог `/cfw/dev/shm`, запускает его внутри `chroot /cfw`, собирает stdout, stderr и статус процесса. Для этой сессии HOME и TMPDIR указывают на RAM. Скрипт предназначен для диагностических исполняемых файлов. Выход из программы возвращает управление вызвавшему процессу. Эти операции не устанавливают приложение в меню. Установочный ZIP содержит `Roms/APPS/<имя>.sh` и `Roms/APPS/<имя>/program`. При ручном запуске установленной версии из APPS журнал пишется рядом с программой в `run.log`.

## Повторный сбор на устройстве

```sh
export ADB=/mnt/c/ADB/adb.exe
"$ADB" devices -l
python3 Scripts/collect.py --libraries
```

Когда устройств несколько, задайте `ANDROID_SERIAL`. Сборщик проверяет модель платформы и наличие CFW. Система устройства опрашивается командами чтения; архив передаётся потоком, промежуточный tar на SD не создаётся. После команды подставьте имя созданного каталога:

```sh
STAMP=20261125T155126Z
python3 Scripts/inventory.py "HardwareDump/$STAMP"
python3 Scripts/sysroot.py "SystemLibraries/$STAMP-garlic.tar.gz"
```

Смотрите поле `report` у каждого архива в `archives.json`. Оно содержит исходные ошибки tar и код завершения. SHA-256 относится к сохранённому архиву. Для просмотра экспортов и версионных требований конкретной библиотеки откройте `elf-symbols.txt.gz` через `zless` и найдите заголовок с областью `garlic` или `base` и полным путём.

Для уже собранного ELF можно отдельно запустить `python3 Scripts/abi.py приложение /путь/к/распакованному/sysroot`. Распаковывайте архив в файловую систему Linux с поддержкой символических ссылок. Для повторения карты кнопок соберите `TestPrograms/keys.c` и вызовите `run.py` при участии человека у приставки. Окно записи составляет 120 секунд. [Порядок нажатий](../TechnicalProfile/Controls.md)
