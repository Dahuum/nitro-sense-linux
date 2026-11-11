#!/usr/bin/env bash
# Remove only files installed by setup-driver.sh; never unload active modules.
set -euo pipefail
usage() {
  cat <<'HELP'
Usage: sudo ./scripts/remove-driver.sh [--user LOGIN] [--kernel VERSION] [--dry-run]

Removes this project's module, boot configuration, and permission integration.
Defaults to the running kernel. Repeat --kernel for another installed kernel.
--user LOGIN removes that account from the nitrosense group; the group is kept.
An already loaded module stays active until an explicit unload or reboot.
HELP
}
login_user=''
kernel_version=$(uname -r)
dry_run=0
while (($#)); do
  case "$1" in
    --user) (($# >= 2)) || { usage >&2; exit 2; }; login_user=$2; shift 2 ;;
    --kernel) (($# >= 2)) || { usage >&2; exit 2; }; kernel_version=$2; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ $(id -u) = 0 ]] || { printf 'Run with sudo.\n' >&2; exit 1; }
[[ $kernel_version =~ ^[a-zA-Z0-9._+-]+$ && $kernel_version != '.' && $kernel_version != '..' ]] || { printf 'Invalid kernel version.\n' >&2; exit 2; }
if [[ -n $login_user ]]; then
  [[ $login_user =~ ^[a-z_][a-z0-9_-]*[$]?$ && $(id -u "$login_user") != 0 ]] || { printf 'Supply an existing non-root login.\n' >&2; exit 2; }
fi
module_dir="/lib/modules/$kernel_version/extra/nitro-sense"
printf 'Remove module: %s/linuwu_sense.ko\nRemove owned permission/boot integration.\n' "$module_dir"
if ((dry_run)); then
  printf 'Dry run: no changes made.\n'; exit 0
fi
fan_control=/sys/devices/platform/acer-wmi/nitro_sense/fan_speed
if [[ -e $fan_control ]]; then
  fan_state=$(cat "$fan_control")
  [[ $fan_state = '0,0' ]] || { printf 'Close the app and restore automatic fans before removing control permissions. No changes made.\n' >&2; exit 1; }
fi
if [[ -d /run/systemd/system ]]; then
  systemctl disable --now nitro-sense-permissions.service 2>/dev/null || true
fi
rm -f -- /etc/systemd/system/nitro-sense-permissions.service \
  /etc/udev/rules.d/70-nitro-sense.rules \
  /etc/modules-load.d/nitro-sense.conf \
  /etc/modprobe.d/nitro-sense.conf \
  /usr/libexec/nitro-sense-permissions \
  "$module_dir/linuwu_sense.ko"
rmdir -- "$module_dir" 2>/dev/null || true
if [[ -d /lib/modules/$kernel_version ]]; then
  depmod -a "$kernel_version"
fi
if [[ -d /run/systemd/system ]]; then
  systemctl daemon-reload
fi
if command -v udevadm >/dev/null; then
  udevadm control --reload-rules
fi
# Revoke only the group permission this installer granted, using the same allowlist.
for relative in \
  nitro_sense/fan_speed nitro_sense/coolboost nitro_sense/backlight_timeout \
  nitro_sense/battery_limiter nitro_sense/usb_charging \
  four_zoned_kb/four_zone_mode four_zoned_kb/per_zone_mode
do
  target="/sys/devices/platform/acer-wmi/$relative"
  if [[ -f $target && ! -L $target && $(stat -c %G "$target") = nitrosense ]]; then
    chgrp root "$target"
    chmod 0644 "$target"
  fi
done
if [[ -n $login_user ]]; then
  case " $(id -nG "$login_user") " in
    *" nitrosense "*) gpasswd -d "$login_user" nitrosense ;;
  esac
fi
printf 'Removed installation files. The module was not unloaded; close the app and reboot when convenient.\n'
printf 'Any module installed for a different kernel needs a separate --kernel removal.\n'
