# 02. Восстановление rootfs.img GarlicOS 1.4.9

## Исходные данные и идентификация

Источник: официальный комплект `RG35XX-CopyPasteOnTopOfStock.7z.001/.002`, оператор успешно проверил 7z t и распаковал. Файл `roms/CFW/rootfs.img`, 209715200 байт (200 МиБ), дата в архиве 30.04.2023. Работы проводились над копиями на Ubuntu 20.04, e2fsck/debugfs 1.45.5. Исходный SHA-256 по результатам предыдущей сессии:

```
b6cc0bb9c349c69a32c7ae28d7dea5394890f745da718fcd7dcb3551dcadfe9f  rootfs_original.img
```

Оригинальный и начальный рабочий образ имели одинаковый SHA. Этот хеш соответствует стоку в [сравнении двух установщиков](../../../../TechnicalProfile/Stock.md). Владелец сохранил **исходный результат ремонта до загрузки** с SHA-256 `da21e57c813c5db3a0901f867066978bcfc4ab6f5da9aca8c64f3f2587cd4feb`. Проверка опубликованного файла подтвердила эту сумму, состояние `clean` и checksum суперблока `0x96448b19`. SHA-256 `23ef20aa8c43f66436b5210171982b7e3563741d6258f014f020933ff70f7635` относится к более поздней копии, снятой по MTP с работающей приставки. [Образ и протоколы обеих проверок](../../../../Firmware/GarlicOS-1.4.9-Repaired/) Не распространять процедуру автоматически на другой хеш или версию. Ранее обсуждалась возможная аналогичная проблема в 1.4.8 — отдельного подтверждения в материалах нет.

## Структура ФС

ext4 без журнала (утилита file может называть ext2, старый stat — ext2/ext3). UUID `3a13c064-c5e7-49ad-a7b9-0883b2a28ac0`; magic EF53, dynamic revision 1. 204800 блоков по 1024 байта, 51200 inode, inode size 256, first block 1, blocks/group 8192, inodes/group 2048, 512 inode table blocks/group, flex_bg 16, reserved blocks 10240, reserved GDT 256, checksum crc32c. Создание 16.12.2022.

Features: ext_attr resize_inode dir_index filetype extent flex_bg sparse_super large_file huge_file dir_nlink extra_isize metadata_csum. Default mount options user_xattr acl. Errors behavior Continue. UUID и набор features сохранены.

## Обнаруженные повреждения

Первоначальный `e2fsck -fvn` прерывался из-за checksum inode 817. ФС была not clean/with errors, в суперблоке четыре зарегистрированные ошибки (это не количество всех дефектов), first error inode 818, last 817, ext4_iget line 4193. Даты ошибок 27.01.2022 старше даты создания образа; вероятны некорректные часы/унаследованные метаданные, причина не установлена.

- Resize inode 7 некорректен; имеются неправильные указатели блоков.
- Inode 807, 2710, 2711: остатки удалённых файлов с нулевым dtime.
- inode 815 `/usr/lib/libao.so.4.1.0` и 817 `/usr/lib/libintl.so` содержали совпадающую метаинформацию, размер 26408, generation 1984224122, checksum 0xce426bb8, общие блоки 57186–57211 (26 блоков). Inode 817 не проходит checksum; содержимое указывает на копию libao, а не на libintl.
- inode 818 `/usr/lib/libjson-c.so` имел некорректный checksum и метаданные ссылки на `libgiomm-2.4.so.1.3.0`, совпадающие с соседним inode 816.
- Правильные версионные библиотеки и runtime SONAME-ссылки libintl.so.8 и libjson-c.so.3 были доступны.
- Overhead blocks = 4294963200 = 0xfffff000 (в интерпретации signed32: -4096). Значение недопустимо для 204800 блоков. Причина возникновения не доказана.

## Хронология

1. Оригинальный архив распакован; созданы `rootfs_original.img`, `rootfs_fixed.img`, оригинал оставлен без изменений.
2. Диагностика e2fsck -fvn, debugfs stat/ncheck с обходом checksum исключительно для чтения (`-n`). Выявлены inode 817/818, общие блоки, ошибочный resize inode.
3. `e2fsck -fyv rootfs_fixed.img`: пересоздан resize inode, исправлены inode checksum, удалённые inode, отклонения bitmap и счётчиков, клонированы 26 общих блоков для inode 815, исправлен тип dirent 817 (symlink -> regular). Код 1 (исправления выполнены). Следующая read-only проверка код 0. Сохранена промежуточная копия `rootfs_fsck.img`.
4. При чтении образа после fsck выяснилось, что libintl.so фактически содержит libao.so.4 и имеет его SONAME; libjson-c.so указывает на giomm. Удалены только эти две ошибочные записи, созданы относительные ссылки. Runtime-ссылки на версионные файлы не трогались. Проверены SHA и SONAME всех трёх групп. Сохранена копия `rootfs_libs_fixed.img`.
5. Read-only проверка всех 722 симлинков относительно корня образа: 715 разрешаются, 7 отсутствуют офлайн. Остальные ссылки оставлены без изменения.
6. Первая попытка rsync --checksum с оригиналом (без исключений) вернула 23: Bad message (74) на двух повреждённых inode; сравнение удалений пропущено. Это не было успешным доказательством полного совпадения.
7. Из копии `rootfs_overhead_test.img` исправлен overhead_blocks на 14399 через debugfs. Суперблок checksum изменился с 0xfe99f888 на 0x96448b19. Последняя проверка e2fsck -fvn: 0. Сравнение rsync с исключением ровно двух известных записей: 0, только `.d..t...... usr/lib/` (mtime каталога).
8. Кандидат перенесён на системную карту, оригинальная приставка успешно загрузилась, оператор не обнаружил изменений в поведении. ADB подтвердил монтирование /cfw ext4 без предупреждений для loop0, обе ссылки и корректный df.

## Контрольные результаты

| Метрика | Оригинал | После fsck, до ссылок | Финальный кандидат |
|---|---:|---:|---:|
| Состояние | not clean | clean | clean |
| Использовано блоков | 138322 по счётчику | 134836 | 134810 |
| Свободно блоков | 66478 | 69964 | 69990 |
| Свободно inode | 48482 | 48485 | 48485 |
| Использовано inode | 2718 по счётчику | 2715 | 2715 |
| Обычные файлы | не подтверждено | 1748 | 1747 |
| Символические ссылки | не подтверждено | 721 | 722 |
| Каталоги | — | — | 236 |
| Char device | — | — | 1 |
| Overhead blocks | 4294963200 | 4294963200 | 14399 |

Финальный e2fsck: 2715 used inode (5.30%); 1 non-contiguous file, 3 non-contiguous directories; extent histogram 1982/1; 134810 blocks (65.83%); 0 bad blocks (по учёту ФС, не физический тест microSD); 0 large files; 1747 regular, 236 dirs, 1 char device, 722 fast symlinks, всего 2706 файлов в сводке.

### Правильные связи и SHA-256 содержимого (разыменованные ссылки)

| Ссылки и файл | SHA-256 | SONAME |
|---|---|---|
| libintl.so, libintl.so.8 -> libintl.so.8.1.5 | 8b2558b10b9de8432d8c9c1c61ee7badea1ce90b90ab65bd900af7b7a89dbb46 | libintl.so.8 |
| libjson-c.so, libjson-c.so.3 -> libjson-c.so.3.0.1 | 36d9cc8ea699e02e1b9a51100a36c699d0b8493c5a3fae2a861b58cda9f676d2 | libjson-c.so.3 |
| libao.so, libao.so.4 -> libao.so.4.1.0 | a69ddf7068e1b89ab1c6efe44f45b53225df3796b7cc6bcf1144d6b0af78d1ea | libao.so.4 |

### Overhead

204800 - 190401 = 14399. Расчёт согласуется с геометрией: 1 first block + 25 × 512 inode table + 25 × 2 bitmap + 6 × (1 superblock + 1 group descriptor block + 256 reserved GDT) = 14399. Sparse super copies расположены в группах 0, 1, 3, 5, 7, 9 (шесть групп; следующие степени 25, 27 и 49 за пределами групп 0–24). Значение подтверждено statfs/df на Ubuntu и RG35XX.

| Показатель в блоках 1 КиБ | Ubuntu | RG35XX |
|---|---:|---:|
| df total | 190401 | 190401 |
| df used | 120411 | 120411 |
| df available | 55654 | 55654 |
| statfs free | 69990 | 69990 (следует из total-used) |

69990 - 55654 = 14336 = 10240 зарезервированных блоков + 4096 дополнительного резерва по наблюдаемой статистике. Интерфейс reserved_clusters присутствует; его значение отдельно не снято. `df` 68/69% зависит от реализации округления; блоковые числа совпадают. Не путать физический размер файла 200 МиБ и доступное пространство ФС 185.94 МиБ.

### 7 неразрешённых офлайн ссылок — не трогать

```
/dev/log -> ../tmp/log
/lib/modules/4.14.0-miyoo/source -> /home/steward/Github/f1c500s_kernel
/lib/modules/4.14.0-miyoo/build -> /home/steward/Github/f1c500s_kernel
/lib/modules/4.14.0-miyoo/kernel/drivers/video/fbdev/r61520fb.ko -> /mnt/kernel/r61520fb.ko
/var/lib/dbus -> /tmp/dbus
/etc/resolv.conf -> ../tmp/resolv.conf
/etc/mtab -> ../proc/self/mounts
```

Часть относится к runtime, часть к окружению сборки. Фактическое назначение r61520fb.ko и доступность цели на устройстве не установлены; ядро отличается от версии каталога модулей. Не удалять.

## Ручное воспроизведение (ТОЛЬКО копия известного образа)

Это документированная последовательность, а не универсальный автоматический ремонт. Проверить хеш оригинала и соответствие дефектов. Никогда не запускать e2fsck/debugfs -w на смонтированном образе или на работающей приставке. Не выполнять при несоответствии результата ожидаемому.

```bash
# В отдельном рабочем каталоге, исходник rootfs_original.img не смонтирован
sha256sum rootfs_original.img
cp -- rootfs_original.img rootfs_fixed.img
sudo env LC_ALL=C e2fsck -fvn rootfs_fixed.img
sudo debugfs -n -R 'ncheck 815 817 818' rootfs_fixed.img
# После подтверждения известных ошибок:
sudo env LC_ALL=C e2fsck -fyv rootfs_fixed.img
# Код 1 ожидаем при исправлении; при иных кодах кроме 0/1 остановиться.
sudo env LC_ALL=C e2fsck -fvn rootfs_fixed.img
# Требуется 0.
cp -- rootfs_fixed.img rootfs_fsck.img
mkdir -p rootfs_mount
sudo mount -o loop,rw rootfs_fixed.img rootfs_mount
# Сначала убедиться, что цель — именно рабочая копия и версии существуют:
ls -l rootfs_mount/usr/lib/libintl.so* rootfs_mount/usr/lib/libjson-c.so*
readelf -d rootfs_mount/usr/lib/libintl.so.8.1.5 | grep SONAME
readelf -d rootfs_mount/usr/lib/libjson-c.so.3.0.1 | grep SONAME
# Только после сверки:
sudo rm -- rootfs_mount/usr/lib/libintl.so rootfs_mount/usr/lib/libjson-c.so
sudo ln -s libintl.so.8.1.5 rootfs_mount/usr/lib/libintl.so
sudo ln -s libjson-c.so.3.0.1 rootfs_mount/usr/lib/libjson-c.so
sha256sum rootfs_mount/usr/lib/libintl.so* rootfs_mount/usr/lib/libjson-c.so* rootfs_mount/usr/lib/libao.so*
sudo umount rootfs_mount
sudo env LC_ALL=C e2fsck -fvn rootfs_fixed.img
cp -- rootfs_fixed.img rootfs_libs_fixed.img
cp -- rootfs_fixed.img rootfs_overhead_test.img
sudo env LC_ALL=C debugfs -w -R 'set_super_value overhead_blocks 14399' rootfs_overhead_test.img
sudo env LC_ALL=C dumpe2fs -h rootfs_overhead_test.img
sudo env LC_ALL=C e2fsck -fvn rootfs_overhead_test.img
# Требуется 0; далее сравнение только RO.
mkdir -p rootfs_original_mount rootfs_fixed_mount
sudo mount -o loop,ro,noload rootfs_original.img rootfs_original_mount
sudo mount -o loop,ro,noload rootfs_overhead_test.img rootfs_fixed_mount
df -k rootfs_fixed_mount
stat -f rootfs_fixed_mount
sudo env LC_ALL=C rsync -aHAXnci --delete --numeric-ids \
 --exclude='/usr/lib/libintl.so' --exclude='/usr/lib/libjson-c.so' \
 rootfs_original_mount/ rootfs_fixed_mount/ 2>&1 | tee rootfs_compare_final.log
echo "rsync exit code: ${PIPESTATUS[0]}"
sudo umount rootfs_original_mount
sudo umount rootfs_fixed_mount
# Если обе проверки успешны:
mkdir -p GarlicOS-1.4.9-Repaired
cp -- rootfs_overhead_test.img GarlicOS-1.4.9-Repaired/rootfs.img
(cd GarlicOS-1.4.9-Repaired && sha256sum rootfs.img > SHA256SUMS.txt && sha256sum -c SHA256SUMS.txt)
```

rsync сравнивает доступное содержимое, имена, типы и выбранные атрибуты, но не побайтово весь образ, не ctime/inode numbers и не исключённые записи. Не доказывает, что оригинальный доступный контент не имел иных исторических ошибок. Восстановленные ссылки проверены отдельно. Финальный SHA зависит от метаданных и времени выполнения. Не обещать воспроизводимость бинарного хеша при повторном ремонте.

## Тестирование и откат

С выключенной приставки снять TF1, сохранить старый `CFW/rootfs.img` отдельно, заменить файл, сверить SHA-256 в Windows (`Get-FileHash -Algorithm SHA256`), безопасно извлечь карту. Изменения внутри rootfs старого пользовательского образа могут быть потеряны; внешние ROMS/CFW не заменять. Откат — возврат предыдущего файла. Оператор имеет полные образы обеих карт на NAS.

На реальной RG35XX: загрузка успешна; штатная работа по наблюдению оператора; ссылки правильные; df совпал; chroot успешен. В dmesg для loop0 нет ошибок. Это достаточное подтверждение успешного ремонта в рамках выполненных проверок, но не длительный стресс-тест всех приложений.

Другие предупреждения: mmcblk0p3 mounting unchecked fs; mmcblk0p4 и mmcblk1p1 FAT not properly unmounted. Не доказательство повреждения файлов; проверить отдельно на выключенной приставке/извлечённых картах, сначала read-only, не запускать fsck на смонтированных разделах. I2C error 12, LCD standby GPIO, HDMI not connected, bootrotate — отдельные сообщения ядра; причинная связь с rootfs не обнаружена. Не писать в `/sys/fs/ext4/loop0/trigger_fs_error` (инъекция ошибки). errors_count в sysfs отсутствует в данной сборке.
