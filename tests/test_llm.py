"""llm 模块单测：用本地 mock server 验证 OpenAI 兼容调用链与错误处理。"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from deskpet import llm


class _Handler(BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *a):  # 静音
        pass

    def do_GET(self):
        if _Handler.mode == "models":
            resp = {"data": [{"id": "mock-a"}, {"id": "mock-b"}]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        if _Handler.mode == "ok":
            assert self.path == "/v1/chat/completions"
            assert self.headers.get("Authorization") == "Bearer sk-test"
            resp = {"choices": [{"message": {"content": "润色后的日报"}}]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())
        elif _Handler.mode == "http500":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error":"boom"}')
        elif _Handler.mode == "badjson":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not json")
        elif _Handler.mode == "models":
            resp = {"data": [{"id": "mock-a"}, {"id": "mock-b"}]}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())
        # 记录收到的 messages 供断言
        _Handler.last_body = body


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


def test_chat_complete_ok(server):
    _Handler.mode = "ok"
    out = llm.chat_complete(server, "sk-test", "m", [
        {"role": "user", "content": "hi"}], timeout=5)
    assert out == "润色后的日报"
    assert _Handler.last_body["model"] == "m"
    assert _Handler.last_body["messages"][0]["role"] == "user"


def test_http_error(server):
    _Handler.mode = "http500"
    with pytest.raises(llm.LLMError, match="500"):
        llm.chat_complete(server, "k", "m", [{"role": "user", "content": "x"}],
                          timeout=5)


def test_bad_json(server):
    _Handler.mode = "badjson"
    with pytest.raises(llm.LLMError, match="JSON"):
        llm.chat_complete(server, "k", "m", [{"role": "user", "content": "x"}],
                          timeout=5)


def test_polish_missing_key():
    with pytest.raises(llm.LLMError, match="API Key"):
        llm.polish_report("# 日报", {"llm_provider": "qwen",
                                     "llm_base_url": "", "llm_model": "",
                                     "llm_api_key": ""})


def test_polish_empty_content():
    with pytest.raises(llm.LLMError, match="为空"):
        llm.polish_report("   ", {"llm_provider": "qwen",
                                  "llm_base_url": "https://x.example/v1",
                                  "llm_model": "m", "llm_api_key": "k"})


def test_polish_ok_via_mock(server):
    _Handler.mode = "ok"
    out = llm.polish_report("# 日报\n- [x] 修 bug", {
        "llm_provider": "custom", "llm_base_url": server,
        "llm_model": "mock", "llm_api_key": "sk-test", "llm_timeout": 5})
    assert out == "润色后的日报"
    # system prompt 必须带上
    roles = [m["role"] for m in _Handler.last_body["messages"]]
    assert roles == ["system", "user"]


def test_local_endpoint_skips_key_check():
    """localhost 免 key：缺 key 不应报"未配置 API Key"，而是走到网络层报错。"""
    with pytest.raises(llm.LLMError) as ei:
        llm.polish_report("# 日报", {
            "llm_provider": "custom",
            "llm_base_url": "http://127.0.0.1:1/v1",
            "llm_model": "m", "llm_api_key": "", "llm_timeout": 2})
    assert "API Key" not in str(ei.value)
    assert "网络" in str(ei.value) or "超时" in str(ei.value)


# ---------------- test_connection 自检 ----------------

def test_conn_ok(server):
    _Handler.mode = "ok"
    ok, msg = llm.test_connection(server, "sk-test", "mock", timeout=5)
    assert ok is True
    assert "连接正常" in msg and "耗时" in msg


def test_conn_http_error(server):
    _Handler.mode = "http500"
    ok, msg = llm.test_connection(server, "k", "m", timeout=5)
    assert ok is False
    assert "500" in msg


def test_conn_missing_fields():
    assert llm.test_connection("", "k", "m")[0] is False
    assert llm.test_connection("http://x/v1", "k", "")[0] is False
    ok, msg = llm.test_connection("https://x.example/v1", "", "m")
    assert ok is False and "API Key" in msg


def test_conn_unreachable():
    ok, msg = llm.test_connection("http://127.0.0.1:1/v1", "", "m", timeout=2)
    assert ok is False
    assert "网络" in msg or "超时" in msg


# ---------------- list_models / discover / env_key_hint ----------------

def test_list_models(server):
    _Handler.mode = "models"
    ids = llm.list_models(server, "sk-test", timeout=5)
    assert ids == ["mock-a", "mock-b"]


def test_list_models_unreachable():
    with pytest.raises(llm.LLMError):
        llm.list_models("http://127.0.0.1:1/v1", timeout=1)


def test_discover_finds_mock_server(server):
    _Handler.mode = "models"
    # 本地四个端口大概率没服务；extra 里放 mock 必中
    found = llm.discover(extra=[("Mock", server, "sk-test")], timeout=1.5)
    srcs = [f["source"] for f in found]
    assert "Mock" in srcs
    entry = next(f for f in found if f["source"] == "Mock")
    assert entry["models"] == ["mock-a", "mock-b"]
    assert entry["base_url"] == server


def test_discover_empty_when_nothing():
    found = llm.discover(extra=[], timeout=0.5)
    # 真机上若恰好有本地服务则非空，只断言结构
    assert isinstance(found, list)
    for f in found:
        assert {"source", "base_url", "api_key", "models"} <= set(f)


def test_env_key_hint(monkeypatch):
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-env")
    assert llm.env_key_hint("qwen") == "sk-env"
    monkeypatch.delenv("DASHSCOPE_API_KEY")
    assert llm.env_key_hint("qwen") == ""
    assert llm.env_key_hint("nosuch") == ""
