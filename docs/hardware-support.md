# Hardware support investigation

Read-only inspection on 2026-11-11. No kernel modules were loaded, hardware
registers written, ACPI methods invoked, or system configuration changed.
Raw local observations are in [hardware-snapshot.json](hardware-snapshot.json).
This is host evidence and source research, not REA binary evidence.

## Observed on this laptop

| Item | Observation |
|---|---|
| Vendor / model | Acer / Nitro AN515-45 |
| Board / BIOS | Scala_CAS / V1.08 |
| Kernel | 6.18.39-1-lts |
| CPU telemetry | `k10temp`, `temp1_label=Tctl`, readable millidegrees Celsius |
| Integrated GPU telemetry | `amdgpu`, `temp1_label=edge`, readable millidegrees Celsius |
| Other temperatures | ACPI thermal zone, NVMe, MediaTek wireless |
| Fan RPM / PWM | No `fan*` or `pwm*` hwmon attributes found |
| Keyboard lighting | No keyboard backlight or RGB entries in `/sys/class/leds`; only lock indicators and LAN indicators |
| Performance profile | Neither `/sys/firmware/acpi/platform_profile` nor its choices file exists |
| Loaded Acer modules | `acer_wireless`; `acer_wmi` is absent |
| Alternative control interfaces | `/proc/acpi/call`, `/dev/acer-gkbbl-0`, `/dev/facer` absent |
| Kernel headers | Build directory for the running kernel exists; module compilation was not attempted |

The WMI bus exposes, without bound drivers, both
`7A4DDFE7-5B5D-40B4-8595-4408E0CC7F56` and
`79772EC5-04B1-4BFD-843C-61E7F77B6CC9`, matching GUID4/5 constants in
Linuwu-Sense. GUID presence identifies a promising communication route; it does
not prove RGB hardware, protocol semantics, or successful control.

## Existing Linux implementation

Current [Linuwu-Sense source](https://github.com/0x7375646F/Linuwu-Sense/blob/main/src/linuwu_sense.c)
contains an exact Acer `Nitro AN515-45` DMI match and a quirk with
`nitro_sense = 2` and `four_zone_kb = 1`. The downloaded source SHA-256 was
`6d0fa7cabe1897871fb239144de6ce85f954b711773e49ef1216b660b1c2ce04`.
These are source declarations, not local device validation. This is a strong
candidate backend; new raw embedded-controller offsets should not be guessed.

The [driver documentation](https://github.com/0x7375646F/Linuwu-Sense/blob/main/README.md)
describes Nitro fan control through `nitro_sense/fan_speed`, with a CPU/GPU
percentage pair and zero meaning firmware automatic control. It exposes RGB
through `four_zoned_kb/four_zone_mode` and `per_zone_mode`. Its installer changes
module blacklisting, DKMS registration, boot loading, groups, and permissions;
that installer has not been run here.

The older [RGB module](https://github.com/JafarAkhondali/acer-predator-turbo-and-rgb-keyboard-linux-module)
lists AN515-45 RGB as tested. This model-level compatibility claim does not
establish this specific laptop's keyboard configuration.

An independent [AN515-45 BIOS V1.08 hardware report](https://github.com/itsdavidmandal/nitro-an515-45-linux/blob/main/FINDINGS.md)
reports fan read/write and dynamic RGB modes working; static/per-zone colors and
performance profiles failed in that author's tests. Treat these as reported
results and hypotheses for local validation, not proof of immutable firmware
limitations. That repository's instruction to add a DMI patch is superseded by
the current upstream source, which already includes the match.

## Implementation implications and remaining gaps

1. A native application can expose CPU and integrated GPU temperatures now.
   Label their provenance; an integrated GPU sensor is not the discrete NVIDIA
   GPU. Discrete GPU telemetry was not investigated in this pass.
2. Fan and RGB controls currently have no available local control backend.
   Report them unavailable until a compatible driver exists and its interfaces
   are detected. Do not show successful changes based on UI state alone.
3. Evaluate a pinned Linuwu-Sense revision against this kernel, review its
   installation effects, then validate actual fan RPM and automatic restoration.
4. Confirm the keyboard's physical RGB configuration and visually verify effects.
   Register readback alone does not establish visible lighting changes.
5. Keep fan-control writes serialized and restore automatic control following a
   failed update or interrupted session. Distinguish saved desired settings from
   measured RPM and hardware readback.
6. Windows requires a separate backend and runtime validation. Linux sysfs
   support cannot establish Windows parity or original NitroSense UI behavior.

Complete feature and UI parity remains unresolved; this investigation establishes
the local interfaces and a concrete Linux driver candidate only.

## Locally prepared driver

Upstream was cloned into `third_party/linuwu-sense` and detached at commit
`4483b6c38b9bb963ac9ada9ca476578e0c63cc08`. The source tree now includes the local hardening patch described below.
The following build succeeded using existing kernel headers:

```sh
make -C /lib/modules/6.18.39-1-lts/build \
  M=/home/void_id/Desktop/nitro-sense/third_party/linuwu-sense modules
```

Output: `third_party/linuwu-sense/src/linuwu_sense.ko`. No install, DKMS setup,
module loading, module signing, or hardware writes were performed. Direct kernel
make avoids the upstream Makefile's optional `sudo` signing step.

Source inspection at that commit establishes:

- `predator_fan_speed_store` accepts CPU/GPU percentages from 0 to 100.
  `acer_set_fan_speed` sends method 14 behavior requests and method 16 custom
  speed requests. Both zero selects automatic behavior (`0x410009`), both 100
  selects maximum (`0x820009`). The default local cache starts at zero.
- `fan_speed` readback returns that software cache; actual RPM must be checked
  through the separate `acer` hwmon device after loading. A cached zero at
  startup is not proof the firmware is in automatic mode.
- RGB `four_zone_mode` accepts seven decimal fields: mode (0–7), speed (0–9),
  brightness (0–100), direction (0–2; nonzero required for wave/shifting), and
  RGB bytes. `per_zone_mode` takes four six-digit hexadecimal colors and
  decimal brightness. These are driver contracts, not validated visible effects.
- The model's `.nitro_sense=2` route exposes legacy fan/battery/USB controls,
  while `.four_zone_kb=1` enables the RGB sysfs group. Do not force newer-model
  `nitro_v4` behavior solely to obtain a profile selector.

### Gaps to address before loading

This is a focused source review, not a security audit or assurance that the
driver is safe. Compilation does not validate firmware behavior.

1. `acer_platform_probe` calls `four_zone_kb_state_load`, which can send lighting
   commands from `/etc/four_zone_kb_state` during module initialization. Loading
   the module is not a passive inventory action.
2. On removal, the driver saves state under `/etc`. In
   `four_zone_kb_state_save`, `filp_open` is checked using `!file` rather than
   `IS_ERR`; a failed `kernel_write` also takes a double `filp_close` path.
   `acer_predator_state_save` uses the same flawed open/error-close pattern.
   These deserve correction before testing unload/error recovery.
3. Fan updates use several WMI calls and return early on failure without
   rollback. The cache updates only after all calls succeed. A reported error
   may therefore leave partially changed firmware state.
4. No automatic fan restoration was seen in `acer_platform_remove`,
   `acer_suspend`, or `acer_wmi_exit`. The application/helper must explicitly
   restore automatic control and verify RPM behavior; losing a userspace process
   is not evidence that firmware falls back automatically.
5. Fan/RGB handlers do not provide a transaction lock around their multi-call
   operations. A single privileged helper should serialize application writes.
6. The upstream installer makes persistent system changes and installs an
   unrelated frontend and services. It has not been executed; a focused local
   test should use the built module and explicitly reviewed lifecycle steps.


### Local hardening applied

[../patches/linuwu-sense-local-hardening.patch](../patches/linuwu-sense-local-hardening.patch)
records changes against the pinned upstream commit:

- Correct both persistence open-error checks to `IS_ERR` and close each file only
  once after a write failure. Do not save keyboard state if its refresh failed.
- Validate fan percentage bounds inside the shared setter as well as the sysfs
  parser. Serialize all setter transactions with a mutex.
- Attempt the existing automatic-mode command after an interrupted fan update.
  Preserve an error return even if recovery succeeds; log failed recovery.
- Remove the correct legacy Nitro attribute group. After control attributes are
  removed and state saving finishes, attempt automatic fan mode before unload.

The patched module rebuilt successfully against the running kernel. Neither the
recovery branches nor module unload have been exercised against real hardware.
This patch reduces identified defects; it does not certify the remaining driver.
Initialization still restores saved lighting, and suspend handling has not been
extended. Hardware activation remains a deliberate next step.

### Exact driver paths for the application

After the module loads successfully, the model's anticipated base is
`/sys/module/linuwu_sense/drivers/platform:acer-wmi/acer-wmi`, equivalently the
platform device `/sys/devices/platform/acer-wmi`. Detect files at runtime rather
than treating either path as proof of availability:

| Relative file | Payload |
|---|---|
| `nitro_sense/fan_speed` | `CPU,GPU\n`, integer percentages 0–100; `0,0` automatic, `100,100` maximum |
| `four_zoned_kb/four_zone_mode` | `mode,speed,brightness,direction,R,G,B\n` |
| `four_zoned_kb/per_zone_mode` | `RRGGBB,RRGGBB,RRGGBB,RRGGBB,brightness\n` |
| `nitro_sense/battery_limiter` | `0\n` or `1\n` |
| `nitro_sense/battery_calibration` | `0\n` stops or `1\n` starts calibration; do not start implicitly |
| `nitro_sense/usb_charging` | Decimal firmware cutoff option; derive exact supported values from the driver |

Find sensor files by `/sys/class/hwmon/hwmon*/name == acer`; indices are dynamic.
`fan1_input` and `fan2_input` provide separate RPMs. Retain their labels when
present instead of relying on stable hwmon indices.

## Subsequent privileged hardware validation (2026-11-11)

The initial inspection above is historical. The driver has since been loaded
and replaced with the final local build containing CoolBoost and timeout fixes.
Bounded tests now cover Auto/Max/custom fans (actual RPM), static/Breathing/Wave
RGB (firmware readback), CoolBoost, keyboard timeout, battery limiter and USB
charging (firmware readback), and Linux power profiles. Original settings were
restored after each operation. See `evidence/*hardware-test.json` and README's
validation table. Physical keyboard appearance remains unobserved while the user
is away. Readback is not a promise that every shipped keyboard is RGB capable.
A single inspected laptop does not establish general model compatibility.

A subsequent normal-user Qt lifecycle test held custom60/70, sent SIGTERM to the
GUI process group, and observed clean exit0 plus cached fan request0/0 before
the outer test harness issued any fallback restoration. See
`evidence/lifecycle-hardware-test.json`. SIGKILL remains outside Python cleanup.
