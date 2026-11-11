# Installing the native application and Linux hardware driver

The desktop application and hardware driver are separate components. The
application runs as your normal user. Administrator access is needed to install
or load the kernel driver and configure narrowly scoped control permissions.
Only the inspected **Acer Nitro AN515-45** is accepted by the supplied driver
installer. Other models require their own compatibility validation.

## Application

Install the released Python wheel or source package in an environment with
Python and PySide6. The installed `nitro-sense` command starts the native desktop
application. A desktop entry and project-owned SVG icon are provided in
`packaging/nitro-sense.desktop` and `packaging/nitro-sense.svg`; the desktop entry
runs `nitro-sense --enable-control` as the logged-in user. Do not run the GUI with
sudo as the everyday setup.

Application installation and packaging are documented in the repository README.
The driver steps below do not install Python packages or desktop application files.

## Driver prerequisites

- Linux kernel headers matching the kernel from `uname -r`.
- Compiler and Make suitable for building external kernel modules.
- Standard module tools (`modinfo`, `modprobe`, `depmod`) and account utilities.
- For persistent permission integration, systemd and udev.
- Secure Boot systems may require signing the built module with an enrolled key;
  the scripts do not disable Secure Boot or enroll keys automatically.

On Arch systems, use the header package corresponding to the running kernel
(for example `linux-lts-headers` for `linux-lts`) and normal development/module
tools. Installing the newest headers while still running an older kernel is not
sufficient; reboot into the matching kernel or install matching headers first.
The installer does not run a distribution package manager.

## Inspect and install

From the project checkout, inspect the planned destinations without changing the
system:

```sh
sudo ./scripts/setup-driver.sh --user "$USER" --dry-run
```

Install the driver for the running kernel and grant your account access through
the `nitrosense` group:

```sh
sudo ./scripts/setup-driver.sh --user "$USER"
```

To additionally enable driver startup on future boots and blacklist the competing
stock `acer_wmi` module:

```sh
sudo ./scripts/setup-driver.sh --user "$USER" --boot
```

The installer never unloads or replaces a running module. If the stock Acer driver
is already bound, reboot after using `--boot`; do not casually unload it while
applications are using its interfaces. If neither driver is currently bound,
the explicit manual load is:

```sh
sudo modprobe linuwu_sense
```

Log out and back in after the group membership change. Existing terminal/desktop
sessions retain their previous groups until a new login. Verify with:

```sh
id -nG
nitro-sense --diagnose
nitro-sense --enable-control
```

If the driver was already loaded from the development tree, installing a new
module file does not replace the loaded code. Reboot to validate the installed
revision. A successful build or installation is not hardware validation.

## Exact installed footprint

| Path | Purpose |
|---|---|
| `/lib/modules/<kernel>/extra/nitro-sense/linuwu_sense.ko` | Module built from the pinned vendored source |
| `/usr/libexec/nitro-sense-permissions` | Root-owned helper with a fixed sysfs allowlist |
| `/etc/systemd/system/nitro-sense-permissions.service` | Boot/hotplug oneshot permission application |
| `/etc/udev/rules.d/70-nitro-sense.rules` | Requests the oneshot on the Acer platform device's add event |
| `/etc/modules-load.d/nitro-sense.conf` | Driver startup; only with `--boot` |
| `/etc/modprobe.d/nitro-sense.conf` | Blacklists competing `acer_wmi`; only with `--boot` |
| Group `nitrosense` | Members may change only the listed hardware controls |

The permission helper grants group read/write access (`0660`) only to these
existing attributes under `/sys/devices/platform/acer-wmi`:

- `nitro_sense/fan_speed`
- `nitro_sense/coolboost`, when supplied by the local driver revision
- `nitro_sense/backlight_timeout`
- `nitro_sense/battery_limiter`
- `nitro_sense/usb_charging`
- `four_zoned_kb/four_zone_mode`
- `four_zoned_kb/per_zone_mode`

It accepts no caller-selected paths. Calibration and unrelated sysfs attributes
are excluded. Group access allows changing these hardware settings outside the
GUI too; add only the intended desktop user. The helper is applied immediately
for an already loaded driver and reapplied at boot/device creation. No passwordless
sudo rule or permission to modify arbitrary root files is installed.

## Kernel updates and removal

This installer builds for one kernel at a time and does not silently install
DKMS. After a kernel update, boot the new kernel with matching headers and rerun
the installer. Keep another working kernel available while validating driver
compatibility. The vendored source contains source and license/provenance;
precompiled modules are kernel-specific and are not the source distribution.

To remove this project's integration and the running kernel's installed module:

```sh
sudo ./scripts/remove-driver.sh --user "$USER"
```

To inspect the removal plan or remove a module installed for another kernel:

```sh
sudo ./scripts/remove-driver.sh --dry-run
sudo ./scripts/remove-driver.sh --kernel 6.18.39-1-lts
```

Removal disables the permission oneshot, removes the project's own files,
revokes the `nitrosense` group permissions on the fixed attributes, and optionally
removes the specified user's membership. It retains the group and never unloads
an active module. Close the application and reboot when convenient. Other
kernels' module files need separate `--kernel` removal.

## Fan safety and operational limits

The app returns fans to automatic control on normal exit after manual control,
and the locally hardened driver attempts automatic restoration after a partial
fan failure and during unload. **SIGKILL, kernel faults, lost devices, and power
loss can bypass normal application cleanup.** A compiled module and a passing
mocked test cannot establish recovery from those conditions. No background
heartbeat service or hidden hardware-writing daemon is installed by these scripts.

Lighting write acceptance/readback is not proof of a visible color. Firmware may
ignore unsupported modes. See the feature matrix and hardware evidence for the
current on-device validation status. Do not enable battery calibration to test a
GUI setting; that action is deliberately excluded from the backend and permission
allowlist.

## Normal-user app launcher

After downloading/unpacking the source release, `./scripts/install-user.sh`
creates a user-owned isolated environment, app/importer launchers in
`~/.local/bin`, and a desktop entry with an absolute executable path. It reuses
system PySide6 when available, otherwise pip resolves dependencies. Do not run
this user installer with sudo. It is separate from the explicit privileged
driver setup. Remove its links, `~/.local/share/nitro-sense-linux/venv`, and user
desktop/icon files to uninstall the application; profiles and imported assets
can be retained independently.

The development laptop has now been installed using the source installer with
`--user void_id --boot`. A fresh normal-user process recognizes the nitrosense
group and all supported control capabilities without root. Existing desktop
sessions may require logout/login for their group membership to refresh.
