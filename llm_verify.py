"""LLM 翻译对齐校验（OpenAI 兼容 Chat Completions API）。

用于在跨源翻译合并后，简单核对翻译行是否与原文歌词对应。
配置通过项目根目录的 .env 文件（见 .env.example），仅读取该文件、不读系统环境变量：
  OPENAI_API_KEY   必填，留空则本功能不可用
  OPENAI_BASE_URL  可选，默认 https://api.openai.com/v1（可换成任意 OpenAI 兼容端点）
  LYRICGETER_LLM_MODEL  可选，默认 gpt-4o-mini

功能定位为「可选的简单验证」：由用户在交互菜单中主动触发，不自动调用。
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

try:
    from dotenv import dotenv_values
except ImportError:
    dotenv_values = None  # type: ignore[assignment]

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
# 避免单次请求 token 过多，截断发送的配对数
_MAX_PAIRS = 60
# LLM 调用本身耗时受模型影响，给出足够长的超时
_REQUEST_TIMEOUT = 120.0

_SYSTEM_PROMPT = (
    "你是歌词翻译对齐校验助手。你会收到一组「原文→翻译」配对，"
    "请判断每条翻译是否与对应原文语义相符。"
    "只指出明显不对应（含义无关、方向相反、明显是相邻行错位）的对，"
    "其余不要点评。无错位时只输出 []。"
)

_USER_PREFIX = (
    "以下是逐行配对的歌词（原文带时间戳，翻译紧跟其后）。"
    "请检查翻译与原文的对应关系，返回一个 JSON 数组，"
    '元素为 {"line": 行号(int), "reason": "一句话理由"}，'
    "无错位则返回 []。不要输出 JSON 以外的内容。\n\n"
)


def _load_env_config() -> dict[str, str]:
    """读取项目根目录下的 .env 文件为字典；不读取系统环境变量。"""
    if dotenv_values is None:
        return {}
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return {}
    return {k: v for k, v in dotenv_values(env_path).items() if v is not None}


def llm_available() -> bool:
    """是否配置了 API Key。"""
    return bool(_load_env_config().get("OPENAI_API_KEY", "").strip())


def _config() -> tuple[str, str, str]:
    cfg = _load_env_config()
    api_key = cfg.get("OPENAI_API_KEY", "").strip()
    base_url = (cfg.get("OPENAI_BASE_URL") or _DEFAULT_BASE_URL).rstrip("/")
    model = cfg.get("LYRICGETER_LLM_MODEL") or _DEFAULT_MODEL
    return api_key, base_url, model


def _parse_chat_response(resp: httpx.Response) -> str:
    """从 OpenAI 兼容响应中提取 message.content，容错空体和 SSE 流式。"""
    body = resp.text or ""

    # 路径 1：标准 JSON 响应
    if body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败：{e}\n响应前 500 字节：{body[:500]!r}")
        if not isinstance(data, dict) or "choices" not in data:
            raise ValueError(f"响应结构异常，前 500 字节：{body[:500]!r}")
        choice = data["choices"][0]
        msg = choice.get("message") or {}
        content = msg.get("content")
        if content is None and choice.get("text") is not None:
            content = choice["text"]  # 一些旧版 completions 接口用 text 字段
        if not content:
            raise ValueError(f"响应 message.content 为空，前 500 字节：{body[:500]!r}")
        return content.strip()

    # 路径 2：SSE 流式响应（某些代理默认走流式）
    if body.lstrip().startswith("data:"):
        chunks: list[str] = []
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]" or not payload:
                continue
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for choice in obj.get("choices", []):
                delta = choice.get("delta") or {}
                piece = delta.get("content") or ""
                if piece:
                    chunks.append(piece)
        if chunks:
            return "".join(chunks).strip()
        raise ValueError("检测到 SSE 流式但未能拼出内容，可能为空流。")

    # 路径 3：什么都不是
    raise ValueError(
        f"响应非 JSON 也非 SSE（HTTP {resp.status_code}），\n响应前 500 字节：{body[:500]!r}"
    )


def _format_request_error(e: Exception, base_url: str, model: str) -> str:
    """把网络层异常分类成人类可读的提示。"""
    if isinstance(e, httpx.ConnectError):
        return (
            "[red]LLM 连接失败：无法连接到服务端。[/]\n"
            f"[dim]请求地址：{base_url}/chat/completions[/]\n"
            f"[dim]原始错误：{e}[/]\n"
            "[yellow]请检查 .env 的 OPENAI_BASE_URL 是否正确、网络/代理是否可达。[/]"
        )
    if isinstance(e, (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout)):
        return (
            f"[red]LLM 请求超时（{model}）。[/]\n"
            "[dim]模型推理耗时较长，可换更快的 LYRICGETER_LLM_MODEL 重试。[/]\n"
            f"[dim]原始错误：{e}[/]"
        )
    if isinstance(e, ValueError):  # 由 _parse_chat_response 抛出
        return f"[red]LLM 响应解析失败：[/]\n[dim]{e}[/]"
    return f"[red]LLM 请求异常：{type(e).__name__}: {e}[/]"


def _extract_pairs(spl: str) -> list[tuple[str, str]]:
    """把 SPL 拆成 (原文行, 翻译行) 配对。

    规则：带时间戳的行是原文；其后紧跟的无时间戳非空行视为该原文的翻译。
    """
    pairs: list[tuple[str, str]] = []
    lines = [ln.strip() for ln in spl.splitlines() if ln.strip()]

    def _has_stamp(line: str) -> bool:
        # 复用 ui 的判定，避免循环导入
        return line.lstrip().startswith("[")

    i = 0
    while i < len(lines):
        if _has_stamp(lines[i]):
            main = lines[i]
            translation = ""
            if i + 1 < len(lines) and not _has_stamp(lines[i + 1]):
                translation = lines[i + 1]
                i += 2
            else:
                i += 1
            pairs.append((main, translation))
        else:
            i += 1  # 没有主歌词的游离翻译，跳过
    return pairs


def verify_translation_alignment(spl: str) -> str:
    """校验合并后 SPL 的翻译对齐，返回面向用户的结论文本。"""
    api_key, base_url, model = _config()
    if not api_key:
        return (
            "[yellow]未配置 LLM。[/]"
            "\n复制 .env.example 为 .env 并填入 OPENAI_API_KEY 启用本功能；"
            "可选配置 OPENAI_BASE_URL、LYRICGETER_LLM_MODEL。"
        )

    pairs = _extract_pairs(spl)
    has_translation = any(trans for _, trans in pairs)
    if not has_translation:
        return "[dim]当前歌词没有翻译行，无需校验。[/]"

    truncated = len(pairs) > _MAX_PAIRS
    shown = pairs[:_MAX_PAIRS]

    body_lines = []
    for idx, (main, trans) in enumerate(shown, 1):
        body_lines.append(f"{idx}. 原文: {main}")
        body_lines.append(f"   翻译: {trans}" if trans else "   翻译: （无）")
    if truncated:
        body_lines.append(f"（共 {len(pairs)} 对，已截断显示前 {_MAX_PAIRS} 对）")
    body = "\n".join(body_lines)

    payload = {
        "model": model,
        "stream": False,  # 显式声明非流式，避免代理默认 SSE
        "temperature": 0,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_PREFIX + body},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
            resp = client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
        if resp.status_code != 200:
            return (
                f"[red]LLM 请求失败 (HTTP {resp.status_code})[/]\n"
                f"[dim]{resp.text[:500]}[/]"
            )
        content = _parse_chat_response(resp)
    except Exception as e:
        return _format_request_error(e, base_url, model)

    return _format_verdict(content, len(pairs), truncated)


def _format_verdict(content: str, total_pairs: int, truncated: bool) -> str:
    """把 LLM 返回的 JSON 数组渲染成用户可读文本。"""
    reasoning = ""
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # 模型偶尔会包 JSON 在 ``` 里或加文字，容错提取
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                reasoning = content
                parsed = None
        else:
            reasoning = content
            parsed = None

    if not isinstance(parsed, list):
        return (
            "[yellow]LLM 返回无法解析为 JSON，原文如下：[/]\n"
            f"[dim]{content}[/]"
        )

    if not parsed:
        note = f"（已检查 {total_pairs} 对翻译）"
        if truncated:
            note = f"（已检查前 {_MAX_PAIRS} 对，共 {total_pairs} 对）"
        return f"[green]✓ 翻译对齐通过[/][dim] {note}[/]"

    out = [f"[yellow]发现 {len(parsed)} 处疑似错位：[/]\n"]
    for item in parsed[: _MAX_PAIRS]:
        if isinstance(item, dict):
            line = item.get("line", "?")
            reason = item.get("reason", "").strip()
            out.append(f"  · 第 {line} 行{'：' + reason if reason else ''}")
    if truncated:
        out.append(f"\n[dim]（仅检查了前 {_MAX_PAIRS} 对，共 {total_pairs} 对）[/]")
    if reasoning:
        out.append(f"\n[dim]补充说明：{reasoning}[/]")
    return "\n".join(out)
