#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="$project_dir/.venv"
app_id="io.github.chise0519.deskpet"
applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons_dir="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
desktop_file="$applications_dir/$app_id.desktop"
icon_file="$icons_dir/$app_id.svg"

if command -v apt-get >/dev/null 2>&1; then
    echo "安装 Ubuntu 运行依赖（可能要求管理员密码）…"
    sudo apt-get update
    sudo apt-get install -y python3-venv libxcb-cursor0
fi

python3 -m venv "$venv_dir"
"$venv_dir/bin/python" -m pip install --upgrade pip
"$venv_dir/bin/python" -m pip install -e "$project_dir"

install -d -m 700 "$applications_dir"
install -d -m 755 "$icons_dir"
install -m 644 "$project_dir/packaging/linux/$app_id.svg" "$icon_file"

DESKPET_EXEC="$venv_dir/bin/deskpet" \
DESKPET_ICON="$app_id" \
DESKPET_TEMPLATE="$project_dir/packaging/linux/$app_id.desktop.in" \
DESKPET_DESKTOP="$desktop_file" \
python3 - <<'PY'
import os
from pathlib import Path

template = Path(os.environ["DESKPET_TEMPLATE"]).read_text(encoding="utf-8")
executable = os.environ["DESKPET_EXEC"]
escaped = executable.replace("\\", "\\\\").replace('"', '\\"')
escaped = escaped.replace("`", "\\`").replace("$", "\\$")
content = template.replace("@EXEC@", f'"{escaped}"')
content = content.replace("@ICON@", os.environ["DESKPET_ICON"])
target = Path(os.environ["DESKPET_DESKTOP"])
target.write_text(content, encoding="utf-8")
target.chmod(0o644)
PY

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir" >/dev/null 2>&1 || true
fi

echo "DeskPet 安装完成。可从应用菜单搜索 DeskPet，或运行：$venv_dir/bin/deskpet"
