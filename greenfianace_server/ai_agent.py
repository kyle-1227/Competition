from __future__ import annotations

import json
from typing import Any, Iterator, Literal

from ai_context import build_chat_messages, build_summary_messages
from ai_service import AiServiceError, request_deepseek_response, stream_deepseek_completion
from ai_tools import AiToolError, build_page_tools, execute_page_tool, summarize_tool_result
from ai_types import AiChatRequest, AiPageContext, AiSummaryRequest

AgentKind = Literal["chat", "summary"]

TOOL_STATUS_LABELS: dict[str, str] = {
    "get_green_finance_province_data": "正在查询全国绿色金融省级数据…",
    "get_green_finance_city_data": "正在查询当前省份的城市层级数据…",
    "get_carbon_province_data": "正在查询全国碳排放省级数据…",
    "get_energy_prediction_data": "正在查询预测历史序列与模型系数…",
    "get_macro_series_data": "正在查询宏观时间序列…",
    "get_macro_stats_data": "正在查询宏观描述性统计…",
}


def _temperature(kind: AgentKind) -> float:
    return 0.4 if kind == "summary" else 0.3


def _build_base_messages(kind: AgentKind, payload: AiChatRequest | AiSummaryRequest) -> list[dict[str, Any]]:
    if kind == "summary":
        return build_summary_messages(payload)  # type: ignore[arg-type]
    return build_chat_messages(payload)  # type: ignore[arg-type]


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _serialize_tool_content(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))


def _assistant_message_for_history(message: dict[str, Any]) -> dict[str, Any]:
    formatted: dict[str, Any] = {
        "role": "assistant",
        "content": message.get("content") or "",
    }
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        formatted["tool_calls"] = tool_calls
    return formatted


def _iter_simulated_chunks(text: str, chunk_size: int = 4) -> Iterator[str]:
    if chunk_size <= 0:
        chunk_size = 1
    for index in range(0, len(text), chunk_size):
        yield text[index:index + chunk_size]


def _stream_final_answer(messages: list[dict[str, Any]], temperature: float) -> Iterator[dict[str, str]]:
    yielded = False
    for chunk in stream_deepseek_completion(messages, temperature=temperature):
        yielded = True
        yield chunk
    if not yielded:
        raise AiServiceError("AI 未返回最终回答内容")


def _build_start_payload(kind: AgentKind, page_context: AiPageContext) -> dict[str, Any]:
    return {
        "kind": kind,
        "page": page_context.page,
        "pageTitle": page_context.pageTitle,
    }


def stream_agent_events(kind: AgentKind, payload: AiChatRequest | AiSummaryRequest) -> Iterator[str]:
    page_context = payload.pageContext
    messages = _build_base_messages(kind, payload)
    temperature = _temperature(kind)
    tools = build_page_tools(page_context)

    yield _sse_event("start", _build_start_payload(kind, page_context))

    try:
        if not tools:
            final_model: str | None = None
            for chunk in _stream_final_answer(messages, temperature):
                final_model = chunk.get("model") or final_model
                content = chunk.get("content") or ""
                if content:
                    yield _sse_event("delta", {"content": content, "model": final_model})
            yield _sse_event("done", {"kind": kind, "model": final_model})
            return

        first_pass = request_deepseek_response(messages, temperature=temperature, tools=tools, tool_choice="auto")
        model = str(first_pass.get("model") or "")
        assistant_message = first_pass.get("message") or {}
        tool_calls = assistant_message.get("tool_calls") or []
        content = str(assistant_message.get("content") or "")

        if tool_calls:
            messages.append(_assistant_message_for_history(assistant_message))
            for index, tool_call in enumerate(tool_calls, start=1):
                function = tool_call.get("function") or {}
                tool_name = str(function.get("name") or f"tool_{index}")
                arguments_json = str(function.get("arguments") or "{}")
                tool_call_id = str(tool_call.get("id") or f"tool-call-{index}")

                yield _sse_event(
                    "tool_start",
                    {
                        "name": tool_name,
                        "message": TOOL_STATUS_LABELS.get(tool_name, "正在查询当前页数据…"),
                    },
                )

                try:
                    tool_result = execute_page_tool(page_context, tool_name, arguments_json)
                    tool_ok = True
                    tool_summary = summarize_tool_result(tool_name, tool_result)
                except AiToolError as exc:
                    tool_result = {"error": str(exc)}
                    tool_ok = False
                    tool_summary = str(exc)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": _serialize_tool_content(tool_result),
                    }
                )
                yield _sse_event(
                    "tool_result",
                    {
                        "name": tool_name,
                        "summary": tool_summary,
                        "ok": tool_ok,
                    },
                )

            final_model = model or None
            for chunk in _stream_final_answer(messages, temperature):
                final_model = chunk.get("model") or final_model
                text = chunk.get("content") or ""
                if text:
                    yield _sse_event("delta", {"content": text, "model": final_model})
            yield _sse_event("done", {"kind": kind, "model": final_model})
            return

        direct_content = content.strip()
        if direct_content:
            for piece in _iter_simulated_chunks(direct_content):
                yield _sse_event("delta", {"content": piece, "model": model or None})
            yield _sse_event("done", {"kind": kind, "model": model or None})
            return

        final_model = model or None
        for chunk in _stream_final_answer(messages, temperature):
            final_model = chunk.get("model") or final_model
            text = chunk.get("content") or ""
            if text:
                yield _sse_event("delta", {"content": text, "model": final_model})
        yield _sse_event("done", {"kind": kind, "model": final_model})
    except AiServiceError as exc:
        yield _sse_event("error", {"message": str(exc)})
    except Exception as exc:  # pragma: no cover - runtime protection
        yield _sse_event("error", {"message": f"AI 处理失败: {exc}"})


def stream_chat_agent_events(payload: AiChatRequest) -> Iterator[str]:
    return stream_agent_events("chat", payload)



def stream_summary_agent_events(payload: AiSummaryRequest) -> Iterator[str]:
    return stream_agent_events("summary", payload)
