# Linux driver provenance

Upstream project: https://github.com/0x7375646F/Linuwu-Sense

Pinned commit: `4483b6c38b9bb963ac9ada9ca476578e0c63cc08`.

`linuwu_sense.c` derives from upstream `src/linuwu_sense.c`, with source SPDX `GPL-2.0-or-later`
(the upstream repository supplies a GPLv3 LICENSE, preserved here). Local fan-restoration, serialization, and
persistence hardening is recorded under `patches/` in this repository. The
local source additionally supplies a dedicated CoolBoost attribute using original
APGeAction commands and corrects timeout status decoding to ignore its brightness
byte; inspect the source and retained evidence for those local differences. The
standalone Makefile is supplied by this project. No precompiled module or
upstream system installer is distributed in this source directory.

This driver is distinct from the Acer Windows application. It communicates with
Linux WMI interfaces and has been selected for the Acer Nitro AN515-45. The app
installer rejects other DMI models, even if upstream supports additional models.

Vendored source SHA-256: `4e0123a92b9b204b13fa203f7a83b8fa48a8016be496c37e0a7918717470f536`.
