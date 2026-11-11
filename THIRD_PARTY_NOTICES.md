# Third-party components and reconstruction inputs

The new Python application, native fallback drawings, website, scripts and docs
are MIT licensed, except where a file explicitly states otherwise.

## Linuwu-Sense driver

`driver/linuwu_sense.c` is a modified copy of
[Linuwu-Sense](https://github.com/0x7375646F/Linuwu-Sense), pinned to upstream commit
`4483b6c38b9bb963ac9ada9ca476578e0c63cc08`. Its notices remain intact and its
upstream GPL license is included as `driver/LICENSE`. The application MIT license
does not relicense the driver. See `driver/PROVENANCE.md` and the included patch
for modifications and build provenance. The driver has its own kernel ABI and
must be compiled for the running kernel.

## Qt / PySide6

PySide6 and Qt are external dependencies with their own LGPL/GPL/commercial
licensing terms. This Python wheel does not bundle Qt. Installation resolves
PySide6 through the user's Python package manager. See
[Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).

## Acer reconstruction inputs

NitroSense, Acer logos, original artwork, Windows binaries, fonts, original
installer archives and decompiled Acer source are not distributed with this
project or its release packages. They remain owned by their respective holders.
Local reverse engineering used the user-supplied NitroSense 3.1.3056.0 package;
artifact digests and bounded protocol observations are documented separately.
`nitro-sense-import-assets` reads the user's exact verified original package and
extracts personal local artwork without executing its code. The included native
fallback skin is original project code. This project is independent and is not
affiliated with or endorsed by Acer.
