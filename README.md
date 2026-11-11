<div align="center">

# NitroSense Linux

### Native laptop controls for Linux.

Fan control, four-zone keyboard lighting and monitoring for the Acer Nitro AN515-45.<br>
Python · PySide6 / Qt · Linux WMI · MIT application / GPL driver

**Release v0.2.0 · Native desktop · AN515-45 hardware tested**

[Website](https://dahuum.github.io/nitro-sense-linux/) · [Downloads](https://github.com/Dahuum/nitro-sense-linux/releases) · [Get started](#get-started) · [What works](#what-works) · [Documentation](#documentation) · [Contribute](CONTRIBUTING.md)

<img src="evidence/ui-native.png?v=0.2.0" width="1000" alt="Actual NitroSense Linux native desktop application with CPU and GPU fan RPM, power profiles and temperature monitoring">

*Actual native application on the development laptop, using independently drawn artwork.*

</div>

NitroSense Linux brings your laptop’s fan controls, keyboard lighting, device settings and live monitoring to a native Qt desktop. The application reads Linux sensors and communicates with Acer firmware through a reviewed, locally patched Linuwu-Sense driver. Run the desktop app as your normal user; administrator access is limited to driver setup.

This is an independent community project, **not affiliated with Acer**. It is an initial release with deliberately narrow hardware support. Original layouts and commands informed the reconstruction; full Windows-software parity has not been established.

## What works

| Capability | Current status |
| --- | --- |
| Auto / Max fan control and measured CPU/GPU RPM | Verified on the development laptop: **3125 / 3703 → 5769 / 5660 RPM**, then Auto restored |
| Independent custom CPU/GPU fan percentages | Physically tested: **60% / 70% → 4615 / 5769 RPM**, then Auto restored |
| Static four-zone RGB; Breathing and Wave | **Visible colors/effects verified** on the development laptop after the v0.2.0 lighting fix |
| Neon, Shifting and Zoom; effect controls and color palettes | Implemented and software-tested; these effects remain visually unverified |
| CoolBoost, keyboard timeout, battery limit and USB charging thresholds | Set/readback tested; original settings restored afterward |
| CPU/NVIDIA GPU telemetry, memory, history, min/max and CSV export | Implemented with real sensor sources; native UI and export software-tested |
| Linux power profiles | Balanced set/readback tested; original performance profile restored |
| Local profiles, JSON import/export, preferences, tray and diagnostics | Implemented and software-tested; loading/importing never applies settings |
| Fan restoration on handled termination | Real normal-user GUI SIGTERM test: **manual 60 / 70 → clean exit → Auto 0 / 0** |
| Windows/macOS backends, Acer proprietary audio processing and Windows accessibility controls | **Unavailable** |

**39 automated tests**, native GUI smoke checks, package checks and GitHub CI are separate from hardware validation. Read the [feature matrix](docs/feature-parity.md), [runtime records](evidence/) and [backend contract](docs/backend.md) for exactly what was observed.

**Supported write target:** **Acer Nitro AN515-45**. Hardware testing used **BIOS V1.08** and **Linux 6.18.39-1-lts**. The backend requires the exact Acer/model identity and recognized writable interfaces before enabling hardware changes. Other Nitro/Predator models are not assumed compatible, even if the underlying driver lists them. General Linux telemetry can work without the driver.

## Get started

### Pick your package

| Platform / package | Scope |
| --- | --- |
| Linux — Python wheel | Native application; Python 3.10+ and PySide6 6.8+ required |
| Linux — source archive | Application, kernel driver source, setup/removal scripts, documentation and tests |
| Windows / macOS | No native backend or download is published |

Download only files actually attached to **[Releases](https://github.com/Dahuum/nitro-sense-linux/releases/tag/v0.2.0)** and compare them against that release’s `SHA256SUMS`. The wheel resolves PySide6 through pip; it is **not a self-contained AppImage** and does not install a kernel driver automatically.

| Published file | Download |
| --- | --- |
| Application wheel | [nitro_sense_linux-0.2.0-py3-none-any.whl](https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.2.0/nitro_sense_linux-0.2.0-py3-none-any.whl) |
| Source and driver | [nitro_sense_linux-0.2.0.tar.gz](https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.2.0/nitro_sense_linux-0.2.0.tar.gz) |
| Checksums | [SHA256SUMS](https://github.com/Dahuum/nitro-sense-linux/releases/download/v0.2.0/SHA256SUMS) |

**Registry status:** releases are published on GitHub. No PyPI, AUR, Flathub, apt or dnf repository is published. Do not install an unrelated similarly named package as a substitute.

### Install the application

Clone the source and create an isolated Python environment:

```sh
git clone https://github.com/Dahuum/nitro-sense-linux.git
cd nitro-sense-linux
python -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/nitro-sense
```

If your distribution already provides PySide6, `python -m venv --system-site-packages .venv` can reuse it. To install a downloaded wheel instead, create the environment and run its pip on the `.whl` file. Platform libraries, Qt display backends and troubleshooting are covered in the [installation guide](docs/installation.md).

For a user-owned environment, menu entry, icon and `~/.local/bin/nitro-sense` launcher, run **`./scripts/install-user.sh` without sudo**. The native application opens directly; no development web server is required.

### Set up hardware access

Install build tools, kernel module utilities and headers matching your **running kernel**. On Arch with the LTS kernel, these normally include `base-devel` and `linux-lts-headers`; other kernels need their own matching headers.

From the source checkout or unpacked source archive:

```sh
# Review destinations and operations without changing anything.
sudo ./scripts/setup-driver.sh --user "$(id -un)" --boot --dry-run

# Build/install the driver, narrow group permissions and boot startup.
sudo ./scripts/setup-driver.sh --user "$(id -un)" --boot
```

The installer never unloads an active module. Reboot/log back in so the driver and `nitrosense` group membership take effect. Where no competing driver is bound, manual loading is `sudo modprobe linuwu_sense`. Secure Boot may require locally signing the module. **Rebuild after a kernel upgrade:** no machine-specific precompiled module is distributed.

Then launch **NitroSense Linux** from the application menu or run `nitro-sense` as your regular user. Do not run the GUI with sudo. See [installation, updates and removal](docs/installation.md) for the complete process and exact system changes.

## Explore without changing hardware

```sh
nitro-sense --read-only
nitro-sense --diagnose
```

Read-only mode disables hardware and power-profile changes. Diagnostics print actual available telemetry and capabilities without applying settings. Missing sensors remain unavailable rather than showing invented values. This is **not a simulated hardware demo**; the website’s interactive examples are separately labeled recorded samples.

<details>
<summary>Use your original NitroSense artwork locally</summary>

The default native skin works on its own. If you have the exact original NitroSense 3.1.3056.0 Acer ZIP, import its artwork with:

```sh
.venv/bin/nitro-sense-import-assets /path/to/Nitro_Sense_Acer_3.01.3056_W11x64_A.zip
```

The importer verifies the assembly/resource-stream SHA-256 and reads only images/fonts without executing Acer code. Artwork is stored in `~/.local/share/nitro-sense/assets`. The [artifact identity record](evidence/artifact-identities.json) identifies the supported package.

Set `NITRO_SENSE_ASSETS=none nitro-sense` to force the independent skin, or point `NITRO_SENSE_ASSETS` at a directory of locally imported resources. Proprietary artwork is not included in releases.

</details>

## Apply a hardware change

1. Start the application on the supported laptop with the driver loaded and recognized interfaces writable.
2. Choose Auto or Max, or stage independent custom fan settings and use **Apply**. Slider release can apply a staged custom request.
3. In Lighting, choose static zones or a dynamic effect, then explicitly press **Apply**.
4. Save a local profile to keep a draft. Selecting, loading or importing one does not configure hardware; **Apply selected profile** sends its fan and lighting requests.
5. Inspect measured fan RPM and firmware readback. Check keyboard colors/effects visually; successful command acceptance alone does not prove visible behavior.

The application does not apply saved profiles automatically at startup. Battery calibration is excluded from automated controls. Run one configurator at a time, and read the [backend behavior](docs/backend.md) before testing an unvalidated effect.

### Return fans to automatic control

Normal exit and handled SIGINT/SIGTERM request Auto after manual changes. Closing to the tray intentionally keeps the app and fan mode running. SIGKILL, kernel/firmware failure and disappeared interfaces cannot be repaired by a stopped Python process.

To request firmware Auto directly:

```sh
printf '0,0\n' | sudo tee /sys/devices/platform/acer-wmi/nitro_sense/fan_speed
```

## Diagnostics

```sh
nitro-sense --version
nitro-sense --diagnose
```

Share only sanitized output in a [GitHub issue](https://github.com/Dahuum/nitro-sense-linux/issues), together with model, kernel, app version and reproducible steps. Do not upload passwords, tokens, serial numbers, original installers or complete private hardware backups.

Profiles/preferences are local to `$XDG_CONFIG_HOME/nitro-sense-linux/profiles.json` (normally `~/.config/nitro-sense-linux/profiles.json`). Import files are bounded and validated as JSON; they do not execute commands.

## Development

```sh
QT_QPA_PLATFORM=offscreen NITRO_SENSE_ASSETS=none \
  python -m unittest discover -s tests -v

QT_QPA_PLATFORM=offscreen NITRO_SENSE_ASSETS=none \
  python -m nitro_sense --smoke-test --screenshot /tmp/nitrosense.png

python -m pip install build
python -m build
```

`backend.py` owns capability detection, telemetry and validated device operations. `ui.py` owns native presentation; `profiles.py` handles local persistence and input validation. `protocol.py` retains pure recovered command encoders without hardware I/O. Tests use temporary sysfs fixtures and fake GUI backends; ordinary CI never writes physical hardware.

The buildless landing page lives in `website/` and publishes through GitHub Pages. Its [reference analysis and design system](docs/website-design-system.md) describe layout, typography, components, interactions and responsive behavior.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding model support or new writes. Passing software tests does not establish physical compatibility.

## Documentation

- [Installation, permissions, troubleshooting and removal](docs/installation.md)
- [Compatibility, implemented features and remaining parity gaps](docs/feature-parity.md)
- [Backend API, capability gates and recovery behavior](docs/backend.md)
- [Hardware investigation and validation](docs/hardware-support.md) · [Runtime test records](evidence/)
- [Protocol findings](docs/protocol-evidence.md) · [Original UI/resource findings](docs/ui-evidence.md)
- [REA evidence identity index](evidence/public-summary.json) · [Artifact identities](evidence/artifact-identities.json)
- [Website design system and reference analysis](docs/website-design-system.md)
- [Release checks](docs/release-checklist.md) · [Changelog](CHANGELOG.md) · [Security](SECURITY.md)

## License and provenance

The new application, website and scripts are [MIT licensed](LICENSE). The modified [Linuwu-Sense driver](driver/PROVENANCE.md) retains its source notices and upstream [GPL license](driver/LICENSE). Qt/PySide6 and self-hosted website fonts retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).

No Acer installer, EXE/DLL, original fonts/artwork or decompiled source is distributed. Raw vendor metadata and reconstruction outputs remain local; bounded protocol findings, hashes and runtime measurements are published. Exact original-software UI, audio, accessibility and Windows-backend parity remain **unfinished**, as documented in the feature matrix.
