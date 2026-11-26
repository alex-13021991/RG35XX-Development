# Восстановленный rootfs.img · GarlicOS 1.4.9 для оригинальной RG35XX

Для восстановления скачайте исходный результат ремонта **до загрузки на приставке**. В ZIP один файл `rootfs.img`, 209715200 байт (200 МиБ). Его SHA-256 совпала с контрольной суммой, которую владелец сохранил вместе с образом. [Скачать ZIP](rootfs.img.zip) · [SHA-256 распакованного файла](SHA256SUMS)

## Извлечение после клонирования

В Linux или WSL из этого каталога выполните

```sh
unzip rootfs.img.zip
sha256sum -c SHA256SUMS
```

В PowerShell из этого каталога выполните

```powershell
Expand-Archive -LiteralPath .\rootfs.img.zip -DestinationPath .\extracted
Get-FileHash -Algorithm SHA256 -LiteralPath .\extracted\rootfs.img
```

## Проверка перед публикацией

| Когда получен файл | SHA-256 образа | Состояние ext4 | Контрольная сумма суперблока |
|---|---|---|---|
| После ремонта, до загрузки. Эта версия лежит в ZIP | `da21e57c813c5db3a0901f867066978bcfc4ab6f5da9aca8c64f3f2587cd4feb` | `clean` | `0x96448b19` |
| После загрузки, скопирован владельцем по MTP с работающей RG35XX | `23ef20aa8c43f66436b5210171982b7e3563741d6258f014f020933ff70f7635` | `not clean` | `0x084e138f` |

Состояние и контрольная сумма суперблока образа в ZIP совпадают с итоговой выпиской ремонта. В момент съёма MTP-копии приставка использовала `/cfw` в режиме чтения и записи. Это объясняет отсутствие отметки о штатном размонтировании в том снимке. [Выписка оператора](../../HardwareDump/Published/20261126-research/evidence/logs/chat-results.txt) · [Журнал на приставке](../../HardwareDump/Published/20261126-research/evidence/logs/adb-initial.txt)

Обе копии прошли все пять этапов `e2fsck -fvn` 1.47.0 с кодом 0. В каждой проверены цели ссылок `libintl.so` и `libjson-c.so`, SHA-256 трёх версионных библиотек и счётчики ext4 (69990 свободных блоков, 48485 свободных inode, overhead 14399). [Проверка образа из ZIP](verification.txt) · [Проверка MTP-снимка](verification-mtp.txt)
