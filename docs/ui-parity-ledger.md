# Original UI and interaction parity ledger

The main mission is matching the original AN515-45 presentation and interaction
contract. This ledger separates recovered facts, implementation obligations and
unknown runtime state. It audits the initial Linux release as the baseline;
concurrent implementation work may close listed gaps without changing the
original evidence.

## Target identity and evidence

- Supplied Windows GUI: NitroSense3.1.3056.0, SHA-256
  `f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd`.
- REA managed identity/member records remain identified by
  `ev_6ca067e5ad67218ddc64f2d22f5dac0709ecb8a1931631f4481401bf8e0a3f75`
  and `ev_2df276a6ff340dd8c8c68693bf6c75893d0bac1c4cd66c9c4856f662a602536f`.
- Model `Plugs/Nitro AN515-45/Feature.ini` declares MachineType1, Year2021 and
  Planet9 enabled. This is package configuration, not a capture of installed
  Windows registry values or hardware effects.
- `App.OnStartup`, recovered `App.cs:36–51`, selects
  **Nitro_MainWindow_Octavia for MachineType1**. The older `Nitro_MainWindow`
  lacks the lighting/sound toolbar and is not the correct main-shell branch.
- Source observations below come from ILSpy-recovered XAML/C# authenticated to
  that artifact. Recovered code is not original source and does not establish
  that Windows executed a particular handler/state on this laptop.
- Raw XAML, decompiled bodies, bitmaps and fonts remain local. Published bounded
  layout/control metadata is in `nitro_sense/ui_contract.json`; its generator is
  `scripts/inspect_ui_contract.py`. It records source hashes and explicitly
  excludes vector path strings, original XAML and embedded payloads.

## Mission questions

| Question | Status | Evidence / next step |
|---|---|---|
| Correct model/main-shell branch? | Answered statically | MachineType1 → Octavia in App.cs |
| Main/fan geometry and controls? | Answered at100%DPI | XAML grid/alignments, selected derived bounds in contract |
| Original style dictionary available? | Answered | All four DPI `style/*/psstyle.xaml`, languages and bitmap assets were already recovered |
| Fan action timing and enablement? | Answered statically | Original click/value/drag handlers listed below |
| Original monitoring and lighting structure? | Answered structurally | Dedicated XAML and sibling parity reports; dynamic Windows state still conditional |
| Exact installed Windows feature visibility? | Partial | Registry-dependent AcerGUID, keyboard color, LCD/dGPU/audio branches require actual runtime baseline |
| Windows screenshot/input-sequence baseline? | Unresolved here | Parent runtime investigation owns any original execution/capture |
| Cross-platform glyph/raster/popup behavior identical? | Unresolved | Segoe UI substitution and window-system behavior require comparison, not assertions |

## P0 — shell and branch selection

The declared window is1320×760, frameless, transparent, center-screen and
`CanMinimize`, with uniform Viewbox scaling. Its sizing helper scales down when
screen work-area height is smaller, preserving aspect ratio. This differs from
an ordinary resizable Qt window with an added40px status footer. The original
outer client composition has no Linux-specific footer.

The content origin is x84,y92 and size1152×624. Fan content is1152×312 at the top;
monitoring is1152×312 below it at global y404. Power/monitoring section labels
are independently placed in the main shell at y388, above their lower content.

### Header bounds at100%DPI

These are selected derived client coordinates; WPF vertical center alignment is
calculated after the top margin, rather than treating margin as y directly.

| Control | x,y | Width×height | Notes |
|---|---|---|---|
| Close |1209,57|26×20|Shutdown action, not close-to-tray |
| Minimize |1166,57|28×20|Explicit WindowState.Minimized |
| Settings |1125,54|26×26|Popup toggle |
| Sound |1075,54|35×26|Octavia audio-mode popup |
| Lighting |1025,54|35×26|Visible when keyboard-color registry state equals2 |
| Planet9 base |987,55|18×27|Visible from package setting; constructor adjusts position when lighting absent |

GeForce Experience is visible only if one of two Windows installation paths
exists; its constructor branch hides it otherwise. A Linux reconstruction should
not invent a working NVIDIA Experience launcher. Planet9 support is present in
this model package; it is not a reason to silently remove the header control when
matching the original layout.

`Main_Grid_MouseDown` initiates window drag on a left click; focus handlers remove
text-box focus through the transparent title rectangle. Header close shuts down
the application. Any retained Linux tray behavior should have a separate explicit
entry point so the original close button does not unexpectedly mean Hide.

### Registry-dependent monitoring variant

Octavia uses `Nitro_MonitoringPage_2022` only for MachineType2. For MachineType1 it
selects `Nitro_MonitoringPage_Acermode` if `_isSupport_AcerMode` is true; otherwise
it selects `Nitro_MonitoringPage`. Startup derives this support through
`Check_Acer_Mode` and an installed Windows `AcerGUID` registry value. The package's
Year2021 alone does not prove which of those two monitoring variants was active
in a real Windows install. Do not present a chosen Linux equivalent as a recorded
Windows runtime fact.

## P0 — fan controls and dispatch policy

The fan page grid produces these global bounds:

| Control | x,y | Width×height |
|---|---|---|
| Auto / Max / Custom |120,170 /238 /306|220×56 each |
| CPU / GPU fan artwork |540,152 /756,152|200×200 each |
| CPU / GPU sliders |372,275 /964,275|160×28 each |
| CPU Auto checkbox |452,315|80×20 |
| GPU Auto checkbox |964,315|80×20 |

Mode controls are styled checkboxes made mutually exclusive by handlers, with
custom fan icons and text, not ordinary circular radio indicators. The original
mode templates reserve a36px icon and134px text area; normal foreground is
#4C4C4C and selected/hover states are declared in the recovered dictionary.

`SpeedSliderStyle` declares range0–10, SmallChange1 and LargeChange1. Handlers
multiply the integer slider position by10 for device percentages. The previous
Linux1–100% continuous controls and an extra Apply button are functional
alternatives, not exact interaction parity.

| User action/state | Recovered behavior |
|---|---|
| Auto selected | Hides both sliders and their Auto checkboxes; enables CoolBoost; requests firmware Auto |
| Max selected | Hides custom controls; disables CoolBoost; requests Max |
| Custom selected | Shows custom controls; disables CoolBoost; immediately sends stored Auto/manual flags and percentages |
| Clicking an already checked mode | Handler rechecks and returns, avoiding a second substantive dispatch |
| Individual Auto checkbox toggled | Disables/enables associated slider and immediately dispatches that fan's state |
| Slider changed outside drag | Applies the new quantized percentage immediately |
| Thumb drag starts | Sets a drag flag, suppressing ValueChanged device updates |
| Thumb drag completes | Applies once using final value, then clears the drag flag |
| Startup loading | `App.initial_flag` suppresses the handlers' hardware writes during initial state population |

Source: `Nitro_FanControlPage.cs:110–118,181–219,337–417,477–513,561–593`.
This establishes user-action policy. It is not authorization to write physical
hardware from tests or as a side effect of constructing a Qt widget. New widgets
must retain an initialization guard and tests using fake backends.

### Fan animation

`PushData_CPU` and `PushData_GPU1` render the incoming measured RPM text and rotate
by negative360 degrees over an integer period:

- Period seconds = `11 - floor(rpm / 450)`.
- Measured RPM above4500 sets the period to2 seconds.
- Zero RPM freezes at the last angle.
- A new animation is started only when the derived period changes.

This differs from the previous custom proportional degrees-per-second formula.
It is a screen animation mapping, not actual blade rotation at measured RPM.

### Poll cadence

Octavia's `pollingMainWindowsStatus` has separate temperature/usage and fan loops:
4000ms after each temperature/usage update and5000ms after each fan update. CPU
usage code also takes a1000ms sampling interval. The previous Linux single2s
refresh is not the original timing. Backend probes may stay separate and bounded,
but visible history cadence must be explicitly reconciled with this contract.

## P0 — original popups and visual state

The settings action toggles a light-gray popup, not a dark multi-tab settings
window. Octavia defines width340 and a base291px settings grid. Runtime feature
checks remove rows:255px when one of LCD/dGPU is hidden,219px when both are
hidden. The actual installed feature flags are still unknown; the model package
mentions LCD among its advanced capabilities, so219px must not be assumed solely
because the Linux backend has no corresponding interface.

- Popup fill #DADADA; ordinary text #191919/#666666.
- Toggle background/knob defaults #242424/#4C4C4C.
- Checked toggles use background #005966 and knob #00AEC7. Universal red modern
  toggle styling would be visually incorrect even though the product is Nitro.
- Opening settings shows a transparent input mask and focuses Sticky Keys.
- Closing hides the mask and returns focus to Settings.
- Escape closes the popup; outside click dismisses `StaysOpen=False` popups.
- Unit changes are immediate and update graph labels/current values; selected
  unit text is red #E60000 and the other is #808080.

Original settings contain Advanced Settings (Sticky Keys, Windows/Menu key,
units and conditional dGPU/LCD) plus Keyboard Settings (backlight timeout).
Battery/USB, profiles and debug/history exports are useful Linux extensions, but
placing them in the main original popup changes its layout and navigation. Keep
extensions separate when the goal is the original surface.

The lighting content is an overlay attached to a1320×760 shell grid; its visible
central outline is roughly868×488, rather than a standard decorated dialog. The
sound popup selects DTS versus TrueHarmony branches using `DTS_Audio_Support`;
opening it focuses the appropriate first radio item. Unsupported native audio
operations must remain honestly unavailable even if their UI is reproduced.

## P1 — resources and typography

All of these are already available locally:

- `extracted/decompiled-xaml/style/100/psstyle.xaml`, plus125,150 and200 variants.
- `extracted/decompiled-xaml/lang/en.xaml`, plus other shipped language dictionaries.
- `extracted/ui-analysis/resources/images/{100,125,150,200}/`.
- Ten AcerFoco TTF faces under the local resource `font/` folder.

The100%DPI dictionary maps the primary brushes to `img_bg_nitro.png`,
`img_bg_newboard_nitro.png`, `img_fan.png`, `img_monitor_chart.png`,
`img_monitor_chartshadow.png` and `img_planet9_small.png`. Toolbar and mode buttons
are largely vector templates, not missing bitmap assets. The bounded contract
records image resource-key/path mappings without copying payloads.

Startup selects100% resources at96DPI;125% at120–143DPI;150% at144–191DPI;200% at
192DPI and above. Native uniform rescaling and the Windows resource-tier choice
are related but not identical behaviors.

Main/fan XAML declares **Segoe UI**. On the current Linux host `fc-match 'Segoe UI'`
resolves to **Adwaita Sans**, so glyph widths and rasterization cannot be assumed
identical. The presence of AcerFoco files does not prove they are the correct main
font. Local original artwork/fonts can support personal rendering; public
fallback skin cannot honestly claim the same bitmap pixels without the original
resources and a controlled rendering baseline.

## Completion and verification gates

A trustworthy parity claim needs all of the following:

1. Model/runtime branch fixed and every uncertain feature flag documented.
2. Original shell size, page origins, toolbar, menu shape and control geometry
   checked against the exported factual contract at a declared DPI.
3. Hover, focus, selected, disabled and popup states exercised with fake device
   transports, including keyboard navigation and Escape/outside click behavior.
4. Original user actions dispatch with the same timing/quantization; initialization
   never accidentally sends requests in software tests.
5. Original screenshot/input traces captured in an appropriate runtime, then
   side-by-side/pixel comparison with the native Qt implementation. Static XAML
   rendering tests are not a substitute for a real Windows runtime baseline.
6. Remaining font, operating-system power/audio/input and unsupported hardware
   differences stay explicit rather than being marked complete by unit tests.

No original executable was run and no hardware operation was performed by this
audit task. Parent agents own integration and any runtime/hardware observation.
