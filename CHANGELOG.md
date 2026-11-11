# Changelog

## 0.2.0 — 2026-11-11

Lighting now actually turns on for the Acer Nitro AN515-45. Static mode writes
per-zone colors followed by the static enable command; dynamic modes prepare
per-zone colors before the dynamic command. Breathing speed is preserved on the
patched driver instead of being forced to zero. Driver quirk enables LED zone
arming and the RGB fix for this model, and the saved keyboard state file no
longer overrides the firmware default to black on boot.

## 0.1.0 — 2026-11-11

First native Linux release for the inspected Acer Nitro AN515-45. Qt desktop UI,
Auto/Max/independent custom fans, CoolBoost via the project driver, static four-zone
and five dynamic lighting effects, live CPU/NVIDIA GPU monitoring and history
export, Linux power profiles, device settings, local profiles and tray support.
Ships a source driver, setup/removal scripts, an original fallback skin, optional
local artwork importer, diagnostics, tests and GitHub Pages documentation.

This is an initial release, not a claim of complete Acer Windows feature or pixel
parity. Read the feature matrix for validation scope and remaining differences.
