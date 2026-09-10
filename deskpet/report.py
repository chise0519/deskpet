"""日报 Markdown 生成与保存（纯逻辑，无 Qt）。"""
from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path
from typing import Union

WEEKDAY_CN = "一二三四五六日"

Day = Union[date, datetime]


def _to_date(day: Day) -> date:
    return day.date() if isinstance(day, datetime) else day


def _hm(iso) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M")
    except ValueError:
        return ""


def build_report(day: Day, notes: list[dict], reminders: list[dict],
                 generated_at: datetime = None) -> str:
    """生成日报 Markdown。

    notes: 当天创建的速记（含 done/done_at/created_at）
    reminders: 当天实际触发过的提醒（含 last_notified_at）
    """
    day = _to_date(day)
    generated_at = generated_at or datetime.now()
    md: list[str] = [
        f"# 工作日报 {day.isoformat()}（周{WEEKDAY_CN[day.weekday()]}）",
        "",
    ]

    done = [n for n in notes if n.get("done")]
    undone = [n for n in notes if not n.get("done")]

    md += ["## ✅ 今日完成", ""]
    if done:
        for n in done:
            suffix = f"（完成于 {_hm(n.get('done_at'))}）" if n.get("done_at") else ""
            md.append(f"- [x] {n['content']}{suffix}")
    else:
        md.append("（无）")
    md.append("")

    md += ["## 🚧 未完成", ""]
    if undone:
        md += [f"- [ ] {n['content']}" for n in undone]
    else:
        md.append("（无）")
    md.append("")

    md += ["## ⏰ 提醒执行", ""]
    if reminders:
        md += [f"- {_hm(r.get('last_notified_at'))} {r['content']}" for r in reminders]
    else:
        md.append("（无）")
    md.append("")

    md += ["## 📝 随手记", ""]
    if notes:
        md += [f"- `{_hm(n['created_at'])}` {n['content']}" for n in notes]
    else:
        md.append("（无）")
    md.append("")

    md += ["---", f"*由 DeskPet 生成于 {generated_at:%Y-%m-%d %H:%M}*", ""]
    return "\n".join(md)


def save_report(content: str, day: Day, reports_dir) -> Path:
    """保存为 reports/YYYY-MM-DD.md；已存在则先备份为 .md.bak。"""
    day = _to_date(day)
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{day.isoformat()}.md"
    if path.exists():
        shutil.copy2(path, path.with_suffix(".md.bak"))
    path.write_text(content, encoding="utf-8")
    return path
