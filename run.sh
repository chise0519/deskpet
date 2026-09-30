#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_bin="$project_dir/.venv/bin/python"

if [[ ! -x "$python_bin" ]]; then
    echo "DeskPet 虚拟环境不存在，请先运行：$project_dir/install-ubuntu.sh" >&2
    exit 1
fi

exec "$python_bin" "$project_dir/run_deskpet.py" "$@"
