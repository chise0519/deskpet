"""技能管理：带 YAML frontmatter 的 Markdown 指令文件。

技能目录：%APPDATA%/DeskPet/skills/*.md
格式：---\nname: xxx\ndescription: xxx\n---\n正文（给模型的指令）
后续新增技能：丢一个 .md 进目录，或设置里点"添加…"。
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from . import config

_FRONT = re.compile(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", re.S)


def skills_dir() -> Path:
    p = config.data_dir() / "skills"
    p.mkdir(parents=True, exist_ok=True)
    return p


def parse_skill(text: str) -> dict:
    """解析 frontmatter（name/description）+ 正文。无 frontmatter 也接受。"""
    name, desc, body = "", "", text
    m = _FRONT.match(text)
    if m:
        fm, body = m.group(1), m.group(2)
        for line in fm.splitlines():
            line = line.strip()
            if line.startswith("name:"):
                name = line[len("name:"):].strip()
            elif line.startswith("description:"):
                desc = line[len("description:"):].strip()
    return {"name": name or "unnamed", "description": desc,
            "body": body.strip()}


def list_skills() -> list[dict]:
    out = []
    for p in sorted(skills_dir().glob("*.md")):
        try:
            s = parse_skill(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        s["path"] = str(p)
        out.append(s)
    return out


def get_skill(name: str) -> dict | None:
    for s in list_skills():
        if s["name"] == name:
            return s
    return None


def add_skill(src) -> dict:
    """把外部 .md 复制进技能目录，返回解析结果。同名覆盖。"""
    src = Path(src)
    s = parse_skill(src.read_text(encoding="utf-8"))
    dst = skills_dir() / f"{_safe_name(s['name'])}.md"
    shutil.copy2(src, dst)
    s["path"] = str(dst)
    return s


def remove_skill(name: str) -> bool:
    for p in skills_dir().glob("*.md"):
        try:
            s = parse_skill(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if s["name"] == name:
            p.unlink()
            return True
    return False


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w一-鿿-]+", "_", name).strip("_") or "skill"
