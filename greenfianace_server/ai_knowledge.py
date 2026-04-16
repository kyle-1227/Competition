from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
KNOWLEDGE_ROOT = ROOT / "knowledge"
INDICATOR_DIR = KNOWLEDGE_ROOT / "01_indicator_dictionary"
PAGE_GUIDANCE_DIR = KNOWLEDGE_ROOT / "02_page_guidance"
RESULT_DIR = KNOWLEDGE_ROOT / "04_result_cards"
PROMPT_DIR = KNOWLEDGE_ROOT / "05_prompt_templates"

_NORMALIZE_RE = re.compile(r"[\s_\-·:：,，。/（）()%]+")


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    return _NORMALIZE_RE.sub("", str(value).strip()).lower()


def _safe_load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _dedupe_by_id(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for entry in entries:
        key = str(entry.get("id") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped


def _collect_tokens(value: Any) -> set[str]:
    tokens: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized_key = _normalize_token(key)
            if normalized_key:
                tokens.add(normalized_key)
            tokens.update(_collect_tokens(nested))
        return tokens
    if isinstance(value, list):
        for item in value[:12]:
            tokens.update(_collect_tokens(item))
        return tokens
    if isinstance(value, (str, int, float, bool)):
        normalized_value = _normalize_token(value)
        if normalized_value:
            tokens.add(normalized_value)
    return tokens


def _read_prompt_template(file_name: str, fallback: str) -> str:
    path = PROMPT_DIR / file_name
    if not path.exists():
        return fallback
    try:
        content = path.read_text(encoding="utf-8").strip()
    except Exception:
        return fallback
    return content or fallback


@lru_cache(maxsize=1)
def load_indicator_dictionary() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(INDICATOR_DIR.glob("*.json")):
        entries.extend(_safe_load_json_list(path))
    return _dedupe_by_id(entries)


@lru_cache(maxsize=1)
def load_page_guidance() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(PAGE_GUIDANCE_DIR.glob("*.json")):
        entries.extend(_safe_load_json_list(path))
    return _dedupe_by_id(entries)


@lru_cache(maxsize=1)
def load_result_cards() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(RESULT_DIR.glob("*.json")):
        entries.extend(_safe_load_json_list(path))
    return _dedupe_by_id(entries)


def load_chat_prompt_template(fallback: str) -> str:
    return _read_prompt_template("chat_prompt.txt", fallback)


def load_summary_prompt_template(fallback: str) -> str:
    return _read_prompt_template("summary_prompt.txt", fallback)


def load_tooltip_prompt_template(fallback: str) -> str:
    return _read_prompt_template("tooltip_prompt.txt", fallback)


def _modules_for_page(page: str, snapshot: dict[str, Any]) -> list[str]:
    if page == "greenFinance":
        return ["green_finance", "policy"]
    if page == "carbon":
        if str(snapshot.get("mapMetric") or "").lower() == "gdp" or str(snapshot.get("viewMode") or "") == "macro":
            return ["macro", "carbon", "policy"]
        return ["carbon", "macro", "policy"]
    if page == "energy":
        return ["energy", "carbon", "policy"]
    return ["macro", "policy"]


def _levels_for_page_context(page_context: Any) -> list[str]:
    if getattr(page_context, "drillCity", None):
        return ["county", "city"]
    if getattr(page_context, "drillProvince", None):
        return ["city", "province"]
    if page_context.page == "carbon" and getattr(page_context, "selectedProvince", None):
        return ["city", "province"]
    return ["province"]


def _modules_for_tooltip(payload: Any) -> list[str]:
    module_name = str(payload.moduleName or "")
    if module_name == "greenFinance":
        return ["green_finance", "policy"]
    if module_name == "macro":
        return ["macro"]
    if module_name == "carbon":
        if "gdp" in str(payload.tooltipScope).lower():
            return ["macro", "carbon", "policy"]
        return ["carbon", "macro", "policy"]
    return ["macro"]


def _levels_for_tooltip(payload: Any) -> list[str]:
    scope = str(payload.tooltipScope or "")
    data_payload = payload.dataPayload or {}
    if "County" in scope:
        return ["county"]
    if "City" in scope:
        return ["city"]
    if "Province" in scope:
        return ["province"]
    if data_payload.get("mode") == "city" or data_payload.get("city"):
        return ["city"]
    if data_payload.get("mode") == "county":
        return ["county"]
    if scope in {"greenFinanceTop10", "greenFinanceRadar"}:
        return ["city"] if data_payload.get("drillProvince") else ["province"]
    if scope == "macroTrend":
        return ["city"] if data_payload.get("city") else ["province"]
    return ["province"]


def _indicator_match_score(entry: dict[str, Any], tokens: set[str]) -> int:
    score = 0
    for field_key in entry.get("field_keys", []):
        if _normalize_token(field_key) in tokens:
            score += 6
    for alias in entry.get("alias", []):
        if _normalize_token(alias) in tokens:
            score += 3
    for raw in (entry.get("name"), entry.get("id"), entry.get("category")):
        if _normalize_token(raw) in tokens:
            score += 2
    return score


def _result_match_score(entry: dict[str, Any], tokens: set[str]) -> int:
    score = 0
    for kind in (entry.get("kind"),):
        if _normalize_token(kind) in tokens:
            score += 3
    for tag in entry.get("tags", []):
        if _normalize_token(tag) in tokens:
            score += 2
    return score


def _entry_list(entry: dict[str, Any], plural_key: str, singular_key: str) -> list[str]:
    raw = entry.get(plural_key)
    if raw is None:
        raw = entry.get(singular_key)
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw if str(item).strip()]
    return [str(raw)] if str(raw).strip() else []


def _page_guidance_match_score(entry: dict[str, Any], tokens: set[str]) -> int:
    score = 0
    for raw in (entry.get("kind"), entry.get("title"), entry.get("category")):
        if _normalize_token(raw) in tokens:
            score += 3
    for tag in entry.get("tags", []):
        if _normalize_token(tag) in tokens:
            score += 2
    for trigger in entry.get("trigger_tokens", []):
        if _normalize_token(trigger) in tokens:
            score += 4
    return score


def _select_indicator_entries(
    modules: list[str],
    levels: list[str],
    tokens: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    candidates = [
        entry for entry in load_indicator_dictionary()
        if entry.get("module") in modules and entry.get("level") in levels
    ]
    ranked = sorted(
        [
            (entry, _indicator_match_score(entry, tokens), index)
            for index, entry in enumerate(candidates)
        ],
        key=lambda item: (
            -item[1],
            levels.index(item[0].get("level")),
            modules.index(item[0].get("module")),
            item[2],
        ),
    )
    matched = [entry for entry, score, _ in ranked if score > 0]
    if len(matched) >= limit:
        return matched[:limit]
    fallback = [entry for entry, _, _ in ranked if entry not in matched]
    return (matched + fallback)[:limit]


def _select_result_entries(
    modules: list[str],
    levels: list[str],
    tokens: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    candidates = [
        entry for entry in load_result_cards()
        if entry.get("module") in modules and entry.get("level") in levels
    ]
    ranked = sorted(
        [
            (entry, _result_match_score(entry, tokens), index)
            for index, entry in enumerate(candidates)
        ],
        key=lambda item: (
            -item[1],
            levels.index(item[0].get("level")),
            item[2],
        ),
    )
    matched = [entry for entry, score, _ in ranked if score > 0]
    if len(matched) >= limit:
        return matched[:limit]
    fallback = [entry for entry, _, _ in ranked if entry not in matched]
    return (matched + fallback)[:limit]


def _select_page_guidance_entries(
    page: str,
    modules: list[str],
    levels: list[str],
    tokens: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entry in load_page_guidance():
        entry_pages = _entry_list(entry, "pages", "page")
        entry_modules = _entry_list(entry, "modules", "module")
        entry_levels = _entry_list(entry, "levels", "level")
        if entry_pages and page not in entry_pages:
            continue
        if entry_modules and not any(module in modules for module in entry_modules):
            continue
        if entry_levels and "all" not in entry_levels and not any(level in levels for level in entry_levels):
            continue
        candidates.append(entry)

    ranked = sorted(
        [
            (
                entry,
                _page_guidance_match_score(entry, tokens),
                int(entry.get("sort_order") or 999),
                index,
            )
            for index, entry in enumerate(candidates)
        ],
        key=lambda item: (-item[1], item[2], item[3]),
    )
    matched = [entry for entry, score, _, _ in ranked if score > 0]
    if len(matched) >= limit:
        return matched[:limit]
    fallback = [entry for entry, _, _, _ in ranked if entry not in matched]
    return (matched + fallback)[:limit]


def _format_indicator_entries(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    lines = ["指标字典:"]
    for entry in entries:
        parts = [f"- {entry.get('name', '未命名指标')}"]
        unit = str(entry.get("unit") or "").strip()
        definition = str(entry.get("definition") or "").strip()
        policy_context = str(entry.get("policy_context") or "").strip()
        if unit:
            parts.append(f"单位: {unit}")
        if definition:
            parts.append(f"释义: {definition}")
        if policy_context:
            parts.append(f"政策背景: {policy_context}")
        lines.append("；".join(parts))
    return "\n".join(lines)


def _format_result_entries(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    lines = ["结果卡片:"]
    for entry in entries:
        kind = str(entry.get("kind") or "").strip()
        content = str(entry.get("content") or "").strip()
        if not content:
            continue
        prefix = f"- [{kind}] " if kind else "- "
        lines.append(f"{prefix}{content}")
    return "\n".join(lines)


def _format_page_guidance_entries(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return ""
    lines = ["页面规则:"]
    for entry in entries:
        title = str(entry.get("title") or entry.get("kind") or "规则").strip()
        content = str(entry.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"- {title}: {content}")
    return "\n".join(lines)


def _join_sections(sections: list[str]) -> str:
    filtered = [section.strip() for section in sections if section and section.strip()]
    return "\n\n".join(filtered)


def get_tooltip_knowledge_context(payload: Any) -> str:
    modules = _modules_for_tooltip(payload)
    levels = _levels_for_tooltip(payload)
    tokens = _collect_tokens(payload.dataPayload or {})
    tokens.add(_normalize_token(payload.tooltipScope))
    indicator_entries = _select_indicator_entries(modules, levels, tokens, limit=4)
    result_entries = _select_result_entries(modules, levels, tokens, limit=1)
    return _join_sections([
        _format_indicator_entries(indicator_entries),
        _format_result_entries(result_entries),
    ])


def _collect_page_tokens(page_context: Any) -> set[str]:
    tokens = _collect_tokens(getattr(page_context, "snapshot", {}) or {})
    for raw in (
        getattr(page_context, "page", ""),
        getattr(page_context, "selectedProvince", ""),
        getattr(page_context, "drillProvince", ""),
        getattr(page_context, "drillCity", ""),
    ):
        normalized = _normalize_token(raw)
        if normalized:
            tokens.add(normalized)
    return tokens


def get_page_knowledge_context(page_context: Any, *, include_results: bool, indicator_limit: int) -> str:
    snapshot = getattr(page_context, "snapshot", {}) or {}
    modules = _modules_for_page(page_context.page, snapshot)
    levels = _levels_for_page_context(page_context)
    tokens = _collect_page_tokens(page_context)
    page_guidance_entries = _select_page_guidance_entries(page_context.page, modules, levels, tokens, limit=4)
    indicator_entries = _select_indicator_entries(modules, levels, tokens, limit=indicator_limit)
    result_entries = _select_result_entries(modules, levels, tokens, limit=3 if include_results else 0)
    return _join_sections([
        _format_page_guidance_entries(page_guidance_entries),
        _format_indicator_entries(indicator_entries),
        _format_result_entries(result_entries),
    ])
