from __future__ import annotations

import json

from ai_types import AiChatRequest, AiHistoryMessage, AiPageContext, AiSummaryRequest, AiTooltipRequest
from ai_knowledge import (
    get_page_knowledge_context,
    get_tooltip_knowledge_context as build_tooltip_knowledge_context,
    load_chat_prompt_template,
    load_summary_prompt_template,
    load_tooltip_prompt_template,
)

SYSTEM_PROMPT = """你是本项目的数据答疑助手和总结生成器。
你的职责：
1. 只基于当前页面上下文、历史对话和工具返回结果回答，不得编造不存在的数据。
2. 如果页面快照不足以回答，可以调用当前页面允许的工具补充查询；不能调用与当前页面无关的工具。
3. 只有在页面快照和可用工具查询后仍然不足时，才能明确说明“当前页面数据不足”。
4. 回答默认使用中文，语气专业、清晰，偏向业务汇报与数据分析。
5. 优先解释趋势、结构、异常点和业务含义，避免输出与当前页面无关的空泛内容。
6. 如果工具返回结果与页面快照冲突，以工具返回结果为准。"""

DEFAULT_CHAT_PROMPT_GUIDE = (
    "回答时优先基于当前页面上下文。若知识库提供了指标释义、单位、政策背景或模型结果卡片，"
    "可用于解释口径、含义和方法，但不能替代当前页面实时数据。"
)

DEFAULT_SUMMARY_PROMPT_GUIDE = (
    "总结时先归纳当前页面数据，再结合知识库补充指标释义、方法说明和政策背景。"
    "如果引用模型结果卡片，要保持谨慎，不要夸大因果。"
)

DEFAULT_TOOLTIP_PROMPT_GUIDE = (
    "你是一个数据分析师，请根据给定结构化数据生成一句不超过50字的简短分析。"
    "不要编造缺失信息，不要输出项目实现细节。"
)

CHAT_PROMPT_GUIDE = load_chat_prompt_template(DEFAULT_CHAT_PROMPT_GUIDE)
SUMMARY_PROMPT_GUIDE = load_summary_prompt_template(DEFAULT_SUMMARY_PROMPT_GUIDE)
TOOLTIP_SYSTEM_PROMPT_PLACEHOLDER = load_tooltip_prompt_template(DEFAULT_TOOLTIP_PROMPT_GUIDE)

PAGE_FOCUS: dict[str, str] = {
    "greenFinance": "绿色金融综合指数页面，重点关注综合分、Top10、七维指标、下钻视角和县级 mock 数据。",
    "carbon": "碳排放底色页面，重点关注当前年份、Top10 省份、总量、均值和空间分布。",
    "energy": "碳排放强度预测页面，重点关注当前层级、省市选择、三情景结果、自定义参数推演、对比线和最终预测结果。",
    "macro": "宏观经济页面，重点关注区域 GDP、碳排放序列、最新年份表现和变化趋势。",
}

GREEN_FINANCE_RELATION_GUIDE = (
    "绿色金融页补充规则：\n"
    "1. 如果用户询问绿色金融与 GDP、碳排放、经济发展、协同或关联分析，优先使用当前页面快照中的省级/城市级指标。\n"
    "2. 若当前页面快照不足以支撑关联分析，必须先调用绿色金融页面工具补查 GDP 与碳排放字段，再判断是否数据不足。\n"
    "3. 如果用户询问历史趋势、变化轨迹、近年变化或长期关系，优先调用绿色金融页的省级/城市历史工具。\n"
    "4. 如果用户询问省际对比，优先调用指定年份的省级工具；如果用户询问城市对比，优先调用当前下钻省份的城市工具。\n"
    "5. 省级视角优先围绕当前选中省份分析；下钻视角优先围绕当前下钻省份的城市样本分析。\n"
    "6. 只有在工具结果明确缺失对应字段时，才能说明当前页面数据不足。"
)

CARBON_ANALYSIS_GUIDE = (
    "碳排放页补充规则：\n"
    "1. 当前页面可能处于碳排放地图或 GDP 地图模式，回答时优先参考页面快照中的 mapMetric；若用户明确指定指标，以用户问题为准。\n"
    "2. 如果用户询问历史趋势、变化轨迹、近年变化或长期关系，优先调用碳排放页的省级/城市历史工具。\n"
    "3. 如果用户询问省际对比，优先调用指定年份的省级工具；如果用户询问城市对比，优先调用当前下钻省份的城市工具。\n"
    "4. 如果当前页面快照不足以支撑趋势或对比分析，必须先使用当前页工具补查，再判断是否数据不足。"
)

ENERGY_PREDICTION_GUIDE = (
    "预测页补充规则：\n"
    "1. 必须严格区分历史观测与模型推演：2000-2024 是历史观测，2025-2027 是模型推演，不得写成未来真实已发生结果。\n"
    "2. 如果当前页面处于保守/基准/乐观三情景，回答时优先引用离线情景结果；如果当前页面处于自定义模式，回答时优先引用当前滑块参数、参数贡献估算和页面对比线。\n"
    "3. 如果用户询问为什么预测上升或下降，优先引用 compareSummary、sourceMode 和 contributionBreakdown；如果上下文不足，必须先调用预测页工具补查。\n"
    "4. 如果工具结果里没有 R²、MAE、RMSE，就不能编造模型评价指标；可以说明本页当前未展示正式精度指标。\n"
    "5. 情景区间只能表述为情景区间，不得表述为统计置信区间。"
)


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


def _build_page_specific_guide(page_context: AiPageContext) -> str:
    if page_context.page == "greenFinance":
        return GREEN_FINANCE_RELATION_GUIDE
    if page_context.page == "carbon":
        return CARBON_ANALYSIS_GUIDE
    if page_context.page == "energy":
        return ENERGY_PREDICTION_GUIDE
    return ""


def build_chat_messages(payload: AiChatRequest) -> list[dict[str, str]]:
    context_text = _page_context_to_text(payload.pageContext)
    knowledge_text = get_page_knowledge_context(payload.pageContext, include_results=True, indicator_limit=6).strip()
    page_guide = _build_page_specific_guide(payload.pageContext).strip()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n补充规则:\n{CHAT_PROMPT_GUIDE}"},
        {"role": "user", "content": f"下面是当前页面的结构化上下文，请先理解再回答。\n{context_text}"},
    ]
    if page_guide:
        messages.append({"role": "user", "content": f"当前页面专项规则：\n{page_guide}"})
    if knowledge_text:
        messages.append(
            {
                "role": "user",
                "content": (
                    "下面是项目知识库中与当前页面最相关的条目，可用于解释指标含义、单位、政策背景和模型结论。"
                    "这些知识不能替代当前页面实时数据。\n"
                    f"{knowledge_text}"
                ),
            }
        )
    messages.extend(_normalize_history(payload.history))
    messages.append(
        {
            "role": "user",
            "content": (
                "请结合上面的当前页面上下文回答这个问题。"
                "如果问题涉及关联分析、历史趋势、省际对比或城市对比，请优先使用当前页面已有字段或当前页工具补查后再判断是否数据不足。"
                "如果上下文仍然不足，请明确指出不足，不要编造。\n"
                f"问题：{payload.question.strip()}"
            ),
        }
    )
    return messages


def build_summary_messages(payload: AiSummaryRequest) -> list[dict[str, str]]:
    context_text = _page_context_to_text(payload.pageContext)
    knowledge_text = get_page_knowledge_context(payload.pageContext, include_results=True, indicator_limit=8).strip()
    page_guide = _build_page_specific_guide(payload.pageContext).strip()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\n补充规则:\n{SUMMARY_PROMPT_GUIDE}"},
        {"role": "user", "content": f"下面是当前页面的结构化上下文，请先理解再生成总结。\n{context_text}"},
    ]
    if page_guide:
        messages.append({"role": "user", "content": f"当前页面专项规则：\n{page_guide}"})
    if knowledge_text:
        messages.append(
            {
                "role": "user",
                "content": (
                    "下面是项目知识库中与当前页面最相关的条目，可用于解释指标、单位、政策背景与模型结果。"
                    "引用时请明确区分知识库结论和页面实时数据。\n"
                    f"{knowledge_text}"
                ),
            }
        )
    messages.extend(_normalize_history(payload.history))
    messages.append(
        {
            "role": "user",
            "content": (
                "请基于当前页面上下文生成 1 到 3 段中文总结。"
                "总结应突出核心结论、结构特征和业务含义；"
                "如果涉及绿色金融与经济发展、GDP、碳排放、历史趋势或对比关系，请优先使用当前页面指标或工具查询结果组织分析；"
                "如果数据不足，请明确说明。"
            ),
        }
    )
    return messages


def _tooltip_context_to_text(payload: AiTooltipRequest) -> str:
    lines = [
        f"模块名称: {payload.moduleName}",
        f"Tooltip 场景: {payload.tooltipScope}",
        f"区域名称: {payload.regionName}",
    ]
    if payload.year is not None:
        lines.append(f"年份: {payload.year}")
    lines.append(f"结构化数据(JSON): {_compact_json(payload.dataPayload or {})}")
    return "\n".join(lines)


def get_tooltip_knowledge_context(payload: AiTooltipRequest) -> str:
    return build_tooltip_knowledge_context(payload)


def build_tooltip_messages(payload: AiTooltipRequest) -> list[dict[str, str]]:
    context_text = _tooltip_context_to_text(payload)
    knowledge_text = get_tooltip_knowledge_context(payload).strip()

    user_prompt = (
        "下面是一个可视化 Tooltip 的结构化数据，请生成一句简短中文分析。"
        "要求：\n"
        "1. 限制在 50 字以内。\n"
        "2. 只分析给定数据，不要编造。\n"
        "3. 优先概括趋势、相对位置、结构特征或异常点。\n"
        "4. 如果信息不足，直接回答“当前 tooltip 数据不足”。\n"
        f"{context_text}"
    )
    if knowledge_text:
        user_prompt += f"\n补充业务知识:\n{knowledge_text}"

    return [
        {"role": "system", "content": TOOLTIP_SYSTEM_PROMPT_PLACEHOLDER},
        {"role": "user", "content": user_prompt},
    ]
