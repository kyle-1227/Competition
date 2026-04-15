from __future__ import annotations

import json

from ai_types import AiChatRequest, AiHistoryMessage, AiPageContext, AiSummaryRequest

SYSTEM_PROMPT = """你是本项目的数据答疑助手和总结生成器。
你的职责：
1. 只基于当前页面上下文、历史对话和工具返回结果回答，不得编造不存在的数据。
2. 如果页面快照不足以回答，可以调用当前页面允许的工具补充查询；不能调用与当前页面无关的工具。
3. 如果上下文仍然不足，必须明确说明“当前页面数据不足”。
4. 回答默认使用中文，语气专业、清晰，偏向业务汇报与数据分析。
5. 优先解释趋势、结构、异常点和业务含义，避免输出与当前页面无关的空泛内容。
6. 如果工具返回结果与页面快照冲突，以工具返回结果为准。"""

PAGE_FOCUS: dict[str, str] = {
    "greenFinance": "绿色金融综合指数页面，重点关注综合分、Top10、七维指标、下钻视角和县级 mock 数据。",
    "carbon": "碳排放底色页面，重点关注当前年份、Top10 省份、总量、均值和空间分布。",
    "energy": "碳排放强度预测页面，重点关注当前区域、滑块参数、历史序列、预测序列和最终预测结果。",
    "macro": "宏观经济页面，重点关注区域 GDP、碳排放序列、最新年份表现和变化趋势。",
}


def _compact_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _normalize_history(history: list[AiHistoryMessage]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in history[-12:]:
        content = item.content.strip()
        if not content:
            continue
        normalized.append({"role": item.role, "content": content})
    return normalized


def _page_context_to_text(page_context: AiPageContext) -> str:
    lines = [
        f"当前页面: {page_context.pageTitle}",
        f"页面标识: {page_context.page}",
        f"页面说明: {PAGE_FOCUS.get(page_context.page, '当前页面暂无额外说明。')}",
    ]
    if page_context.year is not None:
        lines.append(f"当前年份: {page_context.year}")
    if page_context.selectedProvince:
        lines.append(f"当前选中区域: {page_context.selectedProvince}")
    if page_context.drillProvince:
        lines.append(f"当前下钻省份: {page_context.drillProvince}")
    if page_context.drillCity:
        lines.append(f"当前下钻城市: {page_context.drillCity}")

    snapshot_text = _compact_json(page_context.snapshot) if page_context.snapshot else "{}"
    lines.append(f"页面快照(JSON): {snapshot_text}")
    return "\n".join(lines)


def build_chat_messages(payload: AiChatRequest) -> list[dict[str, str]]:
    context_text = _page_context_to_text(payload.pageContext)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"下面是当前页面的结构化上下文，请先理解再回答。\n{context_text}"},
    ]
    messages.extend(_normalize_history(payload.history))
    messages.append(
        {
            "role": "user",
            "content": (
                "请结合上面的当前页面上下文回答这个问题。"
                "如果上下文仍然不足，请明确指出不足，不要编造。\n"
                f"问题：{payload.question.strip()}"
            ),
        }
    )
    return messages


def build_summary_messages(payload: AiSummaryRequest) -> list[dict[str, str]]:
    context_text = _page_context_to_text(payload.pageContext)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"下面是当前页面的结构化上下文，请先理解再生成总结。\n{context_text}"},
    ]
    messages.extend(_normalize_history(payload.history))
    messages.append(
        {
            "role": "user",
            "content": (
                "请基于当前页面上下文生成 1 到 3 段中文总结。"
                "总结应突出核心结论、结构特征和业务含义；"
                "如果数据不足，请明确说明。"
            ),
        }
    )
    return messages
