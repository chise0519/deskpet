"""skills 模块单测：解析/列表/增删 + 润色时技能进 system prompt。"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from deskpet import config, llm, skills

SAMPLE = """---
name: daily-report
description: 将工作要点整理成简洁的中文工作日报。
---

# 日报整理

## 输出格式
M月D日日报
**今日工作进展**
1. **事项**：结果。（进度X%）
"""


@pytest.fixture()
def sdir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return skills.skills_dir()


def test_parse_frontmatter():
    s = skills.parse_skill(SAMPLE)
    assert s["name"] == "daily-report"
    assert "中文工作日报" in s["description"]
    assert s["body"].startswith("# 日报整理")
    assert "name:" not in s["body"]


def test_parse_no_frontmatter():
    s = skills.parse_skill("# 裸指令\n内容")
    assert s["name"] == "unnamed"
    assert s["body"].startswith("# 裸指令")


def test_add_list_get_remove(sdir):
    src = sdir.parent / "src.md"
    src.write_text(SAMPLE, encoding="utf-8")
    added = skills.add_skill(src)
    assert added["name"] == "daily-report"
    names = [s["name"] for s in skills.list_skills()]
    assert names == ["daily-report"]
    got = skills.get_skill("daily-report")
    assert got and "进度X%" in got["body"]
    assert skills.remove_skill("daily-report") is True
    assert skills.list_skills() == []
    assert skills.get_skill("daily-report") is None


def test_add_overwrite_same_name(sdir):
    src = sdir.parent / "a.md"
    src.write_text(SAMPLE, encoding="utf-8")
    skills.add_skill(src)
    src.write_text(SAMPLE.replace("进度X%", "进度Y%"), encoding="utf-8")
    skills.add_skill(src)
    assert len(skills.list_skills()) == 1
    assert "进度Y%" in skills.get_skill("daily-report")["body"]


def test_build_system_prompt():
    assert llm.build_system_prompt("") == llm.SYSTEM_PROMPT
    p = llm.build_system_prompt("技能正文")
    assert p.startswith("技能正文")
    assert "不得编造事实" in p


class _Echo(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        _Echo.body = json.loads(
            self.rfile.read(int(self.headers.get("Content-Length", 0))))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(
            {"choices": [{"message": {"content": "OK"}}]}).encode())


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Echo)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


def test_polish_sends_skill_as_system(server, sdir):
    src = sdir.parent / "src.md"
    src.write_text(SAMPLE, encoding="utf-8")
    skills.add_skill(src)
    cfg = {
        "llm_provider": "custom",
        "llm_profiles": {"custom": {"base_url": server, "model": "m",
                                    "api_key": "k"}},
        "polish_skill": "daily-report",
        "llm_timeout": 5,
    }
    out = llm.polish_report("# 日报", cfg)
    assert out == "OK"
    sysmsg = _Echo.body["messages"][0]
    assert sysmsg["role"] == "system"
    assert "# 日报整理" in sysmsg["content"]
    assert "不得编造事实" in sysmsg["content"]


def test_polish_unknown_skill_falls_back(server):
    cfg = {
        "llm_provider": "custom",
        "llm_profiles": {"custom": {"base_url": server, "model": "m",
                                    "api_key": "k"}},
        "polish_skill": "no-such-skill",
        "llm_timeout": 5,
    }
    llm.polish_report("# 日报", cfg)
    assert _Echo.body["messages"][0]["content"] == llm.SYSTEM_PROMPT
