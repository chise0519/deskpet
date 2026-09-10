"""日报润色：调用 LLM（Qwen / GLM / 任意 OpenAI 兼容端点）。

纯逻辑层，GUI 只负责接线。网络用标准库 urllib，不引第三方依赖。
API key 只存本地 config.json，绝不写日志。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config

# 本地常见 OpenAI 兼容服务，自动扫描用
LOCAL_ENDPOINTS = [
    ("Ollama", "http://127.0.0.1:11434/v1"),
    ("llama-server", "http://127.0.0.1:8080/v1"),
    ("LM Studio", "http://127.0.0.1:1234/v1"),
    ("vLLM", "http://127.0.0.1:8000/v1"),
]

# 环境变量里的 Key 自动带入（用户自己机器上的，不写日志）
ENV_KEY_HINTS = {
    "qwen": ["DASHSCOPE_API_KEY"],
    "glm": ["ZHIPUAI_API_KEY", "GLM_API_KEY"],
    "custom": ["OPENAI_API_KEY"],
}

PROVIDERS = {
    "qwen": {
        "label": "Qwen 通义千问 (DashScope)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "glm": {
        "label": "GLM 智谱 (BigModel)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "custom": {
        "label": "自定义 (OpenAI 兼容，含本地 Ollama/vLLM)",
        "base_url": "",
        "model": "",
    },
}

SYSTEM_PROMPT = (
    "你是工作日报润色助手。要求：\n"
    "1. 只优化措辞、语气与排版，不得编造事实、不得新增或删除事项；\n"
    "2. 保留 Markdown 结构（标题、列表、复选框 - [ ] / - [x]）；\n"
    "3. 已完成事项写得简洁专业，未完成事项保留原意并可补一句后续计划方向（不虚构细节）；\n"
    "4. 直接输出润色后的全文，不要任何解释或前后缀。"
)


class LLMError(Exception):
    """配置缺失 / 网络失败 / 模型返回异常，消息可直接展示给用户。"""


def chat_complete(base_url: str, api_key: str, model: str,
                  messages: list[dict], timeout: int = 60,
                  temperature: float = 0.4) -> str:
    """OpenAI 兼容 /chat/completions 调用，返回助手文本。"""
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001
            pass
        raise LLMError(f"模型接口返回 HTTP {e.code}：{detail}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"网络不通或地址错误：{e.reason}") from e
    except TimeoutError as e:
        raise LLMError(f"调用超时（{timeout}s），可稍后重试") from e
    except json.JSONDecodeError as e:
        raise LLMError("模型返回不是合法 JSON") from e
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as e:
        raise LLMError(f"模型返回结构异常：{str(payload)[:200]}") from e


def env_key_hint(provider: str) -> str:
    """从环境变量取该服务商的 Key（有则返回，无则空串）。"""
    for name in ENV_KEY_HINTS.get(provider, []):
        v = os.environ.get(name, "").strip()
        if v:
            return v
    return ""


def list_models(base_url: str, api_key: str = "", timeout: int = 5) -> list[str]:
    """GET {base}/models，返回模型 id 列表。失败抛 LLMError。"""
    url = base_url.rstrip("/") + "/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"模型列表接口 HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"网络不通或地址错误：{e.reason}") from e
    except TimeoutError as e:
        raise LLMError(f"获取模型列表超时（{timeout}s）") from e
    except json.JSONDecodeError as e:
        raise LLMError("模型列表返回不是合法 JSON") from e
    if isinstance(payload, dict):
        data = payload.get("data") or payload.get("models") or []
    elif isinstance(payload, list):
        data = payload
    else:
        data = []
    ids = [d.get("id") if isinstance(d, dict) else str(d) for d in data]
    return [i for i in ids if i]


def discover(extra=None, timeout: float = 1.5) -> list[dict]:
    """自动发现可用模型服务。

    扫描 LOCAL_ENDPOINTS（本地免 Key）+ extra=[(source, base_url, api_key)]
    （如已填 Key 的云端）。并发探测 /models，返回
    [{"source","base_url","api_key","models":[...]}]，探不到就跳过。
    """
    targets = [(name, base, "") for name, base in LOCAL_ENDPOINTS]
    if extra:
        targets += [(s, b, k) for s, b, k in extra if b]
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(list_models, b, k, timeout): (s, b, k)
                for s, b, k in targets}
        for fut in as_completed(futs):
            src, base, key = futs[fut]
            try:
                models = fut.result()
            except LLMError:
                continue
            if models:
                out.append({"source": src, "base_url": base,
                            "api_key": key, "models": models})
    out.sort(key=lambda e: e["source"])
    return out


def test_connection(base_url: str, api_key: str, model: str,
                    timeout: int = 15) -> tuple[bool, str]:
    """连接自检：发一条最小请求，返回 (是否成功, 可读消息)。

    用表单当前值而非已保存配置，改完不用先保存就能测。
    """
    import time as _time

    base_url = (base_url or "").strip()
    model = (model or "").strip()
    if not base_url:
        return False, "未填 Base URL"
    if not model:
        return False, "未填模型名"
    if (not (api_key or "").strip()
            and "localhost" not in base_url and "127.0.0.1" not in base_url):
        return False, "未填 API Key（本地服务可留空）"
    t0 = _time.monotonic()
    try:
        out = chat_complete(
            base_url, api_key, model,
            [{"role": "user", "content": "请只回复两个字：收到"}],
            timeout=timeout, temperature=0.0)
    except LLMError as e:
        return False, str(e)
    dt = _time.monotonic() - t0
    preview = (out or "").replace("\n", " ").strip()[:40]
    return True, f"连接正常 · 耗时 {dt:.1f}s · 模型回复：{preview or '（空）'}"


def polish_report(markdown: str, cfg: dict | None = None) -> str:
    """一键润色入口：读设置 → 调模型 → 返回润色后全文。"""
    cfg = cfg if cfg is not None else config.load_config()
    provider = cfg.get("llm_provider", "qwen")
    prof = config.get_llm_profile(cfg, provider)
    base_url = prof["base_url"].strip()
    model = prof["model"].strip()
    api_key = prof["api_key"].strip()
    if not base_url or not model:
        preset = PROVIDERS.get(provider, {})
        base_url = base_url or preset.get("base_url", "")
        model = model or preset.get("model", "")
    if not base_url or not model:
        raise LLMError("未配置模型：请到 设置 → AI 润色 填写 Base URL 与模型名")
    if not api_key and "localhost" not in base_url and "127.0.0.1" not in base_url:
        raise LLMError("未配置 API Key：请到 设置 → AI 润色 填写（本地服务可留空）")
    if not markdown.strip():
        raise LLMError("日报内容为空，没什么可润色的")
    timeout = int(cfg.get("llm_timeout", 60))
    return chat_complete(
        base_url, api_key, model,
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": markdown}],
        timeout=timeout,
    )
