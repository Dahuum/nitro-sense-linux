# Original monitoring and power panel reconstruction

This pass targets the supplied NitroSense3.1.3056.0 AN515-45 package and native Qt
presentation. It does not claim a Windows runtime screenshot comparison. The UI
assembly identity is SHA-256
`f71a2eebf07f11e91337a0f5de7feefda54e96d8b007d3904adf4f459856b2cd`;
REA managed/member record IDs and local artifact provenance are retained in
`docs/ui-evidence.md`, `docs/protocol-evidence.md` and `evidence/public-summary.json`.
Recovered XAML/C# remain local and are not distributed as source.

## Correct target and conditional branch

`App.cs:41–43` selects `Nitro_MainWindow_Octavia` for machine type1, as declared
by the supplied AN515-45 `Feature.ini`. `Nitro_MainWindow_Octavia.cs:322–354`
selects the2022 monitor for feature type2, otherwise the Acer-mode monitor only
when `Startup._isSupport_AcerMode`, and the standard `Nitro_MonitoringPage`
otherwise. `Startup.cs:202–211` derives that flag from a Windows AcerGUID registry
check. The registry's actual value is not established on this Linux installation.
The implementation defaults to the standard three-profile view; it can show the
four-entry Acer-mode layout with `acer_mode=True` without inventing an operational
Acer Optimized Linux power profile.

## Recovered geometry

The lower whole panel is1152×312 at global shell84,404. Its first312 pixels are
the power panel; the remaining840 are monitoring. These measurements come from
`NitroSense.Nitro_MonitoringPage.xaml` and its Acer-mode variant:

| Element | Native geometry | Source relationship |
|---|---|---|
| Power widget |312×312, shell84,404 | Standard monitor column0 width312 |
| Monitoring widget |840×312, shell396,404 | Standard monitor column1 |
| CPU chart |0,40,720,100 in monitoring widget | Rows6+29+5; column720 |
| GPU chart |0,172,720,100 | CPU100 +27+5 after y40 |
| CPU values |x735, within y40..140 | Column720+15; temp font28/red |
| GPU values |x735, within y172..272 | Same display arrangement |
| Temperature line/value |#E60000 | Recovered C# AddLineDefinition and XAML text |
| Usage line/value |#FF7800 | Same sources |
| Min/max labels |x578 and649;12px grey | XAML578px first header column plus four35.5px cells |
| Unit header |x0,y6,height29;14px grey | XAML unit heading |
| AC/Battery tabs |x26/146,y42,120×32 | Tab host startsx18 and template header has8px inset |
| Power choices |x18,y80/152/224,257×56 | Standard row6+60+12+60+12+60 inside tab content |

`OriginalMonitoringWidget` is positioned at396,404 and
`OriginalPowerWidget` at84,404 by the parent shell. Neither adds a Linux status
footer, graph-type selector, export button or diagnostic text into the original
panel. Parent-owned Linux extensions can remain outside the parity surface.

## Graph and pointer interactions

Recovered `Nitro_MonitoringPage.cs:59–91,621–697,733–880,941–1052,1055–1199`
establish720 samples per series and a ring insertion index. Each sample occupies
one horizontal pixel; the newest sample is on the right. Temperature and usage
share the0–100 graph scale, and each polygon shadow uses15% opacity. Min/max
retain the run's observed temperatures rather than only the last visible window.
Changing C/F converts displayed temperatures and hover labels; graph physical
scaling remains Celsius/percent in the recovered standard drawing methods.

The native module stores `Sample(time,temperature,usage)` objects in a bounded
720-entry deque and draws matching red/orange1px traces. Hover in recorded space
shows a vertical grey line plus an84×64 three-line timestamp/temperature/usage
popup at cursor+10,+15. Moving into unrecorded space or leaving the graph hides
both. The original GPU idle branch also has a168px-wide notice popup; this
implementation does not infer idle from an absent Linux sensor. Missing readings
remain `--`, and no fabricated measurement is inserted.

The original main polling thread contains sleeps, and its full effective sample
cadence depends on work performed in that loop. The native widget appends once
per supplied snapshot; it does not claim that720 entries establish an exact
Windows recording duration.

## Power interaction and OS boundary

The original view has AC and Battery tabs, power-saver/balanced/high-performance
radio choices, hover grey and selected red states, and an optional fourth Acer
Optimized choice. Tab changes alone do not invoke a power write in this native
implementation. Only an explicit enabled profile click calls
`backend.set_power_profile()`; initial snapshots and tab synchronization do not.

Linux exposes an active Power Profiles Daemon profile rather than two independently
stored Windows scheme configurations. The parent snapshot must supply
`ac_online` as an actual boolean. The inactive source tab remains inspectable,
but its writes are unavailable. Unknown power source, unavailable daemon,
unadvertised profiles and Acer Optimized disable their controls with an accurate
reason. The module never reports successful profile selection before the backend
returns. A failed request restores the previous selection and emits
`operationFailed(str)`. This OS boundary remains a real parity limitation.

The power icons are independently drawn energy/gauge motifs in the recovered
icon area; original WPF vector path assets are not copied into public source.
Original local graph artwork is optional through the `assets` argument. Without
it, a native dark grid is drawn. Segoe UI is requested by pixel size, but exact
font availability and platform rasterization still affect visual comparison.

## History clearing is not an established monitor control

`Clear_history.xaml` declares a560×200 confirmation and the text “History will be
cleared.” However, `Clear_history.cs` persists `MacroHistoryRemind`, and the bounded
search found no standard monitoring invocation of this class. It would be an
unsupported inference to insert this macro/history confirmation into the original
monitoring panel. The module provides `clear()` for parent-owned Linux history
extensions, without claiming a recovered monitoring clear button.

## Integration API

```python
monitor = OriginalMonitoringWidget(parent=canvas, assets=assets_path)
monitor.move(396, 404)
monitor.update_state(snapshot, timestamp=None, append=True)
monitor.set_units('C')  # or F, without discarding underlying measurements
monitor.clear()

power = OriginalPowerWidget(backend, parent=canvas, acer_mode=False)
power.move(84, 404)
power.update_state(snapshot)
power.powerChanged.connect(refresh)
power.operationFailed.connect(show_error)
```

`monitor.labels['CPU'/'GPU']` exposes `title`, `min`, `max`, `temperature` and
`usage` labels; `cpu_graph`, `gpu_graph` and `graphs` expose the two chart widgets.
`update_state(...,append=False)` updates labels without adding another sample.
CPU temperature uses the recognized Acer CPU channel first, then known k10temp
or coretemp fallbacks. GPU values come only from the explicit GPU snapshot.

## Verification and open work

Nine native offscreen tests cover exact chart geometry, bounded/right-aligned
history, timestamp hover/leave, unit conversion without history loss, missing
readings, recognized sensor preference, no startup/tab writes, explicit profile
dispatch/error restoration, source/profile capability gates and unavailable Acer
Optimized mapping. These tests use a fake backend and write no physical hardware.

A Windows reference baseline is still needed for final raster/interaction
comparison, including curve rasterization, tab/font metrics, tooltip placement
under display scaling, Aero/window composition, optional Acer-mode selection and
GPU-idle behavior. Static reconstruction and passing native tests do not prove
those unknowns resolved.
