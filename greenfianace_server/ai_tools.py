from __future__ import annotations

import json
from typing import Any

from ai_types import AiPageContext
from data_service import (
    get_city_rows,
    get_macro_rows,
    get_macro_stats_records,
    get_predict_payload,
    get_province_rows,
)


class AiToolError(RuntimeError):
    pass


def _coerce_year(value: Any, fallback: int | None) -> int:
    if value in (None, ""):
        if fallback is None:
            raise AiToolError("缺少年份参数")
        return int(fallback)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise AiToolError(f"年份参数无效: {value}") from exc


def _coerce_province(value: Any, fallback: str | None) -> str:
    province = str(value or fallback or "").strip()
    if not province:
        raise AiToolError("缺少省份参数")
    return province


def _json_loads(arguments: str) -> dict[str, Any]:
    if not arguments.strip():
        return {}
    try:
        payload = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise AiToolError(f"工具参数不是合法 JSON: {arguments}") from exc
    if not isinstance(payload, dict):
        raise AiToolError("工具参数必须是对象")
    return payload


def _green_finance_province_result(year: int) -> dict[str, Any]:
    rows = get_province_rows(year)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "province": row["province"],
            "year": row["year"],
            "score": row["score"],
            "greenCredit": row["greenCredit"],
            "greenInvest": row["greenInvest"],
            "greenInsurance": row["greenInsurance"],
            "greenBond": row["greenBond"],
            "greenSupport": row["greenSupport"],
            "greenFund": row["greenFund"],
            "greenEquity": row["greenEquity"],
            "carbonEmission": row["carbonEmission"],
            "gdp": row["gdp"],
            "did": row["did"],
        }
        for row in rows
    ]
    top10 = sorted(normalized, key=lambda item: float(item.get("score") or 0), reverse=True)[:10]
    return {"year": year, "count": len(normalized), "top10": top10, "rows": normalized}


def _green_finance_city_result(province: str, year: int) -> dict[str, Any]:
    rows = get_city_rows(province, year)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "city": row["city"],
            "province": row["province"],
            "year": row["year"],
            "score": row["score"],
            "greenCredit": row["greenCredit"],
            "greenInvest": row["greenInvest"],
            "greenInsurance": row["greenInsurance"],
            "greenBond": row["greenBond"],
            "greenSupport": row["greenSupport"],
            "greenFund": row["greenFund"],
            "greenEquity": row["greenEquity"],
        }
        for row in rows
    ]
    top = sorted(normalized, key=lambda item: float(item.get("score") or 0), reverse=True)[:12]
    return {"province": province, "year": year, "count": len(normalized), "top": top, "rows": normalized}


def _carbon_result(year: int) -> dict[str, Any]:
    rows = get_province_rows(year)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "province": row["province"],
            "year": row["year"],
            "carbonEmission": row["carbonEmission"],
            "score": row["score"],
            "gdp": row["gdp"],
        }
        for row in rows
    ]
    top10 = sorted(normalized, key=lambda item: float(item.get("carbonEmission") or 0), reverse=True)[:10]
    return {"year": year, "count": len(normalized), "top10": top10, "rows": normalized}


def _energy_result(province: str) -> dict[str, Any]:
    payload = get_predict_payload()
    if payload is None:
        raise AiToolError("数据库连接失败")
    history_data = payload["historyData"]
    return {
        "province": province,
        "coefficients": payload["coefficients"],
        "historySeries": history_data.get(province) or history_data.get("全国") or [],
        "nationalHistorySeries": history_data.get("全国") or [],
    }


def _macro_series_result(province: str | None) -> dict[str, Any]:
    rows = get_macro_rows(province if province and province != "全国" else None)
    if rows is None:
        raise AiToolError("数据库连接失败")
    return {
        "province": province or "全国",
        "count": len(rows),
        "rows": rows,
    }


def _macro_stats_result() -> dict[str, Any]:
    rows = get_macro_stats_records()
    if rows is None:
        raise AiToolError("数据库连接失败")
    return {"count": len(rows), "rows": rows}


def build_page_tools(page_context: AiPageContext) -> list[dict[str, Any]]:
    empty_object = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    if page_context.page == "greenFinance":
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_green_finance_province_data",
                    "description": "查询指定年份的全国省级绿色金融与碳排放数据。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "integer", "description": "要查询的年份，例如 2024"},
                        },
                        "required": ["year"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_green_finance_city_data",
                    "description": "查询指定省份、指定年份的地级市绿色金融数据。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 广东省"},
                            "year": {"type": "integer", "description": "要查询的年份，例如 2024"},
                        },
                        "required": ["province", "year"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    if page_context.page == "carbon":
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_carbon_province_data",
                    "description": "查询指定年份的全国省级碳排放与相关指标数据。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "year": {"type": "integer", "description": "要查询的年份，例如 2024"},
                        },
                        "required": ["year"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

    if page_context.page == "energy":
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_energy_prediction_data",
                    "description": "查询指定区域的碳排放强度预测历史序列与模型系数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "区域名称，例如 全国、广东省"},
                        },
                        "required": ["province"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

    if page_context.page == "macro":
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_macro_series_data",
                    "description": "查询指定区域的 GDP 与碳排放时间序列。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "区域名称，例如 全国、广东省"},
                        },
                        "required": ["province"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_macro_stats_data",
                    "description": "查询宏观指标描述性统计结果。",
                    "parameters": empty_object,
                },
            },
        ]

    return []


def execute_page_tool(page_context: AiPageContext, tool_name: str, arguments_json: str) -> dict[str, Any]:
    args = _json_loads(arguments_json)

    if tool_name == "get_green_finance_province_data" and page_context.page == "greenFinance":
        year = _coerce_year(args.get("year"), page_context.year)
        return _green_finance_province_result(year)

    if tool_name == "get_green_finance_city_data" and page_context.page == "greenFinance":
        province = _coerce_province(args.get("province"), page_context.drillProvince or page_context.selectedProvince)
        year = _coerce_year(args.get("year"), page_context.year)
        return _green_finance_city_result(province, year)

    if tool_name == "get_carbon_province_data" and page_context.page == "carbon":
        year = _coerce_year(args.get("year"), page_context.year)
        return _carbon_result(year)

    if tool_name == "get_energy_prediction_data" and page_context.page == "energy":
        province = _coerce_province(args.get("province"), page_context.selectedProvince or "全国")
        return _energy_result(province)

    if tool_name == "get_macro_series_data" and page_context.page == "macro":
        province = _coerce_province(args.get("province"), page_context.selectedProvince or "全国")
        return _macro_series_result(province)

    if tool_name == "get_macro_stats_data" and page_context.page == "macro":
        return _macro_stats_result()

    raise AiToolError(f"当前页面不支持工具 {tool_name}")


def summarize_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    if tool_name == "get_green_finance_province_data":
        return f"已获取 {result.get('year')} 年全国 {result.get('count', 0)} 个省级绿色金融样本。"
    if tool_name == "get_green_finance_city_data":
        return f"已获取 {result.get('province')} {result.get('year')} 年 {result.get('count', 0)} 个地级市样本。"
    if tool_name == "get_carbon_province_data":
        return f"已获取 {result.get('year')} 年全国 {result.get('count', 0)} 个省级碳排放样本。"
    if tool_name == "get_energy_prediction_data":
        return f"已获取 {result.get('province')} 的预测历史序列和模型系数。"
    if tool_name == "get_macro_series_data":
        return f"已获取 {result.get('province')} 的宏观时间序列，共 {result.get('count', 0)} 条记录。"
    if tool_name == "get_macro_stats_data":
        return f"已获取宏观描述性统计，共 {result.get('count', 0)} 条指标记录。"
    return f"已完成工具 {tool_name} 查询。"
