# Contributing

Use Python 3.10+ and a virtual environment. Install `python -m pip install -e .`.
Run `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -v`.
Tests must never require hardware writes or root. Add backend tests using a
fixture sysfs root; distinguish requested state, firmware readback, physical
measurements and visual confirmation. Preserve fan Auto restoration on errors.

New laptop write support requires a precise DMI profile, reviewed protocol
provenance and an on-device test log; do not relax the model guard to make an
untested laptop look supported. Unsupported controls should explain the missing
capability, not silently claim success. Do not add raw EC offset writes from
unverified Internet snippets. Keep proprietary binaries/artwork/decompiled source
out of commits and releases. Submit UI changes with screenshots of the native
fallback skin and keyboard-accessible controls.
