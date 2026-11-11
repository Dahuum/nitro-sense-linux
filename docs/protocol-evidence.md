# Recovered fan, lighting, and Windows service input words

This is static analysis of the supplied Acer NitroSense package. No Windows
application, service, WMI call, or keyboard/fan command was executed. These are
application input words, not proof of firmware behavior or Linux method IDs.

## Artifact and evidence identity

The UI assembly is `extracted/ui-analysis/Win32/NitroSense.exe`, SHA-256
`f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd`.
REA records:

- `evidence/ui-managed.json`: `ev_6ca067e5ad67218ddc64f2d22f5dac0709ecb8a1931631f4481401bf8e0a3f75`
- `evidence/ui-members.json`: `ev_2df276a6ff340dd8c8c68693bf6c75893d0bac1c4cd66c9c4856f662a602536f`

REA records establish the selected artifact's managed metadata/member identity.
The formulas below were read from ILSpy 9.1.0.7988 reconstructed C# in
`extracted/decompiled/NitroSense/`. They are decompiler observations, not original
source or runtime traces. WPF type-resolution warnings appear in some UI methods;
the integer arithmetic statements used below are readable. This pass did not
perform an independent instruction-by-instruction CIL audit of each formula.

The package's `Plugs/Nitro AN515-45/Feature.ini` declares machine type 1 and year
2021; `HW_Support.ini` declares four default zone colors, per-key disabled, CPU/GPU
fans, and zone adjustment factors R/G/B = 1.0. These declarations guide the
relevant feature subset, but they do not identify the keyboard physically fitted
to this particular laptop or establish that all bundled paths execute on it.

## Fan commands

`CommonFunction.cs:919` (`set_all_fan_mode`) sends these words through
`WMIFunction.SetAcerGamingFanGroupBehavior`:

| Mode | Input word |
|---|---:|
| Auto | `0x410009` |
| Max | `0x820009` |
| Custom | `0xC30009` |

`CommonFunction.cs:952` (`set_all_custom_fan_state`) constructs
`9 | (cpu_behavior << 16) | (gpu_behavior << 22)`, where each behavior is 1 for
automatic or 3 for manual. It then sends two speed words:
`1 | (cpu_percent << 8)` and `4 | (gpu_percent << 8)`.

`CommonFunction.cs:986` (`set_single_custom_fan_state`) uses CPU behavior selector
1, but GPU behavior selector **8**, while the GPU **speed** selector is **4**.
These selectors must not be conflated. `set_single_custom_fan_speed` at line 1014
uses those same speed selectors. The original fan page calls these helpers:
`Nitro_FanControlPage.cs:356,381,412,500,590`.

`CommonFunction.cs:943` (`set_coolboost_state`) sends `7 | (enabled << 16)`
through `WMISetFunction`. `get_coolboost_state` at line 1031 reads `0x207` and
checks low-byte status zero and next-byte value one. Generic helper return checks
use `(result & 0xff) == 0`; some original fire-and-forget helpers do not check a
returned result, which is not a pattern the reconstruction should copy.

## Four-zone static lighting

`Popup_Lighting.cs:641` (`Change_Zone_Color`) floors each channel multiplied by
its model adjustment factor, then packs:

`zone_mask | (R << 8) | (G << 16) | (B << 24)`

Zone masks are 1, 2, 4, and 8. It calls `WMISetGamingRgbKbSetting`.
`Change_Zone_Brightness_RGB` at line 847 additionally scales channel values by
0.0/0.5/1.0 for brightness 0/50/100, then sends each zone separately. The
`zone_rgb` pure encoder takes already-adjusted channels and does not implement
profile parsing or brightness scaling.

`Change_Zone_Status` at line 722 sends
`8 | (zone1_enabled << 40) | (zone2_enabled << 41) |
(zone3_enabled << 42) | (zone4_enabled << 43)`
through `WMISetGamingLEDBehavior` (actual call at line 755).

`Change_Keyboard_Brightness` at line 839 constructs `(brightness_step-1)*25 << 16`
for `WMISetGamingKBBacklight`. Another older brightness path
`Change_Zone_Brightness` at line 817 uses 33→39, 66→84, 100→100 and performs a
read/modify/write with the hotkey number. These are distinct paths; this pass
has not proven which path executes for every possible runtime configuration.

## Dynamic lighting

`LightingDynamicUI.cs:267` (`Set_Dynamic_Keyboard`) uses this layout for the
64-bit input to `WMISetGamingKBBacklight`:

| Byte (little endian) | Content |
|---|---|
| 0 | Effect ID |
| 1 | Speed |
| 2 | `(brightness_step - 1) * 25` |
| 3 | `0x08` for Wave, otherwise zero |
| 4 | Direction for Wave/Shifting, otherwise zero |
| 5 | Adjusted red, except Neon uses zero |
| 6 | Adjusted green, except Neon uses zero |
| 7 | Adjusted blue, except Neon uses zero |

The declared pattern enum at line 19 is Breathing=0, Wave=1, Zoom=2, Shifting=3,
Neon=4. The switch maps these to wire IDs **1,3,5,4,2**, respectively. The declared
direction enum at line 28 is NA=0, Left=1, Right=2, Up=3, Down=4, Rotate_left=5,
Rotate_right=6. The enum's existence does not establish that every effect supports
every direction. For year >=2020, Wave disables the color radio controls in UI
logic (`LightingDynamicUI.cs:176`), even though the word construction still has
color fields.

## Windows service transport

The UI's `WMIFunction` methods are wrappers around a named pipe called
`PredatorSense_service_namedpipe`; they are not direct calls to WMI. Recovered
command codes in `WMIFunction.cs`:

| UI wrapper | Service command code |
|---|---:|
| SetAcerGamingFanGroupBehavior (line 125) | 15 |
| SetAcerGamingFanGroupSpeed (148) | 16 |
| WMISetFunction (171) | 17 |
| WMIGetFunction (194) | 20 |
| WMISetGamingKBBacklight (263) | 27 |
| WMISetGamingRgbKbSetting (286) | 28 |
| WMISetGamingLEDBehavior (309) | 29 |

Set responses are read as nine bytes, returning a UInt32 at offset 5. Get
responses are read as thirteen bytes, returning a UInt64 at offset 5. Original
code uses one `Read` call without proving the buffer was filled. A future
Windows backend needs bounded connection/read timeouts and complete frame reads.
No Windows backend has been connected or validated in this pass.

The transport helper was separately decompiled without execution from
`extracted/msi/FILE_APP_DOTNETLIB_DLL`, SHA-256
`79a1645c08976ddf74e84d3c5bd6ffd47f1fde9f2a9f0ad89bf78171912b2705`.
REA identity/member evidence is retained in `evidence/protocol-ipc-managed.json`
(`ev_c71e79eb0dec2e7c8f415dbb624e81fdaed4883757f9e75bf89a9857a06b5479`) and
`evidence/protocol-ipc-members.json`
(`ev_b8c0b039f009d2ab49735943da0b2645040ac4e4c91d7554cc339f465afc34c2`).
`extracted/decompiled-ipc/TsDotNetLib/IPCMethods.cs:33`
(`SendCommandByNamedPipe`) constructs a two-byte command, one-byte argument
count, and for each argument a four-byte length followed by the marshaled value.
For the selected x64 Windows target these integer fields are little endian.
One UInt64 argument therefore produces a 15-byte frame: `u16 command`, `u8 1`,
`u32 8`, `u64 input_word`. `service_u64_request` implements only this specific
case, with no service connection or I/O.

## Implementation and coverage

`nitro_sense/protocol.py` contains pure encoders for the recovered input words
and the single-UInt64 service frame. Seven unit tests in `tests/test_protocol.py`
check concrete mode constants, asymmetric fan selectors, byte order, zone bits,
dynamic effect mapping, framing, and rejection of invalid values. Validation
bounds are reconstruction design choices, not claimed original validation.

Linux backend integration is separate. These Windows service command IDs must
not be passed blindly as WMI method IDs. Native service dispatch, firmware
semantics, keyboard presence, visible lighting effects, RPM response, error
recovery, runtime UI parity, and Windows backend behavior remain unverified.

### Comparison with the prepared Linux driver

The inspected local `third_party/linuwu-sense/src/linuwu_sense.c:3831`
`fan_val_calc` computes `(((percentage * 25600) / 100) & 0xFF00) + fan_index`.
For every validated integer percentage 0..100 this is mathematically identical
to `(percentage << 8) | fan_index` with fan_index 1 or 4: 25600/100 is exactly
256, no relevant high bits are discarded, and selector bits do not overlap.
There is no arithmetic discrepancy on this domain. The Linux driver also uses
`0xC30009` for combined manual mode. This source-level agreement strengthens the
candidate protocol match but does not prove that the Windows native service
passes its input words unmodified or that the firmware responds correctly.

## Native service and APGeAction confirmation

A later native pass used REA 6.7.0 with Ghidra 12.1.4 against service SHA-256
`e6638fecc41730075d25587bfdda7b4dda2d170b64ac9df9b3c03543999f3b4e`.
REA search record `ev_80a0a40eeaf1837b7d641803237345c76f280ffbff2a0f7970ea75b100849a0f`
searched for `SetGamingFunction` and returned no matching defined string. A
focused regex search identified `SetFunction` at VA `0x140055b20`; its reference
at `0x14000f071` resolves to native function `FUN_14000ef20`.
Decompilation record
`ev_482d3b2658e04868535ed72b47edac2fca7ff7b0ec572f37aae60e8b37580dff`
observes an APGeAction / SetFunction COM WMI invocation carrying the input word.
This identifies the native routing of original command 17; static pseudocode is
not a Windows execution trace. Complete records remain in the local workspace;
the public identity index authenticates them without publishing Acer source.

The prepared driver now exposes `nitro_sense/coolboost`: APGeAction GUID3 method2
reads word `0x207`, method1 writes `7 | (enabled << 16)`. ACPI failure and firmware
low-byte errors are checked separately. On this laptop toggling 0→1→0 produced
matching firmware readbacks. This is evidence for command/state functionality,
not a standalone measurement of an increased thermal limit.

The keyboard-timeout readback is `0x1e6400080000`, not just `0x1e0000080000`:
the extra byte contains brightness100. The old whole-word equality incorrectly
reported -1. The local driver validates the status/function low24 bits and
reads the timeout field in bits40..55. Toggling 1→0→1 matched readback. These are
local-source changes, captured in the vendored driver and patch provenance.
