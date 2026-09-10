from datetime import date

from deskpet import report

DAY = date(2026, 9, 9)  # 周三

NOTES = [
    {"id": 1, "content": "写周报", "created_at": "2026-09-09T09:10:00",
     "done": 1, "done_at": "2026-09-09T10:20:00"},
    {"id": 2, "content": "修登录 bug", "created_at": "2026-09-09T11:00:00",
     "done": 0, "done_at": None},
]
REMS = [
    {"id": 1, "content": "站会", "last_notified_at": "2026-09-09T09:30:00"},
]


def test_build_report_sections():
    md = report.build_report(DAY, NOTES, REMS)
    assert "# 工作日报 2026-09-09（周三）" in md
    assert "- [x] 写周报（完成于 10:20）" in md
    assert "- [ ] 修登录 bug" in md
    assert "- 09:30 站会" in md
    assert "`09:10` 写周报" in md
    assert "`11:00` 修登录 bug" in md


def test_build_report_empty():
    md = report.build_report(DAY, [], [])
    assert md.count("（无）") == 4


def test_save_report_and_backup(tmp_path):
    p = report.save_report("v1", DAY, tmp_path)
    assert p.name == "2026-09-09.md"
    assert p.read_text(encoding="utf-8") == "v1"

    p2 = report.save_report("v2", DAY, tmp_path)
    assert p2.read_text(encoding="utf-8") == "v2"
    bak = tmp_path / "2026-09-09.md.bak"
    assert bak.exists() and bak.read_text(encoding="utf-8") == "v1"
