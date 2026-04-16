from __future__ import annotations

import json
from typing import Any

from ai_types import AiPageContext
from data_service import (
    get_city_carbon_history_rows,
    get_city_carbon_rows,
    get_city_history_rows,
    get_city_rows,
    get_macro_rows,
    get_macro_stats_records,
    get_province_history_rows,
    get_province_rows,
)
from predict_results_service import get_predict_data_payload


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


def _coerce_city(value: Any, fallback: str | None = None) -> str:
    city = str(value or fallback or "").strip()
    if not city:
        raise AiToolError("缺少城市参数")
    return city


def _coerce_level(value: Any, fallback: str | None = None) -> str:
    level = str(value or fallback or "province").strip().lower()
    if level not in {"province", "city"}:
        raise AiToolError(f"不支持的预测层级: {level}")
    return level


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
            "carbonEmissionWanTon": (
                round(float(row["carbonEmission"]) / 10000, 2)
                if row.get("carbonEmission") is not None
                else None
            ),
            "gdp": row["gdp"],
            "did": row["did"],
        }
        for row in rows
    ]
    top10 = sorted(normalized, key=lambda item: float(item.get("score") or 0), reverse=True)[:10]
    return {"year": year, "count": len(normalized), "top10": top10, "rows": normalized}


def _history_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "count": 0,
            "startYear": None,
            "endYear": None,
            "latest": None,
            "rows": [],
        }
    return {
        "count": len(rows),
        "startYear": rows[0].get("year"),
        "endYear": rows[-1].get("year"),
        "latest": rows[-1],
        "rows": rows,
    }


def _green_finance_province_history_result(province: str) -> dict[str, Any]:
    rows = get_province_history_rows(province)
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
            "carbonEmissionWanTon": (
                round(float(row["carbonEmission"]) / 10000, 2)
                if row.get("carbonEmission") is not None
                else None
            ),
            "gdp": row["gdp"],
            "did": row["did"],
        }
        for row in rows
    ]
    return {"province": province, **_history_payload(normalized)}


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
            "gdp": row.get("gdp"),
            "carbonEmission": row.get("carbonEmission"),
            "carbonEmissionWanTon": row.get("carbonEmissionWanTon"),
        }
        for row in rows
    ]
    top = sorted(normalized, key=lambda item: float(item.get("score") or 0), reverse=True)[:12]
    return {"province": province, "year": year, "count": len(normalized), "top": top, "rows": normalized}


def _green_finance_city_history_result(province: str, city: str) -> dict[str, Any]:
    rows = get_city_history_rows(province, city)
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
            "gdp": row.get("gdp"),
            "carbonEmission": row.get("carbonEmission"),
            "carbonEmissionWanTon": row.get("carbonEmissionWanTon"),
        }
        for row in rows
    ]
    return {"province": province, "city": city, **_history_payload(normalized)}


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
    top10_gdp = sorted(normalized, key=lambda item: float(item.get("gdp") or 0), reverse=True)[:10]
    return {"year": year, "count": len(normalized), "top10": top10, "top10Gdp": top10_gdp, "rows": normalized}


def _carbon_city_result(province: str, year: int) -> dict[str, Any]:
    rows = get_city_carbon_rows(province, year)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "city": row["city"],
            "province": row["province"],
            "year": row["year"],
            "gdp": row.get("gdp"),
            "carbonEmission": row.get("carbonEmission"),
            "carbonEmissionWanTon": row.get("carbonEmissionWanTon"),
            "primaryIndustry": row.get("primaryIndustry"),
            "secondaryIndustry": row.get("secondaryIndustry"),
            "tertiaryIndustry": row.get("tertiaryIndustry"),
            "primaryIndustryRatio": row.get("primaryIndustryRatio"),
            "secondaryIndustryRatio": row.get("secondaryIndustryRatio"),
            "tertiaryIndustryRatio": row.get("tertiaryIndustryRatio"),
        }
        for row in rows
    ]
    top10_carbon = sorted(normalized, key=lambda item: float(item.get("carbonEmissionWanTon") or 0), reverse=True)[:10]
    top10_gdp = sorted(normalized, key=lambda item: float(item.get("gdp") or 0), reverse=True)[:10]
    return {
        "province": province,
        "year": year,
        "count": len(normalized),
        "top10Carbon": top10_carbon,
        "top10Gdp": top10_gdp,
        "rows": normalized,
    }


def _carbon_province_history_result(province: str) -> dict[str, Any]:
    rows = get_province_history_rows(province)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "province": row["province"],
            "year": row["year"],
            "score": row["score"],
            "gdp": row["gdp"],
            "carbonEmission": row["carbonEmission"],
            "carbonEmissionWanTon": (
                round(float(row["carbonEmission"]) / 10000, 2)
                if row.get("carbonEmission") is not None
                else None
            ),
            "primaryIndustry": row.get("primaryIndustry"),
            "secondaryIndustry": row.get("secondaryIndustry"),
            "tertiaryIndustry": row.get("tertiaryIndustry"),
            "primaryIndustryRatio": row.get("primaryIndustryRatio"),
            "secondaryIndustryRatio": row.get("secondaryIndustryRatio"),
            "tertiaryIndustryRatio": row.get("tertiaryIndustryRatio"),
        }
        for row in rows
    ]
    return {"province": province, **_history_payload(normalized)}


def _carbon_city_history_result(province: str, city: str) -> dict[str, Any]:
    rows = get_city_carbon_history_rows(province, city)
    if rows is None:
        raise AiToolError("数据库连接失败")
    normalized = [
        {
            "city": row["city"],
            "province": row["province"],
            "year": row["year"],
            "gdp": row.get("gdp"),
            "carbonEmission": row.get("carbonEmission"),
            "carbonEmissionWanTon": row.get("carbonEmissionWanTon"),
            "primaryIndustry": row.get("primaryIndustry"),
            "secondaryIndustry": row.get("secondaryIndustry"),
            "tertiaryIndustry": row.get("tertiaryIndustry"),
            "primaryIndustryRatio": row.get("primaryIndustryRatio"),
            "secondaryIndustryRatio": row.get("secondaryIndustryRatio"),
            "tertiaryIndustryRatio": row.get("tertiaryIndustryRatio"),
        }
        for row in rows
    ]
    return {"province": province, "city": city, **_history_payload(normalized)}


def _energy_result(level: str, province: str, city: str | None = None) -> dict[str, Any]:
    try:
        payload = get_predict_data_payload(
            level=level,
            target="carbonIntensity",
            province=province,
            city=city,
        )
    except ValueError as exc:
        raise AiToolError(str(exc)) from exc

    compare_series = payload.get("compareSeries") or {}
    compare_history = compare_series.get("historyPoints") or []
    compare_future = compare_series.get("scenarioPoints") or {}

    return {
        "level": payload.get("level"),
        "province": payload.get("province"),
        "city": payload.get("city"),
        "entityLabel": payload.get("entityLabel"),
        "historySeries": payload.get("historySeries") or [],
        "compareSeries": {
            "name": compare_series.get("name"),
            "historyPoints": compare_history,
            "scenarioPoints": compare_future,
        },
        "scenarios": payload.get("scenarios") or [],
        "scenarioBand": payload.get("scenarioBand") or [],
        "coefficients": payload.get("coefficients") or {},
        "sampleMeta": payload.get("sampleMeta") or {},
        "sourceNotice": payload.get("sourceNotice"),
        "weightType": payload.get("weightType"),
        "availableScenarios": payload.get("availableScenarios") or [],
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
                    "description": "查询指定年份的全国省级绿色金融、GDP 与碳排放数据，可用于绿色金融与经济发展、减排表现的关联分析。",
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
                    "description": "查询指定省份、指定年份的地级市绿色金融、GDP 与碳排放关联数据，可用于分析省内城市绿色金融与经济发展、碳排放的协同关系。",
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
            {
                "type": "function",
                "function": {
                    "name": "get_green_finance_province_history",
                    "description": "查询指定省份 2000-2024 年绿色金融、GDP 与碳排放历史序列，可用于趋势分析和跨年比较。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 北京市；不传时默认使用当前选中省份"},
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_green_finance_city_history",
                    "description": "查询指定省份下某个地级市的绿色金融、GDP 与碳排放历史序列，可用于城市趋势分析和城市间历史比较。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 广东省；不传时默认使用当前下钻省份或当前选中省份"},
                            "city": {"type": "string", "description": "地级市名称，例如 广州市"},
                        },
                        "required": ["city"],
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
            },
            {
                "type": "function",
                "function": {
                    "name": "get_carbon_city_data",
                    "description": "查询指定省份、指定年份的地级市碳排放与 GDP 数据，可用于省内城市对比分析。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 广东省；不传时默认使用当前下钻省份"},
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
                    "name": "get_carbon_province_history",
                    "description": "查询指定省份 2000-2024 年碳排放与 GDP 历史序列，可用于长期趋势分析。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 北京市；不传时默认使用当前下钻省份"},
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_carbon_city_history",
                    "description": "查询指定省份下某个地级市的碳排放与 GDP 历史序列，可用于城市趋势与城市间历史比较。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "province": {"type": "string", "description": "省份全称，例如 广东省；不传时默认使用当前下钻省份"},
                            "city": {"type": "string", "description": "地级市名称，例如 深圳市"},
                        },
                        "required": ["city"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    if page_context.page == "energy":
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_energy_prediction_data",
                    "description": "查询预测页当前层级的历史观测、离线三情景结果、对比线和模型系数，可用于解释历史趋势、情景差异和为什么预测上升或下降。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "level": {"type": "string", "description": "预测层级，province 或 city；不传时默认根据当前页面快照推断"},
                            "province": {"type": "string", "description": "省份名称，例如 全国、广东省；市级模式下必须是具体省份"},
                            "city": {"type": "string", "description": "市级模式下的地级市名称，例如 深圳市"},
                        },
                        "required": [],
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

    if tool_name == "get_green_finance_province_history" and page_context.page == "greenFinance":
        province = _coerce_province(args.get("province"), page_context.selectedProvince)
        return _green_finance_province_history_result(province)

    if tool_name == "get_green_finance_city_history" and page_context.page == "greenFinance":
        province = _coerce_province(args.get("province"), page_context.drillProvince or page_context.selectedProvince)
        city = _coerce_city(args.get("city"), page_context.drillCity)
        return _green_finance_city_history_result(province, city)

    if tool_name == "get_carbon_province_data" and page_context.page == "carbon":
        year = _coerce_year(args.get("year"), page_context.year)
        return _carbon_result(year)

    if tool_name == "get_carbon_city_data" and page_context.page == "carbon":
        province = _coerce_province(args.get("province"), page_context.drillProvince or page_context.selectedProvince)
        year = _coerce_year(args.get("year"), page_context.year)
        return _carbon_city_result(province, year)

    if tool_name == "get_carbon_province_history" and page_context.page == "carbon":
        province = _coerce_province(args.get("province"), page_context.drillProvince or page_context.selectedProvince)
        return _carbon_province_history_result(province)

    if tool_name == "get_carbon_city_history" and page_context.page == "carbon":
        province = _coerce_province(args.get("province"), page_context.drillProvince or page_context.selectedProvince)
        city = _coerce_city(args.get("city"), page_context.drillCity)
        return _carbon_city_history_result(province, city)

    if tool_name == "get_energy_prediction_data" and page_context.page == "energy":
        snapshot = page_context.snapshot or {}
        fallback_level = str(snapshot.get("level") or "province")
        level = _coerce_level(args.get("level"), fallback_level)
        fallback_province = page_context.drillProvince or page_context.selectedProvince or "全国"
        province = _coerce_province(args.get("province"), fallback_province)
        city = None
        if level == "city":
            fallback_city = page_context.drillCity or str(snapshot.get("city") or "").strip() or None
            city = _coerce_city(args.get("city"), fallback_city)
        return _energy_result(level, province, city)

    if tool_name == "get_macro_series_data" and page_context.page == "macro":
        province = _coerce_province(args.get("province"), page_context.selectedProvince or "全国")
        return _macro_series_result(province)

    if tool_name == "get_macro_stats_data" and page_context.page == "macro":
        return _macro_stats_result()

    raise AiToolError(f"当前页面不支持工具 {tool_name}")


def summarize_tool_result(tool_name: str, result: dict[str, Any]) -> str:
    if tool_name == "get_green_finance_province_data":
        return f"已获取 {result.get('year')} 年全国 {result.get('count', 0)} 个省级绿色金融样本，包含 GDP 与碳排放字段。"
    if tool_name == "get_green_finance_city_data":
        return f"已获取 {result.get('province')} {result.get('year')} 年 {result.get('count', 0)} 个地级市样本，包含绿色金融、GDP 与碳排放关联字段。"
    if tool_name == "get_green_finance_province_history":
        return f"已获取 {result.get('province')} {result.get('startYear')} 至 {result.get('endYear')} 年的省级历史序列。"
    if tool_name == "get_green_finance_city_history":
        return f"已获取 {result.get('province')}{result.get('city')} {result.get('startYear')} 至 {result.get('endYear')} 年的城市历史序列。"
    if tool_name == "get_carbon_province_data":
        return f"已获取 {result.get('year')} 年全国 {result.get('count', 0)} 个省级碳排放样本，包含 GDP 字段。"
    if tool_name == "get_carbon_city_data":
        return f"已获取 {result.get('province')} {result.get('year')} 年 {result.get('count', 0)} 个地级市碳排放/GDP 样本。"
    if tool_name == "get_carbon_province_history":
        return f"已获取 {result.get('province')} {result.get('startYear')} 至 {result.get('endYear')} 年的省级碳排放历史序列。"
    if tool_name == "get_carbon_city_history":
        return f"已获取 {result.get('province')}{result.get('city')} {result.get('startYear')} 至 {result.get('endYear')} 年的城市碳排放历史序列。"
    if tool_name == "get_energy_prediction_data":
        level = "市级" if result.get("level") == "city" else "省级"
        entity = result.get("city") or result.get("province") or result.get("entityLabel") or "当前区域"
        return (
            f"已获取 {level}预测对象 {entity} 的历史观测、离线情景结果、对比线和模型系数，"
            f"可用于解释趋势、情景差异和预测变化原因。"
        )
    if tool_name == "get_macro_series_data":
        return f"已获取 {result.get('province')} 的宏观时间序列，共 {result.get('count', 0)} 条记录。"
    if tool_name == "get_macro_stats_data":
        return f"已获取宏观描述性统计，共 {result.get('count', 0)} 条指标记录。"
    return f"已完成工具 {tool_name} 查询。"
