from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
EMPIRICAL_RESULTS_ROOT = ROOT / "empirical_results"

PROVINCE_FIELD = "省份"
CITY_FIELD = "地级市"
YEAR_FIELD = "年份"
NATIONWIDE = "全国"
PANEL_FILE = "中国绿色金融-能源平衡面板数据集(最终版).csv"

TARGETS: dict[str, dict[str, str]] = {
    "carbonIntensity": {
        "label": "碳排放强度",
        "historyFieldProvince": "碳排放强度",
        "historyFieldCity": "碳排放强度",
    }
}

SCENARIO_LABELS = {
    "baseline": "基准",
    "lowCarbon": "低碳",
    "optimized": "优化",
}

SCENARIO_NAME_MAP = {
    "基准情景": "baseline",
    "低碳情景": "lowCarbon",
    "优化情景": "optimized",
}

SOURCES: dict[str, dict[str, str]] = {
    "combo": {
        "label": "组合预测",
        "scenarioFile": "组合预测结果.csv",
        "valueField": "组合预测值",
    },
    "stirpat": {
        "label": "STIRPAT",
        "scenarioFile": "STIRPAT三情景预测结果.csv",
        "valueField": "预测值",
    },
    "systemDynamics": {
        "label": "系统动力学",
        "scenarioFile": "系统动力学情景仿真结果.csv",
        "valueFieldTemplate": "预测_{target_label}",
    },
}

CUSTOM_DRIVER_CONFIG: list[dict[str, Any]] = [
    {
        "key": "population",
        "label": "人口",
        "hint": "调节人口规模变化对未来碳排放强度的弹性影响。",
        "aliases": ["ln_年末常住人口", "ln_年末常住人口数"],
    },
    {
        "key": "affluence",
        "label": "富裕度",
        "hint": "调节人均 GDP 变化对未来碳排放强度的弹性影响。",
        "aliases": ["ln_人均地区生产总值"],
    },
    {
        "key": "technology",
        "label": "技术或能耗",
        "hint": "优先使用人均能源消耗弹性，反映技术进步或能耗变化。",
        "aliases": ["ln_人均能源消耗"],
    },
    {
        "key": "industry",
        "label": "产业结构",
        "hint": "使用产业结构相关弹性，模拟产业升级或回摆的影响。",
        "aliases": ["ln_第二产业增加值占GDP比重", "ln_产业结构高级化"],
    },
    {
        "key": "energyStructure",
        "label": "能源结构",
        "hint": "优先使用天然气占比；若缺失则退化为能源强度相关弹性。",
        "aliases": ["ln_天然气占比", "ln_能源消费强度", "ln_能源强度"],
    },
    {
        "key": "greenFinance",
        "label": "绿色金融",
        "hint": "模拟绿色金融投入变化对未来碳排放强度的影响。",
        "aliases": ["ln_绿色金融综合指数", "ln_gfi_std"],
    },
]

FUTURE_YEARS = (2025, 2026, 2027)


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def _safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _compact_number(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized: dict[str, str] = {}
            for key, value in row.items():
                normalized[(key or "").strip()] = (value or "").strip()
            rows.append(normalized)
        return rows


def _level_root(level: str) -> Path:
    return EMPIRICAL_RESULTS_ROOT / level


@lru_cache(maxsize=2)
def _load_panel_rows(level: str) -> list[dict[str, str]]:
    return _read_csv_rows(_level_root(level) / PANEL_FILE)


def _source_value_field(source: str, target: str) -> str:
    source_config = SOURCES[source]
    if "valueField" in source_config:
        return source_config["valueField"]
    return source_config["valueFieldTemplate"].format(target_label=TARGETS[target]["label"])


@lru_cache(maxsize=12)
def _load_source_rows(level: str, source: str, target: str) -> list[dict[str, str]]:
    scenario_file = SOURCES[source]["scenarioFile"]
    scenario_path = _level_root(level) / "prediction_results" / "scenario" / scenario_file
    return _read_csv_rows(scenario_path)


@lru_cache(maxsize=2)
def _load_stirpat_rows(level: str) -> list[dict[str, str]]:
    stirpat_path = _level_root(level) / "prediction_results" / "stirpat" / "STIRPAT面板固定效应结果.csv"
    return _read_csv_rows(stirpat_path)


def _point_from_province_row(row: dict[str, str], target: str) -> dict[str, Any] | None:
    year = _safe_int(row.get(YEAR_FIELD))
    value = _safe_float(row.get(TARGETS[target]["historyFieldProvince"]))
    if year is None or value is None:
        return None
    return {
        "year": year,
        "value": _compact_number(value),
        "gfi_std": _compact_number(_safe_float(row.get("gfi_std"))),
        "ln_pop": _compact_number(_safe_float(row.get("ln_pop"))),
        "energy_intensity": _compact_number(_safe_float(row.get("能源强度") or row.get("能源消费强度"))),
        "energy_per_capita": _compact_number(_safe_float(row.get("人均能源消耗"))),
    }


def _point_from_city_row(row: dict[str, str], target: str) -> dict[str, Any] | None:
    year = _safe_int(row.get(YEAR_FIELD))
    value = _safe_float(row.get(TARGETS[target]["historyFieldCity"]))
    if year is None or value is None:
        return None
    return {
        "year": year,
        "value": _compact_number(value),
        "gfi_std": _compact_number(_safe_float(row.get("gfi_std"))),
        "population": _compact_number(_safe_float(row.get("年末常住人口数") or row.get("年末常住人口")), 2),
        "energy_intensity": _compact_number(_safe_float(row.get("能源消费强度") or row.get("能源强度"))),
        "energy_per_capita": _compact_number(_safe_float(row.get("人均能源消耗"))),
        "gdp_growth": _compact_number(_safe_float(row.get("GDP增速")), 2),
        "per_capita_gdp": _compact_number(_safe_float(row.get("人均地区生产总值")), 2),
    }


def _average_points(rows: list[dict[str, str]], value_field: str) -> list[dict[str, Any]]:
    buckets: dict[int, dict[str, list[float]]] = {}
    for row in rows:
        year = _safe_int(row.get(YEAR_FIELD))
        value = _safe_float(row.get(value_field))
        if year is None or value is None:
            continue

        bucket = buckets.setdefault(
            year,
            {
                "value": [],
                "gfi_std": [],
                "ln_pop": [],
                "energy_intensity": [],
                "energy_per_capita": [],
            },
        )
        bucket["value"].append(value)

        gfi = _safe_float(row.get("gfi_std"))
        if gfi is not None:
            bucket["gfi_std"].append(gfi)

        ln_pop = _safe_float(row.get("ln_pop"))
        if ln_pop is not None:
            bucket["ln_pop"].append(ln_pop)

        energy_intensity = _safe_float(row.get("能源强度") or row.get("能源消费强度"))
        if energy_intensity is not None:
            bucket["energy_intensity"].append(energy_intensity)

        energy_per_capita = _safe_float(row.get("人均能源消耗"))
        if energy_per_capita is not None:
            bucket["energy_per_capita"].append(energy_per_capita)

    points: list[dict[str, Any]] = []
    for year in sorted(buckets):
        bucket = buckets[year]
        points.append(
            {
                "year": year,
                "value": _compact_number(sum(bucket["value"]) / len(bucket["value"])),
                "gfi_std": _compact_number(sum(bucket["gfi_std"]) / len(bucket["gfi_std"])) if bucket["gfi_std"] else None,
                "ln_pop": _compact_number(sum(bucket["ln_pop"]) / len(bucket["ln_pop"])) if bucket["ln_pop"] else None,
                "energy_intensity": _compact_number(sum(bucket["energy_intensity"]) / len(bucket["energy_intensity"])) if bucket["energy_intensity"] else None,
                "energy_per_capita": _compact_number(sum(bucket["energy_per_capita"]) / len(bucket["energy_per_capita"])) if bucket["energy_per_capita"] else None,
            }
        )
    return points


def _average_simple_series(rows: list[dict[str, str]], value_field: str) -> list[dict[str, Any]]:
    buckets: dict[int, list[float]] = {}
    for row in rows:
        year = _safe_int(row.get(YEAR_FIELD))
        value = _safe_float(row.get(value_field))
        if year is None or value is None:
            continue
        buckets.setdefault(year, []).append(value)

    return [
        {
            "year": year,
            "value": _compact_number(sum(values) / len(values)),
        }
        for year, values in sorted(buckets.items())
        if values and year in FUTURE_YEARS
    ]


@lru_cache(maxsize=1)
def _city_to_province_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _load_panel_rows("city"):
        city = row.get(CITY_FIELD, "")
        province = row.get(PROVINCE_FIELD, "")
        if city and province:
            mapping.setdefault(city, province)
    return mapping


@lru_cache(maxsize=2)
def _load_stirpat_coefficients(level: str) -> dict[str, float]:
    raw: dict[str, float] = {}
    for row in _load_stirpat_rows(level):
        name = (row.get("变量") or "").strip()
        value = _safe_float(row.get("系数"))
        if name and value is not None:
            raw[name] = float(value)
    return raw


def _pick_alias(raw: dict[str, float], aliases: list[str]) -> tuple[float, str | None]:
    for alias in aliases:
        if alias in raw:
            return float(raw[alias]), alias
    return 0.0, None


def _build_stirpat_custom_meta(level: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = _load_stirpat_coefficients(level)
    drivers: list[dict[str, Any]] = []
    elasticities: dict[str, Any] = {"raw": raw}

    for item in CUSTOM_DRIVER_CONFIG:
        coefficient, matched = _pick_alias(raw, item["aliases"])
        elasticities[item["key"]] = coefficient
        drivers.append(
            {
                "key": item["key"],
                "label": item["label"],
                "hint": item["hint"],
                "coefficient": _compact_number(coefficient, 6) or 0,
                "featureLabel": matched.replace("ln_", "") if matched else None,
                "active": matched is not None,
            }
        )

    return drivers, elasticities


@lru_cache(maxsize=1)
def _predict_meta_cache() -> dict[str, Any]:
    province_rows = _load_panel_rows("province")
    city_rows = _load_panel_rows("city")

    provinces = sorted({row.get(PROVINCE_FIELD, "") for row in province_rows if row.get(PROVINCE_FIELD)})
    cities_by_province: dict[str, list[str]] = {}
    for row in city_rows:
        province = row.get(PROVINCE_FIELD, "")
        city = row.get(CITY_FIELD, "")
        if not province or not city:
            continue
        cities_by_province.setdefault(province, [])
        if city not in cities_by_province[province]:
            cities_by_province[province].append(city)

    for province in cities_by_province:
        cities_by_province[province].sort()

    province_years = sorted({_safe_int(row.get(YEAR_FIELD)) for row in province_rows if _safe_int(row.get(YEAR_FIELD)) is not None})
    city_years = sorted({_safe_int(row.get(YEAR_FIELD)) for row in city_rows if _safe_int(row.get(YEAR_FIELD)) is not None})

    return {
        "levels": [
            {"key": "province", "label": "省级预测"},
            {"key": "city", "label": "市级预测"},
        ],
        "targets": [
            {"key": "carbonIntensity", "label": "碳排放强度"},
        ],
        "sources": [
            {"key": key, "label": config["label"]}
            for key, config in SOURCES.items()
        ],
        "defaultSource": "combo",
        "scenarios": [
            {
                "key": key,
                "label": label,
                "sourceLabel": next(raw for raw, mapped in SCENARIO_NAME_MAP.items() if mapped == key),
            }
            for key, label in SCENARIO_LABELS.items()
        ],
        "provinces": provinces,
        "citiesByProvince": cities_by_province,
        "sampleMeta": {
            "province": {
                "historyStartYear": province_years[0] if province_years else None,
                "historyEndYear": province_years[-1] if province_years else None,
                "forecastStartYear": FUTURE_YEARS[0],
                "forecastEndYear": FUTURE_YEARS[-1],
                "coverageCount": len(provinces),
                "coverageNote": "省级历史序列来自最终清洗面板数据，全国线按省级样本均值计算。",
            },
            "city": {
                "historyStartYear": city_years[0] if city_years else None,
                "historyEndYear": city_years[-1] if city_years else None,
                "forecastStartYear": FUTURE_YEARS[0],
                "forecastEndYear": FUTURE_YEARS[-1],
                "coverageCount": sum(len(cities) for cities in cities_by_province.values()),
                "coverageNote": "市级历史序列来自最终清洗面板数据，对比线按同省市级样本均值计算。",
            },
            "boundaryNotice": "2000-2024 为历史观测，2025-2027 为离线模型推演；情景区间是三种官方情景的包络带，不是统计置信区间。",
        },
    }


def get_predict_meta_payload() -> dict[str, Any]:
    return _predict_meta_cache()


def _get_default_city(province: str) -> str | None:
    city_list = _predict_meta_cache()["citiesByProvince"].get(province) or []
    return city_list[0] if city_list else None


def _build_entity_history(level: str, target: str, province: str, city: str | None) -> tuple[str, list[dict[str, Any]]]:
    rows = _load_panel_rows(level)
    if level == "province":
        if province == NATIONWIDE:
            return "全国样本均值", _average_points(rows, TARGETS[target]["historyFieldProvince"])
        entity_rows = [row for row in rows if row.get(PROVINCE_FIELD) == province]
        points = [point for row in entity_rows if (point := _point_from_province_row(row, target)) is not None]
        points.sort(key=lambda item: item["year"])
        return province, points

    selected_city = city or _get_default_city(province)
    entity_rows = [row for row in rows if row.get(PROVINCE_FIELD) == province and row.get(CITY_FIELD) == selected_city]
    points = [point for row in entity_rows if (point := _point_from_city_row(row, target)) is not None]
    points.sort(key=lambda item: item["year"])
    return selected_city or "", points


def _build_compare_history(level: str, target: str, province: str) -> tuple[str, list[dict[str, Any]]]:
    rows = _load_panel_rows(level)
    if level == "province":
        return "全国样本均值", _average_points(rows, TARGETS[target]["historyFieldProvince"])

    compare_rows = [row for row in rows if row.get(PROVINCE_FIELD) == province]
    return f"{province}市级均值", _average_points(compare_rows, TARGETS[target]["historyFieldCity"])


def _build_entity_scenarios(
    level: str,
    target: str,
    province: str,
    city: str | None,
    source: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = _load_source_rows(level, source, target)
    if not rows:
        return [], []

    if level == "province":
        entity_rows = rows if province == NATIONWIDE else [row for row in rows if row.get(PROVINCE_FIELD) == province]
    else:
        selected_city = city or _get_default_city(province)
        entity_rows = [row for row in rows if row.get(CITY_FIELD) == selected_city]

    value_field = _source_value_field(source, target)
    scenario_rows_by_key: dict[str, list[dict[str, str]]] = {}
    for row in entity_rows:
        scenario_key = SCENARIO_NAME_MAP.get(row.get("情景", ""))
        year = _safe_int(row.get(YEAR_FIELD))
        value = _safe_float(row.get(value_field))
        if scenario_key is None or year not in FUTURE_YEARS or value is None:
            continue
        scenario_rows_by_key.setdefault(scenario_key, []).append(row)

    normalized: list[dict[str, Any]] = []
    should_average_entity_series = level == "province" and province == NATIONWIDE
    for scenario_key, label in SCENARIO_LABELS.items():
        scenario_rows = scenario_rows_by_key.get(scenario_key, [])
        if should_average_entity_series:
            points = _average_simple_series(scenario_rows, value_field)
        else:
            points = sorted(
                [
                    {
                        "year": _safe_int(row.get(YEAR_FIELD)),
                        "value": _compact_number(_safe_float(row.get(value_field))),
                    }
                    for row in scenario_rows
                    if _safe_int(row.get(YEAR_FIELD)) in FUTURE_YEARS and _safe_float(row.get(value_field)) is not None
                ],
                key=lambda item: item["year"],
            )
        if not points:
            continue
        normalized.append({"key": scenario_key, "label": label, "points": points})
    return normalized, [item["key"] for item in normalized]


def _build_compare_future(level: str, target: str, province: str, source: str) -> dict[str, list[dict[str, Any]]]:
    rows = _load_source_rows(level, source, target)
    if not rows:
        return {}

    if level == "province":
        relevant_rows = rows
    else:
        city_to_province = _city_to_province_map()
        relevant_rows = [row for row in rows if city_to_province.get(row.get(CITY_FIELD, "")) == province]

    value_field = _source_value_field(source, target)
    scenario_groups: dict[str, list[dict[str, str]]] = {}
    for row in relevant_rows:
        scenario_key = SCENARIO_NAME_MAP.get(row.get("情景", ""))
        if scenario_key:
            scenario_groups.setdefault(scenario_key, []).append(row)

    return {
        scenario_key: _average_simple_series(scenario_rows, value_field)
        for scenario_key, scenario_rows in scenario_groups.items()
    }


def _build_scenario_band(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, list[float]] = {year: [] for year in FUTURE_YEARS}
    for scenario in scenarios:
        for point in scenario["points"]:
            if point["year"] in by_year and point.get("value") is not None:
                by_year[point["year"]].append(float(point["value"]))

    band: list[dict[str, Any]] = []
    for year in FUTURE_YEARS:
        values = by_year[year]
        if values:
            band.append(
                {
                    "year": year,
                    "min": _compact_number(min(values)),
                    "max": _compact_number(max(values)),
                }
            )
    return band


def _source_notice(source: str, has_scenarios: bool) -> str:
    label = SOURCES[source]["label"]
    if not has_scenarios:
        return f"当前来源“{label}”暂无离线预测输出，请先运行新的 prediction_model.py 生成结果文件。"
    if source == "stirpat":
        return "当前来源为 STIRPAT 面板预测，可用于解释主要驱动项和弹性方向。"
    if source == "systemDynamics":
        return "当前来源为系统动力学情景仿真结果，强调政策反馈与时滞效应。"
    return "当前来源为组合预测结果，按 STIRPAT 与系统动力学的离线输出加权融合。"


def _build_custom_payload(
    level: str,
    source: str,
) -> tuple[bool, list[dict[str, Any]], dict[str, Any] | None, str | None, str | None]:
    if source not in {"combo", "stirpat"}:
        return False, [], None, None, None

    custom_drivers, stirpat_elasticities = _build_stirpat_custom_meta(level)
    supports_custom = any(bool(driver.get("active")) for driver in custom_drivers)
    if not supports_custom:
        return False, custom_drivers, stirpat_elasticities, None, None

    custom_notice = (
        "当前自定义为基于 STIRPAT 弹性的组合预测近似调节，不是后端正式重算。"
        if source == "combo"
        else "当前自定义基于 STIRPAT 弹性系数进行推演。"
    )
    return True, custom_drivers, stirpat_elasticities, "stirpat", custom_notice


def get_predict_data_payload(
    level: str,
    target: str,
    province: str | None = None,
    city: str | None = None,
    source: str = "combo",
) -> dict[str, Any]:
    if level not in {"province", "city"}:
        raise ValueError(f"不支持的预测层级: {level}")
    if target not in TARGETS:
        raise ValueError(f"不支持的预测目标: {target}")
    if source not in SOURCES:
        raise ValueError(f"不支持的预测来源: {source}")

    selected_province = (province or NATIONWIDE).strip() or NATIONWIDE
    if level == "city" and selected_province == NATIONWIDE:
        raise ValueError("市级预测必须提供省份")

    entity_label, history_series = _build_entity_history(level, target, selected_province, city)
    compare_label, compare_history = _build_compare_history(
        level,
        target,
        selected_province if level == "city" else NATIONWIDE,
    )
    scenarios, available_scenarios = _build_entity_scenarios(level, target, selected_province, city, source)
    compare_future = _build_compare_future(
        level,
        target,
        selected_province if level == "city" else NATIONWIDE,
        source,
    )
    meta = _predict_meta_cache()
    sample_meta = meta["sampleMeta"][level]
    supports_custom, custom_drivers, stirpat_elasticities, custom_basis, custom_notice = _build_custom_payload(level, source)

    return {
        "level": level,
        "target": target,
        "source": source,
        "sourceLabel": SOURCES[source]["label"],
        "entityLabel": entity_label,
        "province": selected_province,
        "city": city or (entity_label if level == "city" else None),
        "historySeries": history_series,
        "compareSeries": {
            "name": compare_label,
            "historyPoints": compare_history,
            "scenarioPoints": compare_future,
        },
        "scenarios": scenarios,
        "scenarioBand": _build_scenario_band(scenarios),
        "sampleMeta": {
            **sample_meta,
            "boundaryNotice": meta["sampleMeta"]["boundaryNotice"],
        },
        "sourceNotice": _source_notice(source, bool(available_scenarios)),
        "availableScenarios": available_scenarios,
        "supportsCustom": supports_custom,
        "customDrivers": custom_drivers,
        "stirpatElasticities": stirpat_elasticities,
        "customBasis": custom_basis,
        "customNotice": custom_notice,
    }
