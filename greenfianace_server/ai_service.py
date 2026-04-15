from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterator

import httpx


class AiServiceError(RuntimeError):
    pass


@dataclass(slots=True)
class DeepSeekConfig:
    api_key: str
    base_url: str
    model: str
    timeout: float


def load_deepseek_config() -> DeepSeekConfig:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise AiServiceError("DeepSeek API Key 未配置，请先在 greenfianace_server/.env 中设置 DEEPSEEK_API_KEY")

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com"
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"

    timeout_raw = os.getenv("DEEPSEEK_TIMEOUT", "60").strip() or "60"
    try:
        timeout = float(timeout_raw)
    except ValueError as exc:
        raise AiServiceError(f"DEEPSEEK_TIMEOUT 配置无效: {timeout_raw}") from exc

    return DeepSeekConfig(
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        model=model,
        timeout=timeout,
    )


def _build_headers(config: DeepSeekConfig) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }


def _build_payload(
    config: DeepSeekConfig,
    messages: list[dict[str, Any]],
    temperature: float,
    stream: bool,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice or "auto"
    return payload


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 401:
        raise AiServiceError("DeepSeek 认证失败，请检查 DEEPSEEK_API_KEY 是否正确")
    if response.status_code >= 400:
        detail = response.text.strip()
        raise AiServiceError(f"DeepSeek 上游返回异常({response.status_code}): {detail or '无详细信息'}")


def _normalize_assistant_message(message: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "role": "assistant",
        "content": message.get("content") or "",
    }
    tool_calls = message.get("tool_calls")
    if isinstance(tool_calls, list) and tool_calls:
        normalized["tool_calls"] = tool_calls
    return normalized


def request_deepseek_response(
    messages: list[dict[str, Any]],
    temperature: float = 0.3,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = load_deepseek_config()
    payload = _build_payload(config, messages, temperature, stream=False, tools=tools, tool_choice=tool_choice)
    headers = _build_headers(config)
    url = f"{config.base_url}/chat/completions"

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=config.timeout)
    except httpx.TimeoutException as exc:
        raise AiServiceError("DeepSeek 请求超时，请稍后重试") from exc
    except httpx.HTTPError as exc:
        raise AiServiceError(f"DeepSeek 请求失败: {exc}") from exc

    _raise_for_status(response)

    try:
        data: dict[str, Any] = response.json()
    except ValueError as exc:
        raise AiServiceError("DeepSeek 返回了无法解析的 JSON") from exc

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AiServiceError("DeepSeek 返回结果为空")

    first = choices[0] or {}
    message = first.get("message") or {}
    if not isinstance(message, dict):
        raise AiServiceError("DeepSeek 返回的消息格式无效")

    return {
        "message": _normalize_assistant_message(message),
        "model": str(data.get("model") or config.model),
        "finish_reason": first.get("finish_reason"),
    }


def request_deepseek_completion(messages: list[dict[str, Any]], temperature: float = 0.3) -> dict[str, str]:
    result = request_deepseek_response(messages, temperature=temperature)
    content = str(result["message"].get("content") or "").strip()
    if not content:
        raise AiServiceError("DeepSeek 返回内容为空")
    return {"content": content, "model": str(result["model"])}


def stream_deepseek_completion(messages: list[dict[str, Any]], temperature: float = 0.3) -> Iterator[dict[str, str]]:
    config = load_deepseek_config()
    payload = _build_payload(config, messages, temperature, stream=True)
    headers = _build_headers(config)
    url = f"{config.base_url}/chat/completions"
    model = config.model

    try:
        with httpx.Client(timeout=config.timeout) as client:
            with client.stream("POST", url, json=payload, headers=headers) as response:
                _raise_for_status(response)
                for raw_line in response.iter_lines():
                    line = (raw_line or "").strip()
                    if not line or not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        break

                    try:
                        chunk: dict[str, Any] = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    model = str(chunk.get("model") or model)
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue

                    delta = (choices[0] or {}).get("delta") or {}
                    content = str(delta.get("content") or "")
                    if content:
                        yield {"content": content, "model": model}
    except httpx.TimeoutException as exc:
        raise AiServiceError("DeepSeek 流式请求超时，请稍后重试") from exc
    except httpx.HTTPError as exc:
        raise AiServiceError(f"DeepSeek 流式请求失败: {exc}") from exc
