# Feature and interface parity

This document compares the native Linux implementation with the supplied
NitroSense 3.1.3056.0 package for the **Acer Nitro AN515-45, model year 2021**.
Other Nitro/Predator variants in the same Windows package are not automatically
features of this model. Full Windows pixel/interaction parity is **not claimed**.

## Evidence boundary

The Windows executable SHA-256 is
`f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd`.
REA managed metadata and resources are identified in [UI evidence](ui-evidence.md),
and input-word formulas in [protocol evidence](protocol-evidence.md). Recovered
XAML/C# in the local investigation workspace establish static layouts and event
handlers; they are not recordings of Windows runtime behavior. Linux hardware
results are recorded separately by the hardware tests, not inferred from XAML.

## Native app coverage

| Original control or behavior | Linux implementation | Verification / difference |
|---|---|---|
| Main 1320×760 shell; fan, power and monitoring panels | Native Qt scene with proportional resizing and measured fan geometry | Offscreen rendering verified. Generated independent skin is distributed; user-imported original artwork is optional. Window includes a 40-pixel status footer. |
| Auto / Max / Custom fan modes | Backend commands; independent CPU/GPU Auto and 1–100% custom controls | UI interaction tested with fake backend; actual fan test evidence is separate. Native CPU/GPU sliders and Auto checkboxes appear inline at the recovered XAML columns and rows; selecting Custom stages controls without writing, Apply or drag release sends the explicit request. |
| CPU/GPU fan RPM | Actual Acer hwmon fan1/fan2 readings | Inspected AN515-45 source maps channels to CPU/GPU; no fabricated RPM when absent. |
| Fan animation | Measured-RPM-driven native rotating fan artwork | Zero RPM or missing sensors stop animation. Screen rotation is scaled for readable movement; it is not a physical tachometer. Optional original fan artwork rotates through the same native path. |
| CoolBoost switch | Native toggle with current readback, exposed by locally patched driver using recovered original command | Enabled only when the loaded driver exposes a readable/writable state; hardware test results are separate. |
| Static four-zone keyboard colors | Four native color pickers, zone enable/disable, brightness | Exact Linux driver interface; disabled zones send black. Device acceptance and visible effects remain distinct. |
| Dynamic keyboard effects | Breathing, Neon, Wave, Shifting, Zoom; speed, brightness, direction, effect color | Controls honor inspected model constraints. Breathing speed is firmware-controlled; Neon/Wave colors are firmware-controlled. Visual confirmation requires someone at the keyboard. |
| Basic/recent color palettes and custom picker | Recovered nine basic colors, nine session-recent swatches, and a native custom picker | Basic colors match `LightingDynamicUI.basic_color_table`; recent choices are retained for the running application session. Per-zone and dynamic effect colors use the same palette. |
| Temperature graphs | CPU, discrete GPU, all sensors, CPU/GPU usage views | Measured values only; background worker keeps subprocess probes off the GUI thread. Original tab arrangement is replaced by a compact selector. |
| CPU/GPU temperature and usage; min/max | Actual CPU and discrete NVIDIA telemetry when available; measured temperature min/max per current graph window | No CPU/GPU usage when a source is absent. Min/max cover retained four-minute history; CPU usage needs two samples. |
| Celsius / Fahrenheit | Persisted application preference; converted displayed samples, axes and CSV unit labels | Native fake-backend interaction/unit tests; changing units clears the displayed trace to avoid mixing scales. |
| Monitoring clear/history export | Clear and timestamped CSV export | Export tests verify actual measured values and units. CSV is a Linux addition. |
| AC/battery Windows power schemes | Current Linux power profile controls via actual OS interface | Single Linux active profile; separate Windows plugged-in/battery scheme registries are not emulated. Only advertised profiles are enabled. |
| Backlight timeout / USB charging / battery charge limit | Capability-gated device settings | Unknown or unreadable state remains disabled. USB charging threshold is an integer choice, not a boolean. |
| Tray/minimize behavior | Optional close-to-tray; Show, Auto Fans, Quit actions | Enabled only when Qt detects a system tray. Normal exit requests automatic fans; closing to tray intentionally keeps the app running. |
| Saved lighting/fan settings and import/export | Versioned, bounded, validated local JSON profiles | Import/selection never writes hardware. Explicit Apply sends requests; partial apply attempts Auto restoration. Profiles are not wire-compatible with Acer XML profiles. |
| Sticky Keys / Windows key lock / menu key | Not implemented | Windows accessibility/input behavior requires a separate Linux desktop/input integration. No system key remapping is silently installed. |
| DTS / TrueHarmony / audio modes | Not implemented | Proprietary Windows audio components are unavailable in this Linux backend. |
| Model-dependent LCD overdrive/discrete-GPU switch | Not implemented | No verified local control path. Visibility in multi-model code does not establish support on this laptop. |
| Planet9/promotion links | Not reproduced | Promotional content, not a hardware capability. |
| Windows native backend | Not implemented | Pure protocol encoders exist; Acer service/runtime behavior remains unverified on Windows. |

## Configuration and startup

The UI stores profiles and preferences in
`$XDG_CONFIG_HOME/nitro-sense-linux/profiles.json`, defaulting to
`~/.config/nitro-sense-linux/profiles.json`. Loading a file never applies a device
profile. Files larger than 1 MiB are rejected; individual imported profiles are
limited to 64 KiB. Fan values, effect parameters, color strings and profile
versions are validated. Importing JSON cannot execute commands.

Artwork lookup is: `NITRO_SENSE_ASSETS`, then
`$XDG_DATA_HOME/nitro-sense/assets`, then the local investigation extraction path.
`NITRO_SENSE_ASSETS=none` explicitly selects the independent drawn skin. Public
releases do not require or bundle Acer's executable, fonts, or images.

## UI verification

`tests/test_ui.py` starts the actual Qt application offscreen with an isolated
fake backend and temporary profile directory. It verifies no startup device
writes, explicit Auto/Max dispatch, static zone/brightness payloads, dynamic wire
IDs and disabled irrelevant controls, capability gates, measured history CSV, and
clearing history. `tests/test_profiles.py` covers round trips, invalid values,
corrupt configuration, and bounded imports. These checks are not proof of
Windows visual parity, visible keyboard effects, or real firmware behavior.

## Remaining requirements for exact parity

Exact parity would additionally require a controlled Windows runtime baseline,
pixel/interaction comparisons for every active dialog/state, remaining WPF
style details and persisted recent-color behavior, Windows
power/audio/accessibility equivalents, model-specific firmware validation, and
Windows backend testing. The current app is a functional native Linux
reconstruction of supported controls, not a claim that those open requirements
have disappeared.

## Process lifecycle and screenshots

Telemetry is collected in a dedicated Qt thread pool with bounded backend probes.
Quit stops new polls, waits up to ten seconds for the current poll, then requests
automatic fans. If polling or restoration cannot finish, the window stays open
and reports the issue. SIGINT/SIGTERM schedule the same Quit path through a Qt
heartbeat. This is best-effort process cleanup, not protection from SIGKILL or a
kernel/firmware failure.

`--smoke-test` saves a screenshot to `NITRO_SENSE_SCREENSHOT` when specified,
otherwise `./evidence/ui-preview.png` if that directory exists, otherwise
`$XDG_CACHE_HOME/nitro-sense/ui-preview.png` (default `~/.cache/nitro-sense`).
It does not try to write installed package directories.
