# Две версионные библиотеки GarlicOS 1.4.9

Эти ELF-файлы извлечены из `/usr/lib` внутри установочного `rootfs.img`. Сверка SHA-256 подтвердила их побайтовое совпадение с библиотеками на проверенной приставке. В установочном образе microSD повреждены две другие записи каталога, с именами без номера версии. [Проверка обоих установщиков](../../TechnicalProfile/Stock.md)

| Скачать ELF | Имя для загрузчика | Байт | SHA-256 |
|---|---|---:|---|
| [libintl.so.8.1.5](libintl.so.8.1.5) | `libintl.so.8` | 30164 | `8b2558b10b9de8432d8c9c1c61ee7badea1ce90b90ab65bd900af7b7a89dbb46` |
| [libjson-c.so.3.0.1](libjson-c.so.3.0.1) | `libjson-c.so.3` | 46632 | `36d9cc8ea699e02e1b9a51100a36c699d0b8493c5a3fae2a861b58cda9f676d2` |

Для проверки в Linux выполните в этом каталоге `sha256sum -c SHA256SUMS`. Для сборки с `-lintl` и `-ljson-c` сценарий создания sysroot добавляет соответствующие ссылки на компьютере. [Состав sysroot](../../Sysroot/README.md)

libintl входит в GNU gettext (Free Software Foundation, LGPL-2.1-or-later). json-c распространяется по лицензии MIT. [GNU gettext](https://www.gnu.org/software/gettext/) · [json-c](https://github.com/json-c/json-c) · [Лицензия libintl](COPYING.LIB) · [Лицензия json-c](COPYING.json-c)
