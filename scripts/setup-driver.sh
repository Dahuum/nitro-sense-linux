#!/usr/bin/env bash
# Build/install the pinned source; never unload or replace an active module.
set -euo pipefail
usage() {
  cat <<'HELP'
Usage: sudo ./scripts/setup-driver.sh --user LOGIN [--boot] [--dry-run]

Builds for the running kernel, installs the module and fixed control permissions.
--user LOGIN  Existing non-root account to add to the nitrosense group (required).
--boot        Load linuwu_sense on future boots and blacklist competing acer_wmi.
--dry-run     Validate inputs and print the planned destinations without changes.

Does not load/unload any module or install missing OS packages. Log out/in after
adding group membership. Without --boot, module loading remains a manual action.
HELP
}
login_user=''
boot=0
dry_run=0
while (($#)); do
  case "$1" in
    --user) (($# >= 2)) || { usage >&2; exit 2; }; login_user=$2; shift 2 ;;
    --boot) boot=1; shift ;;
    --dry-run) dry_run=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ $(id -u) = 0 ]] || { printf 'Run with sudo.\n' >&2; exit 1; }
[[ $login_user =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || { printf 'Supply --user with an existing non-root login.\n' >&2; exit 2; }
login_uid=$(id -u "$login_user")
[[ $login_uid != 0 ]] || { printf 'The target account must not be root.\n' >&2; exit 2; }
[[ $(cat /sys/class/dmi/id/sys_vendor) = Acer && $(cat /sys/class/dmi/id/product_name) = 'Nitro AN515-45' ]] || {
  printf 'This installer supports only the inspected Acer Nitro AN515-45.\n' >&2; exit 1;
}
repo_dir=$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
driver_dir="$repo_dir/driver"
kernel_version=$(uname -r)
module_dir="/lib/modules/$kernel_version/extra/nitro-sense"
[[ -d /lib/modules/$kernel_version/build ]] || { printf 'Install kernel headers matching %s first.\n' "$kernel_version" >&2; exit 1; }
for program in make install depmod modinfo getent groupadd usermod; do
  command -v "$program" >/dev/null || { printf 'Missing prerequisite: %s\n' "$program" >&2; exit 1; }
done
[[ -f $driver_dir/linuwu_sense.c ]] || { printf 'Vendored driver source is missing.\n' >&2; exit 1; }
printf 'Kernel: %s\nModule destination: %s/linuwu_sense.ko\nControl group: nitrosense; user: %s\n' "$kernel_version" "$module_dir" "$login_user"
printf 'Permission helper: /usr/libexec/nitro-sense-permissions\nBoot startup/acer_wmi blacklist: %s\n' "$boot"
if ((dry_run)); then
  printf 'Dry run: no files, groups, module state, or permissions changed.\n'
  exit 0
fi
make -C "$driver_dir" KVER="$kernel_version"
[[ $(modinfo -F name "$driver_dir/linuwu_sense.ko") = linuwu_sense ]] || { printf 'Unexpected module identity.\n' >&2; exit 1; }
module_kernel=$(modinfo -F vermagic "$driver_dir/linuwu_sense.ko")
[[ ${module_kernel%% *} = "$kernel_version" ]] || { printf 'Built module does not match the running kernel.\n' >&2; exit 1; }
install -d -m 0755 "$module_dir" /usr/libexec /etc/udev/rules.d /etc/systemd/system
install -m 0644 "$driver_dir/linuwu_sense.ko" "$module_dir/linuwu_sense.ko"
depmod -a "$kernel_version"
getent group nitrosense >/dev/null || groupadd --system nitrosense
usermod -a -G nitrosense "$login_user"
install -m 0755 "$repo_dir/packaging/nitro-sense-permissions" /usr/libexec/nitro-sense-permissions
install -m 0644 "$repo_dir/packaging/nitro-sense-permissions.service" /etc/systemd/system/nitro-sense-permissions.service
install -m 0644 "$repo_dir/packaging/70-nitro-sense.rules" /etc/udev/rules.d/70-nitro-sense.rules
if ((boot)); then
  install -d -m 0755 /etc/modules-load.d /etc/modprobe.d
  printf 'linuwu_sense\n' > /etc/modules-load.d/nitro-sense.conf
  printf '# Competes for the same Acer WMI platform interface.\nblacklist acer_wmi\n' > /etc/modprobe.d/nitro-sense.conf
fi
if [[ -d /run/systemd/system ]]; then
  systemctl daemon-reload
  systemctl enable nitro-sense-permissions.service
fi
if command -v udevadm >/dev/null; then
  udevadm control --reload-rules
fi
/usr/libexec/nitro-sense-permissions
printf '\nInstalled. No module was loaded or unloaded.\n'
printf 'Log out and back in to activate group membership.\n'
printf 'Manual load (when no competing driver is bound): sudo modprobe linuwu_sense\n'
printf 'Rebuild after kernel upgrades; Secure Boot may require locally signing the module.\n'
if [[ -d /sys/module/acer_wmi ]]; then
  printf 'acer_wmi is currently loaded. This installer left it untouched; reboot after --boot setup.\n'
fi
