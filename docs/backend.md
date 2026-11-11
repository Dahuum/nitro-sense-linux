# Linux backend contract and hardware boundaries

The backend is native Python operating through Linux sysfs and installed OS
utilities. It does not run Acer's Windows binaries, guess EC offsets, execute
shell strings, install drivers, or require the GUI to run as root. The current
write target is specifically Acer Nitro AN515-45: exact vendor and DMI model,
loaded `linuwu_sense`, one unambiguous platform interface, explicit control opt-in,
and writable attributes are all required.

## Driver provenance and meaning of success

The local driver is pinned to Linuwu-Sense commit
`4483b6c38b9bb963ac9ada9ca476578e0c63cc08`, plus the recorded local hardening patch.
The formats below were inspected in its `src/linuwu_sense.c`, rather than inferred
from filename or adapted Windows service command numbers. See
[protocol evidence](protocol-evidence.md) for the separately recovered original
Windows UI words. Static source inspection is not physical validation.

`Path.write_text` success means the kernel accepted the sysfs request. In
particular, RGB setters return `verified_visible: false`: no command or readback
proves that a particular zone changed to the requested visible color. The
upstream static RGB implementation has model/firmware limitations. Fan sysfs
readback contains cached requested percentages, **not measured RPM**. Measured
fans always come from hwmon `fan*_input`.

## Controls

| Backend method | Inspected interface | Request and bounds |
|---|---|---|
| `set_fans(cpu, gpu)` | `nitro_sense/fan_speed`, `predator_fan_speed_store` | `CPU,GPU`, each integer 0–100; zero means automatic |
| `set_lighting_static(colors, brightness)` | `four_zoned_kb/per_zone_mode`, `per_zoned_rgb_kb_store` | Exactly four six-digit RGB colors, then brightness 0–100 |
| `set_lighting_dynamic(mode, speed, brightness, direction, color)` | `four_zoned_kb/four_zone_mode`, `four_zoned_rgb_kb_store` | Seven comma-delimited decimal fields; mode 0–5, speed 0–9, brightness 0–100, direction 0–2, RGB bytes 0–255 |
| `set_coolboost(enabled)` or `set_switch('coolboost', value)` | `nitro_sense/coolboost`, locally added original-evidence APGeAction wrapper | 0/1; firmware status/readback checked |
| `set_switch('battery_limiter', value)` | `nitro_sense/battery_limiter`, `predator_battery_limit_store` | 0/1 (80% battery limit) |
| `set_switch('backlight_timeout', value)` | `nitro_sense/backlight_timeout`, `predator_backlight_timeout_store` | 0/1 (30-second backlight timeout); writes disabled when current state is unknown |
| `set_switch('usb_charging', value)` | `nitro_sense/usb_charging`, `predator_usb_charging_store` | 0/10/20/30; this is a threshold setting, not a boolean |
| `set_power_profile(name)` | `powerprofilesctl` / Power Profiles Daemon | Only profiles actually reported by `powerprofilesctl list`; readback must match |

Lighting mode IDs exposed by the app: Static=0, Breathing=1, Neon=2, Wave=3,
Shifting=4, Zoom=5. Wave and Shifting require direction 1 or 2. The AN515-45 driver
forces breathing speed to zero, ignores direction for Static/Breathing/Neon/Zoom,
and ignores RGB for Neon/Wave. The backend normalizes those ignored fields before
reporting the request, so UI selections do not imply unsupported changes.

Aliases `set_zone_colors(colors, brightness)` and
`set_lighting(mode, speed, brightness, direction, red, green, blue)` are available
for callers requiring the lower-level numeric API. They use the same validation.

Switch writes require a recognized current value and matching post-write
readback. A mismatch raises an error rather than pretending success. At the initial read-only check on this laptop, backlight timeout returned `-1`,
USB charging returned `30`, and battery limiter returned `0`. Subsequent driver
analysis found that the timeout's full-word comparison incorrectly included a
brightness byte; the corrected driver reports timeout `1`. Unknown values still
disable writes. An attribute's existence alone does not establish firmware support.

The local driver now exposes CoolBoost through a dedicated sysfs attribute,
using the recovered original APGeAction GetFunction input `0x207` and SetFunction
input `7 | (enabled << 16)`. Capability is enabled only when this dedicated
interface exists, returns known 0/1 state, and is writable. Old upstream drivers
without the local extension keep CoolBoost unavailable. Battery calibration is not
exposed: the app never initiates a calibration cycle as a settings toggle.
Windows power schemes are not claimed identical to Linux power profiles.

## Restoration

Fan changes are serialized by a reentrant backend lock. A failed write triggers
an automatic `0,0` request. If that also fails, restoration remains armed;
`close()` tries again and reports failure. After a successful manual request,
`close()` restores automatic fan behavior. The driver itself also has a
best-effort restoration patch. Neither normal shutdown handling nor this patch
can promise recovery from abrupt power loss, a dead kernel, or disappearing
hardware. The GUI must call `close()` and surface errors.

Other deliberate settings (lighting, battery limiter, USB threshold, power
profile) persist as requested; closing the GUI does not silently undo them.
Bounded runtime tests should save baseline state and restore it in a `finally`
block. Global state restoration tests and actual hardware writes are performed
by the owning root agent, not by unit tests.

## Telemetry and snapshot schema

`Backend.snapshot()` retains `model`, `temperatures`, `fans`,
`fan_control_available`, `lighting_available`, `reason`, and `lighting_reason`.
Additional fields:

- `fan_request`: `{cpu, gpu}` with requested percentages, or `null`.
- `lighting.dynamic`: `{mode, speed, brightness, direction, red, green, blue}`;
  `lighting.zones`: `{colors: ['#RRGGBB', ...], brightness}`. Either may be null on
  malformed/unavailable readback.
- `switches[name]`: `{available, readable, value, choices, reason}`. Unknown values
  remain null and control is disabled.
- `power`: `{available, profiles, active, reason}` from Power Profiles Daemon.
- `cpu_usage_percent`: CPU usage computed from consecutive `/proc/stat` samples;
  first sample is null rather than a fabricated zero.
- `memory`: `{total_bytes, used_bytes, percent}` from `MemTotal` and `MemAvailable`.
- `gpu`: NVIDIA name, temperature, utilization, VRAM used/total, and source, or
  null if `nvidia-smi` is unavailable. Integrated AMD temperature remains explicitly
  labeled by hwmon; it is not presented as the discrete NVIDIA temperature.
- `capabilities`: booleans for fans, lighting, CoolBoost, power profiles, and
  battery calibration. Availability is not equivalent to device validation.

CPU and all readable hwmon temperatures retain driver/sensor identity. Zero fan
RPM is preserved as a valid measurement; missing or malformed sensors are omitted.
NVIDIA telemetry is obtained through an argument-array subprocess call with a
2-second timeout and a short cache. Power daemon probes have the same timeout;
missing programs, failed commands, and timeouts produce unavailable capabilities.
The GUI should collect snapshots on a worker to avoid UI blocking on the timeout.

## Verification

`tests/test_backend.py` and `tests/test_backend_features.py` use temporary fake
sysfs/proc trees and injected command runners. They cover missing sensors,
telemetry units, true zero RPM, exact model and permission gates, fan restoration,
retry after failed restoration, unambiguous driver discovery, RGB byte formatting,
invalid inputs, ignored dynamic fields, unknown setting state, USB threshold
bounds, CPU deltas, memory units, subprocess timeout behavior, and power-profile
readback. They do not write this laptop's hardware. Runtime hardware evidence is
kept separately under `evidence/` and must be read for the current validation status.
