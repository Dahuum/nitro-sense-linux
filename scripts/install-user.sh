#!/usr/bin/env sh
# Install the native application into the current user's isolated environment.
set -eu
if [ "$(id -u)" = 0 ]; then
  printf 'Run this script as your normal desktop user, without sudo.\n' >&2
  exit 1
fi
repo_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
application_dir="${XDG_DATA_HOME:-$HOME/.local/share}/nitro-sense-linux"
python -m venv --system-site-packages "$application_dir/venv"
"$application_dir/venv/bin/python" -m pip install "$repo_dir"
mkdir -p "$HOME/.local/bin" "${XDG_DATA_HOME:-$HOME/.local/share}/applications" "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
for command_name in nitro-sense nitro-sense-import-assets; do
  if [ -e "$HOME/.local/bin/$command_name" ] && [ ! -L "$HOME/.local/bin/$command_name" ]; then
    printf 'Refusing to replace existing regular file: %s\n' "$HOME/.local/bin/$command_name" >&2
    exit 1
  fi
  ln -sfn "$application_dir/venv/bin/$command_name" "$HOME/.local/bin/$command_name"
done
# Desktop launchers do not universally inherit ~/.local/bin in PATH.
"$application_dir/venv/bin/python" - "$repo_dir" "$application_dir" <<'PY'
from pathlib import Path
import os, sys
source, application = map(Path, sys.argv[1:])
text=(source/'packaging/nitro-sense.desktop').read_text()
exe=str(application/'venv/bin/nitro-sense').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
text=text.replace('Exec=nitro-sense --enable-control',f'Exec="{exe}" --enable-control')
base=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
(base/'applications/nitro-sense.desktop').write_text(text)
(base/'icons/hicolor/scalable/apps/nitro-sense.svg').write_bytes((source/'packaging/nitro-sense.svg').read_bytes())
PY
printf 'Installed. Launch: %s/.local/bin/nitro-sense\n' "$HOME"
printf 'Driver setup is separate: see docs/installation.md.\n'
