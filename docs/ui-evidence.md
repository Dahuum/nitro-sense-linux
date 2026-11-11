# NitroSense UI investigation

## Identity and evidence

Source: `extracted/ui/CentenialConvert_3.1.3056.0_x64.appx`, manifest identity
`AcerIncorporated.NitroSenseV31`, version `3.1.3056.0`, x64. Manifest launches
`Win32/NitroSense.exe` as `Windows.FullTrustApplication`.

The actual UI executable is a CIL .NET Framework WPF assembly. It is not the
.NET Native wrapper assembly. SHA-256:
`f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd`.
MVID `085cfc3f-ac88-401d-b629-1df3010dc6c2`.

REA CLI 6.7.0 static inspection, without executing Acer code:

| Saved record | Evidence ID | Observation |
|---|---|---|
| `evidence/ui-managed.json` | `ev_6ca067e5ad67218ddc64f2d22f5dac0709ecb8a1931631f4481401bf8e0a3f75` | Managed classification, resources and assembly metadata |
| `evidence/ui-members.json` | `ev_2df276a6ff340dd8c8c68693bf6c75893d0bac1c4cd66c9c4856f662a602536f` | 287 type rows, 1306 method rows, CIL anchors, call edges, literals |
| `evidence/ui-pe-resources.json` | `ev_2a6131bd2de7b2c42826a90efbc2273ab7618167c294f712d37febbcfc03eb13` | PE resource inventory |

Metadata coverage is complete; literal/CIL inventory coverage retains the REA
record's limits. Neither static tool executes the assembly or observes Windows
runtime behavior. ILSpy output in `extracted/decompiled/` is recovered C#, with
unresolved WPF references and decompiler warnings; it is not original source.

## Actual controls established by static evidence

- `Nitro_FanControlPage` has Auto, Max, Custom controls; CPU and GPU percentage
  sliders, independent Auto checkboxes, fan RPM displays and CoolBoost. Recovered
  `SetFanMode` uses values 0=Auto, 1=Max, 2=Custom. Custom alone shows the sliders.
  `SetCustomFanAutoMode` disables each slider when its Auto box is selected.
- Original fan event handlers update registry values under
  `SOFTWARE\OEM\NitroSense\FanControl`. CoolBoost uses `CoolBoostMode`;
  percentage values use `CPUFanPercentage` and `GPU1FanPercentage`. This UI is
  coupled to the installed Windows service; drawing a control is not a Linux
  implementation of its behavior.
- `Popup_Lighting` has Static/Dynamic selection, brightness, four zone selectors,
  zone color buttons, nine basic colors, nine recent colors and a further color
  picker. Additional per-key lighting and profile/macro classes exist in this
  multi-model package. Their existence does not establish this laptop supports
  per-key RGB or any particular effect.
- `Nitro_MonitoringPage` has CPU/GPU temperature and usage displays, minimum and
  maximum temperatures, graph history, separate plugged-in/battery power scheme
  tabs and Power Saver/Balanced/High Performance choices. 2022 and Acer mode
  variants also exist.
- Main window settings include Celsius/Fahrenheit, Sticky Keys, Windows/menu key,
  and model-dependent backlight timeout, discrete GPU and LCD overdrive controls.
  `Nitro_MainWindow_Octavia` also includes sound-mode, lighting and Planet9 UI.
- `WMIFunction` contains named Acer gaming profile, group LED color, system
  information, fan group behavior/speed and keyboard-setting methods. These are
  boundaries requiring protocol inspection and platform adaptation, not evidence
  that Windows WMI is directly usable from Linux.

## Recovered artwork and geometry

`NitroSense.g.resources` is 13,581,869 bytes with SHA-256
`501a274df16fc191f9172fc1fbb3f86c1fba668e494e216eb464f86d01dc0f8b`.
`scripts/extract_ui_resources.py` verifies this hash and extracts its 270 stream
members without loading any target assembly. Exact per-member lengths/hashes are
in `evidence/ui-resource-index.json`. Files are under
`extracted/ui-analysis/resources/`.

Important recovered members:

| Member | Observation |
|---|---|
| `images/100/img_bg_nitro.png` | 1320×760 original NitroSense/acer shell artwork |
| `images/100/img_bg_newboard_nitro.png` | 1152×624 original upper fan panel and lower power/monitoring panels |
| `images/100/img_fan.png` | 200×200 fan graphic |
| `images/100/img_lighting_zone.png` | 816×228 keyboard/zone graphic |
| `nitro_fancontrolpage.baml` | Compiled WPF control tree retained |
| `nitro_mainwindow_octavia.baml` | Compiled WPF main layout retained |
| `lang/en.baml` | Compiled English dictionary retained |
| `font/*.ttf` | Acer Foco font variants retained |

Recovered main constructor explicitly places 1152×312 fan and monitoring pages
in successive content rows. BAML has 1320-wide main window and the matching
background resource references. Exact XAML has now been recovered under `extracted/decompiled-xaml/` using
ILSpy 10 with .NET Framework reference assemblies. Windows runtime pixel
comparison remains outstanding. XAML confirms the main grid rows are 92, *, 44;
content starts at (84,92). Fan columns are 36,220,32,160,*,*,160,112; the two fan
images are 200×200 and start at local y=60. The preview now follows these
coordinates for its background, fan displays, mode controls and panel headings.
Lighting popup main grid is 867.84×488.16, with 24-pixel side columns.

## Implemented native preview and remaining gaps

`nitro_sense/ui.py` uses PySide6 and the extracted original local artwork.
Major fan-panel geometry follows recovered XAML. The lighting popup currently
provides a disabled summary rather than its original full control tree. It
scales its scene, reads real backend sensor names, and plots temperature history.
No fake RPM or CPU/GPU label mapping is shown for unclassified fan sensors. Auto,
Max and a custom fan request dialog are enabled only when the backend advertises
verified availability; failures are visible. Closing calls backend cleanup,
which restores automatic control if it owned the fans. Lighting and power
controls remain unavailable pending actual platform implementations.

This is a reconstruction preview, not UI-to-UI/feature-to-feature parity. Some
geometry, custom WPF styles, original fonts, animation, graph interaction,
localization, all settings/audio/profile functions and Windows behavior remain
unimplemented or unverified. Qt portability does not establish a working Windows
hardware backend. No Acer runtime was launched.

Validation: actual Qt offscreen launch and screenshot succeeded, including the
real Linux backend. `evidence/ui-preview.png` is a reconstruction screenshot,
not a screenshot of the original Acer app. Hardware actions were not exercised
by this UI smoke check.
