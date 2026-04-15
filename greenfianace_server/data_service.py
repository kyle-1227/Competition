from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv
import pymysql

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _db_config_from_env() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "green_finance"),
        "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    }


POOL = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=0,
    blocking=True,
    cursorclass=pymysql.cursors.DictCursor,
    **_db_config_from_env(),
)


def get_db_connection():
    try:
        return POOL.connection()
    except Exception as exc:  # pragma: no cover
        print(f"DB Error: {exc}")
        return None


def safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        result = float(value)
        if result != result:
            return 0.0
        return result
    except (TypeError, ValueError):
        return 0.0


def get_province_rows(year: int = 2024) -> list[dict[str, Any]] | None:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT province, year, score, greenCredit, greenInvest, greenInsurance,
                   greenBond, greenSupport, greenFund, greenEquity, carbonEmission,
                   energyConsume, gdp, did
            FROM province_green_finance
            WHERE year = %s AND province != '西藏自治区'
            """,
            (year,),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_city_rows(province: str, year: int = 2024) -> list[dict[str, Any]] | None:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT city, province, year, score, greenCredit, greenInvest, greenInsurance,
                   greenBond, greenSupport, greenFund, greenEquity
            FROM city_green_finance
            WHERE province = %s AND year = %s
            """,
            (province, year),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_city_carbon_rows(province: str, year: int = 2024) -> list[dict[str, Any]] | None:
    conn = get_db_connection()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT city,
                   province,
                   year,
                   city_code AS cityCode,
                   co2_emission AS carbonEmission,
                   ROUND(co2_emission / 10000, 2) AS carbonEmissionWanTon,
                   ROUND(gdp / 10000, 2) AS gdp
            FROM city_carbon_gdp
            WHERE province = %s AND year = %s
            ORDER BY co2_emission DESC, city ASC
            """,
            (province, year),
        )
        rows = cursor.fetchall()
        for row in rows:
            row["carbonEmission"] = safe_float(row.get("carbonEmission"))
            row["carbonEmissionWanTon"] = round(safe_float(row.get("carbonEmissionWanTon")), 2)
            row["gdp"] = round(safe_float(row.get("gdp")), 2)
        return rows
    finally:
        conn.close()


def get_macro_rows(province: Optional[str] = None) -> list[dict[str, Any]] | None:
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        if province and province != "全国":
            cursor.execute(
                """
                SELECT year, gdp, carbonEmission
                FROM province_green_finance
                WHERE province = %s
                ORDER BY year ASC
                """,
                (province,),
            )
        else:
            cursor.execute(
                """
                SELECT year, SUM(gdp) AS gdp, SUM(carbonEmission) AS carbonEmission
                FROM province_green_finance
                GROUP BY year
                ORDER BY year ASC
                """
            )

        rows = cursor.fetchall()
        for row in rows:
            if row.get("carbonEmission") is not None:
                row["carbonEmission"] = round(safe_float(row["carbonEmission"]) / 10000, 2)
        return rows
    finally:
        conn.close()


def _load_sdm_coef_pairs() -> tuple[dict[str, float], list[tuple[str, float]]]:
    conn = get_db_connection()
    if not conn:
        return {}, []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT parameter, value FROM sdm_coefficients ORDER BY id ASC")
        rows = cursor.fetchall()
    finally:
        conn.close()

    raw: dict[str, float] = {}
    ordered: list[tuple[str, float]] = []
    for row in rows:
        name = str(row["parameter"]).strip()
        raw[name] = float(row["value"])
        ordered.append((name, float(row["value"])))
    return raw, ordered


def _build_coefficients_for_frontend(raw: dict[str, float], ordered: list[tuple[str, float]]) -> dict[str, Any]:
    def pick(*names: str) -> float | None:
        for name in names:
            if name in raw:
                return float(raw[name])
        return None

    rho = pick("W_碳排放强度") or (ordered[1][1] if len(ordered) > 1 else 0.4882)
    core = pick("gfi_std") or (ordered[2][1] if len(ordered) > 2 else 0.1446)
    ln_pop = pick("ln_pop") or (ordered[3][1] if len(ordered) > 3 else 1.1873)
    energy = pick("能源强度") or (ordered[4][1] if len(ordered) > 4 else 1.251)
    mediator = pick("人均能源消费") or (ordered[5][1] if len(ordered) > 5 else -0.3284)
    spatial = pick("W_gfi_std") or (ordered[6][1] if len(ordered) > 6 else -0.0284)

    return {
        "core": core,
        "control": energy,
        "control_ln_pop": ln_pop,
        "policy": float(pick("DID") or pick("did") or 0.0),
        "spatial": spatial,
        "rho": rho,
        "mediator": mediator,
        "raw": raw,
    }


def get_predict_payload() -> dict[str, Any] | None:
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT province, year, carbon_intensity, gfi_std, ln_pop,
                   energy_intensity, energy_per_capita
            FROM province_panel_data
            ORDER BY province ASC, year ASC
            """
        )
        panel_rows = cursor.fetchall()

        cursor.execute(
            """
            SELECT year,
                   AVG(carbon_intensity) AS carbon_intensity,
                   AVG(gfi_std) AS gfi_std,
                   AVG(ln_pop) AS ln_pop,
                   AVG(energy_intensity) AS energy_intensity,
                   AVG(energy_per_capita) AS energy_per_capita
            FROM province_panel_data
            GROUP BY year
            ORDER BY year ASC
            """
        )
        national_rows = cursor.fetchall()
    finally:
        conn.close()

    history_data: dict[str, list[dict[str, Any]]] = {}
    for row in panel_rows:
        province = str(row["province"])
        history_data.setdefault(province, []).append(
            {
                "year": int(row["year"]),
                "value": safe_float(row["carbon_intensity"]),
                "gfi_std": safe_float(row["gfi_std"]),
                "ln_pop": safe_float(row["ln_pop"]),
                "energy_intensity": safe_float(row["energy_intensity"]),
                "energy_per_capita": safe_float(row["energy_per_capita"]),
            }
        )

    history_data["全国"] = [
        {
            "year": int(row["year"]),
            "value": safe_float(row["carbon_intensity"]),
            "gfi_std": safe_float(row["gfi_std"]),
            "ln_pop": safe_float(row["ln_pop"]),
            "energy_intensity": safe_float(row["energy_intensity"]),
            "energy_per_capita": safe_float(row["energy_per_capita"]),
        }
        for row in national_rows
    ]

    raw_coef, ordered_coef = _load_sdm_coef_pairs()
    return {
        "coefficients": _build_coefficients_for_frontend(raw_coef, ordered_coef),
        "historyData": history_data,
    }


def _macro_stats_row_to_pandas_shape(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "Unnamed: 0": row["variable_name"],
        "count": safe_float(row["count"]),
        "mean": safe_float(row["mean"]),
        "std": safe_float(row["std"]),
        "min": safe_float(row["min"]),
        "25%": safe_float(row["q25"]),
        "50%": safe_float(row["q50"]),
        "75%": safe_float(row["q75"]),
        "max": safe_float(row["max"]),
    }


def get_macro_stats_records() -> list[dict[str, Any]] | None:
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT variable_name, `count`, mean, std, `min`, q25, q50, q75, `max`
            FROM descriptive_statistics
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()
        return [_macro_stats_row_to_pandas_shape(row) for row in rows]
    finally:
        conn.close()
