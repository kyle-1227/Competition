from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
EMPIRICAL_RESULTS_ROOT = ROOT / "empirical_results"

TARGETS: dict[str, dict[str, str]] = {
    "carbonIntensity": {
        "label": "碳排放强度",
        "scenarioFile": "碳排放强度_三情景预测结果.csv",
        "historyFieldProvince": "碳排放强度",
        "historyFieldCity": "碳排放强度",
    }
}

SCENARIO_LABELS = {
    "conservative": "保守",
    "baseline": "基准",
    "optimistic": "乐观",
}

SCENARIO_NAME_MAP = {
    "保守情景": "conservative",
    "基准情景": "baseline",
    "乐观情景": "optimistic",
}

WEIGHT_FILE_PRIORITY = [
    ("nested", "嵌套权重"),
    ("economic", "经济权重"),
    ("geographic", "地理权重"),
]

FUTURE_YEARS = (2025, 2026, 2027)


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:  # NaN
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
        normalized: list[dict[str, str]] = []
        for row in reader:
            clean_row: dict[str, str] = {}
            for key, value in row.items():
                normalized_key = (key or "").strip()
                clean_row[normalized_key] = (value or "").strip()
            normalized.append(clean_row)
        return normalized


def _level_root(level: str) -> Path:
    return EMPIRICAL_RESULTS_ROOT / level


@lru_cache(maxsize=2)
def _load_panel_rows(level: str) -> list[dict[str, str]]:
    panel_path = _level_root(level) / "中国绿色金融-能源平衡面板数据集(最终版).csv"
    return _read_csv_rows(panel_path)


@lru_cache(maxsize=4)
def _load_scenario_rows(level: str, target: str) -> list[dict[str, str]]:
    target_config = TARGETS.get(target)
    if not target_config:
        return []
    scenario_path = _level_root(level) / "prediction_results" / "scenario" / target_config["scenarioFile"]
    return _read_csv_rows(scenario_path)


def _coefficient_path(level: str, target: str, weight_label: str) -> Path:
    target_label = TARGETS[target]["label"]
    return _level_root(level) / "spatial" / "主回归结果" / f"{target_label}_{weight_label}_回归系数.csv"


@lru_cache(maxsize=6)
def _load_coefficients(level: str, target: str) -> tuple[dict[str, float], str]:
    for weight_key, weight_label in WEIGHT_FILE_PRIORITY:
        rows = _read_csv_rows(_coefficient_path(level, target, weight_label))
        if not rows:
            continue

        raw: dict[str, float] = {}
        for row in rows:
            name = row.get("") or row.get("Unnamed: 0") or row.get("index") or row.get("参数") or ""
            value = _safe_float(row.get("parameter") or row.get("value") or row.get("系数"))
            if name and value is not None:
                raw[name] = float(value)
        if raw:
            return raw, weight_label

    return {}, WEIGHT_FILE_PRIORITY[0][1]


def _pick_coefficient(raw: dict[str, float], *names: str) -> float:
    for name in names:
        if name in raw:
            return float(raw[name])
    return 0.0


def _build_frontend_coefficients(level: str, target: str) -> tuple[dict[str, Any], str]:
    raw, weight_type = _load_coefficients(level, target)
    coefficients = {
        "core": _pick_coefficient(raw, "gfi_std"),
        "control": _pick_coefficient(raw, "人均能源消耗", "能源强度", "能源消费强度"),
        "control_ln_pop": _pick_coefficient(raw, "ln_pop", "年末常住人口数"),
        "policy": _pick_coefficient(raw, "DID", "did", "绿色金融试点DID", "碳排放交易DID"),
        "spatial": _pick_coefficient(raw, "W_gfi_std"),
        "rho": _pick_coefficient(raw, "W_碳排放强度"),
        "mediator": _pick_coefficient(raw, "indus_2", "第二产业增加值占GDP比重", "能源利用效率"),
        "raw": raw,
    }
    return coefficients, weight_type


def _point_from_province_row(row: dict[str, str], target: str) -> dict[str, Any] | None:
    year = _safe_int(row.get("年份"))
    value = _safe_float(row.get(TARGETS[target]["historyFieldProvince"]))
    if year is None or value is None:
        return None
    return {
        "year": year,
        "value": _compact_number(value),
        "gfi_std": _compact_number(_safe_float(row.get("gfi_std"))),
        "ln_pop": _compact_number(_safe_float(row.get("ln_pop"))),
        "energy_intensity": _compact_number(_safe_float(row.get("能源强度"))),
        "energy_per_capita": _compact_number(_safe_float(row.get("人均能源消耗"))),
    }


def _point_from_city_row(row: dict[str, str], target: str) -> dict[str, Any] | None:
    year = _safe_int(row.get("年份"))
    value = _safe_float(row.get(TARGETS[target]["historyFieldCity"]))
    if year is None or value is None:
        return None
    return {
        "year": year,
        "value": _compact_number(value),
        "gfi_std": _compact_number(_safe_float(row.get("gfi_std"))),
        "population": _compact_number(_safe_float(row.get("年末常住人口数")), 2),
        "energy_intensity": _compact_number(_safe_float(row.get("能源消费强度"))),
        "energy_per_capita": _compact_number(_safe_float(row.get("人均能源消耗"))),
        "gdp_growth": _compact_number(_safe_float(row.get("GDP增速")), 2),
        "per_capita_gdp": _compact_number(_safe_float(row.get("人均地区生产总值")), 2),
    }


def _average_points(rows: list[dict[str, str]], target: str, value_builder: str) -> list[dict[str, Any]]:
    buckets: dict[int, dict[str, list[float]]] = {}
    for row in rows:
        year = _safe_int(row.get("年份"))
        value = _safe_float(row.get(TARGETS[target][value_builder]))
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


def _average_simple_series(rows: list[dict[str, str]], year_field: str, value_field: str) -> list[dict[str, Any]]:
    buckets: dict[int, list[float]] = {}
    for row in rows:
        year = _safe_int(row.get(year_field))
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
        if values
    ]


@lru_cache(maxsize=1)
def _city_to_province_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for row in _load_panel_rows("city"):
        city = row.get("地级市", "")
        province = row.get("省份", "")
        if city and province:
            mapping.setdefault(city, province)
    return mapping


@lru_cache(maxsize=1)
def _predict_meta_cache() -> dict[str, Any]:
    province_rows = _load_panel_rows("province")
    city_rows = _load_panel_rows("city")

    provinces = sorted({row.get("省份", "") for row in province_rows if row.get("省份")}, key=lambda value: value)
    cities_by_province: dict[str, list[str]] = {}
    for row in city_rows:
        province = row.get("省份", "")
        city = row.get("地级市", "")
        if not province or not city:
            continue
        cities_by_province.setdefault(province, [])
        if city not in cities_by_province[province]:
            cities_by_province[province].append(city)

    for province in cities_by_province:
        cities_by_province[province].sort()

    province_years = sorted({_safe_int(row.get("年份")) for row in province_rows if _safe_int(row.get("年份")) is not None})
    city_years = sorted({_safe_int(row.get("年份")) for row in city_rows if _safe_int(row.get("年份")) is not None})

    return {
        "levels": [
            {"key": "province", "label": "省级预测"},
            {"key": "city", "label": "市级预测"},
        ],
        "targets": [
            {"key": "carbonIntensity", "label": "碳排放强度"},
        ],
        "scenarios": [
            {"key": key, "label": label, "sourceLabel": next(raw for raw, mapped in SCENARIO_NAME_MAP.items() if mapped == key)}
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
                "coverageNote": "省级样本基于迁移后的面板总表，全国值按省级样本均值计算。",
            },
            "city": {
                "historyStartYear": city_years[0] if city_years else None,
                "historyEndYear": city_years[-1] if city_years else None,
                "forecastStartYear": FUTURE_YEARS[0],
                "forecastEndYear": FUTURE_YEARS[-1],
                "coverageCount": sum(len(cities) for cities in cities_by_province.values()),
                "coverageNote": "市级样本基于迁移后的地级市面板总表，同省对比线按省内城市样本均值计算。",
            },
            "boundaryNotice": "2000-2024 为历史观测，2025-2027 为模型推演；情景区间不是统计置信区间。",
        },
    }


def get_predict_meta_payload() -> dict[str, Any]:
    return _predict_meta_cache()


def _get_default_city(province: str) -> str | None:
    cities_by_province = _predict_meta_cache()["citiesByProvince"]
    city_list = cities_by_province.get(province) or []
    return city_list[0] if city_list else None


def _build_entity_history(level: str, target: str, province: str, city: str | None) -> tuple[str, list[dict[str, Any]]]:
    rows = _load_panel_rows(level)
    if level == "province":
        if province == "全国":
            return "全国平均", _average_points(rows, target, "historyFieldProvince")
        entity_rows = [row for row in rows if row.get("省份") == province]
        points = [point for row in entity_rows if (point := _point_from_province_row(row, target)) is not None]
        points.sort(key=lambda item: item["year"])
        return province, points

    selected_city = city or _get_default_city(province)
    entity_rows = [row for row in rows if row.get("省份") == province and row.get("地级市") == selected_city]
    points = [point for row in entity_rows if (point := _point_from_city_row(row, target)) is not None]
    points.sort(key=lambda item: item["year"])
    return selected_city or "", points


def _build_compare_history(level: str, target: str, province: str) -> tuple[str, list[dict[str, Any]]]:
    rows = _load_panel_rows(level)
    if level == "province":
        return "全国平均", _average_points(rows, target, "historyFieldProvince")

    compare_rows = [row for row in rows if row.get("省份") == province]
    return f"{province}市级均值", _average_points(compare_rows, target, "historyFieldCity")


def _build_entity_scenarios(level: str, target: str, province: str, city: str | None) -> tuple[list[dict[str, Any]], list[str]]:
    rows = _load_scenario_rows(level, target)
    if not rows:
        return [], []

    if level == "province":
        if province == "全国":
            entity_rows = rows
        else:
            entity_rows = [row for row in rows if row.get("省份") == province]
    else:
        selected_city = city or _get_default_city(province)
        entity_rows = [row for row in rows if row.get("地级市") == selected_city]

    scenario_points: dict[str, list[dict[str, Any]]] = {}
    for row in entity_rows:
        scenario_key = SCENARIO_NAME_MAP.get(row.get("情景", ""))
        year = _safe_int(row.get("年份"))
        value = _safe_float(row.get("预测值"))
        if scenario_key is None or year not in FUTURE_YEARS or value is None:
            continue
        scenario_points.setdefault(scenario_key, []).append({"year": year, "value": _compact_number(value)})

    normalized = []
    for scenario_key, label in SCENARIO_LABELS.items():
        points = sorted(scenario_points.get(scenario_key, []), key=lambda item: item["year"])
        if not points:
            continue
        normalized.append({"key": scenario_key, "label": label, "points": points})

    return normalized, [item["key"] for item in normalized]


def _build_compare_future(level: str, target: str, province: str) -> dict[str, list[dict[str, Any]]]:
    rows = _load_scenario_rows(level, target)
    if not rows:
        return {}

    if level == "province":
        relevant_rows = rows
    else:
        city_to_province = _city_to_province_map()
        relevant_rows = [row for row in rows if city_to_province.get(row.get("地级市", "")) == province]

    scenario_groups: dict[str, list[dict[str, str]]] = {}
    for row in relevant_rows:
        scenario_key = SCENARIO_NAME_MAP.get(row.get("情景", ""))
        if not scenario_key:
            continue
        scenario_groups.setdefault(scenario_key, []).append(row)

    compare_future: dict[str, list[dict[str, Any]]] = {}
    for scenario_key, scenario_rows in scenario_groups.items():
        compare_future[scenario_key] = _average_simple_series(scenario_rows, "年份", "预测值")
        compare_future[scenario_key] = [point for point in compare_future[scenario_key] if point["year"] in FUTURE_YEARS]
    return compare_future


def _build_scenario_band(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, list[float]] = {year: [] for year in FUTURE_YEARS}
    for scenario in scenarios:
        for point in scenario["points"]:
            if point["year"] in by_year and point.get("value") is not None:
                by_year[point["year"]].append(float(point["value"]))

    band: list[dict[str, Any]] = []
    for year in FUTURE_YEARS:
        values = by_year[year]
        if not values:
            continue
        band.append(
            {
                "year": year,
                "min": _compact_number(min(values)),
                "max": _compact_number(max(values)),
            }
        )
    return band


def _default_source_notice(has_scenarios: bool) -> str:
    if has_scenarios:
        return "当前三情景结果来自仓库内离线预测输出；自定义模式仍使用页面参数推演。"
    return "暂无离线情景结果，前端仅可做自定义参数推演。"


def get_predict_data_payload(
    level: str,
    target: str,
    province: str | None = None,
    city: str | None = None,
) -> dict[str, Any]:
    if level not in {"province", "city"}:
        raise ValueError(f"不支持的预测层级: {level}")
    if target not in TARGETS:
        raise ValueError(f"不支持的预测目标: {target}")

    selected_province = (province or "全国").strip() or "全国"
    if level == "city" and selected_province == "全国":
        raise ValueError("市级预测必须提供省份")

    entity_label, history_series = _build_entity_history(level, target, selected_province, city)
    compare_label, compare_history = _build_compare_history(level, target, selected_province if level == "city" else "全国")
    scenarios, available_scenarios = _build_entity_scenarios(level, target, selected_province, city)
    compare_future = _build_compare_future(level, target, selected_province if level == "city" else "全国")
    coefficients, weight_type = _build_frontend_coefficients(level, target)
    meta = _predict_meta_cache()
    sample_meta = meta["sampleMeta"][level]

    return {
        "level": level,
        "target": target,
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
        "coefficients": coefficients,
        "sampleMeta": {
            **sample_meta,
            "boundaryNotice": meta["sampleMeta"]["boundaryNotice"],
        },
        "sourceNotice": _default_source_notice(bool(available_scenarios)),
        "weightType": weight_type,
        "availableScenarios": available_scenarios,
    }
