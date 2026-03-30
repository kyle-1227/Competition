"""
绿色金融大屏：MySQL 省级/地级/宏观 + 仪表盘接口（预测与描述性统计均读库，不依赖运行时 CSV）。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from dbutils.pooled_db import PooledDB
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


DB_CONFIG = _db_config_from_env()

# mincached=0：不在 import 时预连，避免无 .env 时启动失败；有稳定库后可改为 2 预热
POOL = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=0,
    blocking=True,
    cursorclass=pymysql.cursors.DictCursor,
    **DB_CONFIG,
)

app = FastAPI(title="绿色金融碳减排可视化大屏 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MySQL（连接池：归还连接请调用 conn.close()）
# ---------------------------------------------------------------------------
def get_db_connection():
    try:
        return POOL.connection()
    except Exception as e:
        print(f"DB Error: {e}")
        return None


def _safe_float(x: Any) -> float:
    if x is None:
        return 0.0
    try:
        v = float(x)
        if v != v:
            return 0.0
        return v
    except (TypeError, ValueError):
        return 0.0


@app.get("/api/province/data")
def get_province_data(year: int = 2024):
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": []}

    cursor = conn.cursor()
    sql = """
    SELECT province,year,score,greenCredit,greenInvest,greenInsurance,
           greenBond,greenSupport,greenFund,greenEquity,carbonEmission,
           energyConsume,gdp,did
    FROM province_green_finance
    WHERE year=%s AND province!='西藏自治区'
    """
    cursor.execute(sql, (year,))
    data = cursor.fetchall()
    conn.close()
    return {"code": 200, "msg": "success", "data": data}


@app.get("/api/city/data")
def get_city_data(province: str, year: int = 2024):
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": []}

    cursor = conn.cursor()
    sql = """
    SELECT city,province,year,score,greenCredit,greenInvest,greenInsurance,
           greenBond,greenSupport,greenFund,greenEquity
    FROM city_green_finance
    WHERE province=%s AND year=%s
    """
    cursor.execute(sql, (province, year))
    data = cursor.fetchall()
    conn.close()

    if not data:
        return {"code": 200, "msg": f"暂未获取到{province}的地级市数据", "data": []}
    return {"code": 200, "msg": "success", "data": data}


@app.get("/api/macro/data")
def get_macro_data(province: Optional[str] = None):
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": []}

    cursor = conn.cursor()

    if province and province != "全国":
        sql = """
        SELECT year, gdp, carbonEmission
        FROM province_green_finance
        WHERE province=%s
        ORDER BY year ASC
        """
        cursor.execute(sql, (province,))
    else:
        sql = """
        SELECT year, SUM(gdp) as gdp, SUM(carbonEmission) as carbonEmission
        FROM province_green_finance
        GROUP BY year
        ORDER BY year ASC
        """
        cursor.execute(sql)

    data = cursor.fetchall()
    conn.close()

    for row in data:
        if row.get("carbonEmission"):
            row["carbonEmission"] = round(row["carbonEmission"] / 10000, 2)

    return {"code": 200, "msg": "success", "data": data}


# ---------------------------------------------------------------------------
# SDM 系数：sdm_coefficients → 前端五维滑块 + rho（与 BizCarbonPrediction.vue 对齐）
# ---------------------------------------------------------------------------
def _load_sdm_coef_pairs() -> tuple[dict[str, float], list[tuple[str, float]]]:
    conn = get_db_connection()
    if not conn:
        return {}, []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT parameter, value FROM sdm_coefficients ORDER BY id ASC"
        )
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
        for n in names:
            if n in raw:
                return float(raw[n])
        return None

    rho = pick("W_碳排放强度") or (ordered[1][1] if len(ordered) > 1 else 0.4882)
    core = pick("gfi_std") or (ordered[2][1] if len(ordered) > 2 else 0.1446)
    ln_pop = pick("ln_pop") or (ordered[3][1] if len(ordered) > 3 else 1.1873)
    energy = pick("能源强度") or (ordered[4][1] if len(ordered) > 4 else 1.251)
    mediator = pick("人均能源消耗") or (ordered[5][1] if len(ordered) > 5 else -0.3284)
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


@app.get("/api/dashboard/predict-data")
def get_predict_data():
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": None}

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
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": None}
    finally:
        conn.close()

    history_data: dict[str, list[dict[str, Any]]] = {}

    for row in panel_rows:
        prov = str(row["province"])
        pt = {
            "year": int(row["year"]),
            "value": _safe_float(row["carbon_intensity"]),
            "gfi_std": _safe_float(row["gfi_std"]),
            "ln_pop": _safe_float(row["ln_pop"]),
            "energy_intensity": _safe_float(row["energy_intensity"]),
            "energy_per_capita": _safe_float(row["energy_per_capita"]),
        }
        history_data.setdefault(prov, []).append(pt)

    history_data["全国"] = [
        {
            "year": int(row["year"]),
            "value": _safe_float(row["carbon_intensity"]),
            "gfi_std": _safe_float(row["gfi_std"]),
            "ln_pop": _safe_float(row["ln_pop"]),
            "energy_intensity": _safe_float(row["energy_intensity"]),
            "energy_per_capita": _safe_float(row["energy_per_capita"]),
        }
        for row in national_rows
    ]

    raw_coef, ordered_coef = _load_sdm_coef_pairs()
    coefficients = _build_coefficients_for_frontend(raw_coef, ordered_coef)

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "coefficients": coefficients,
            "historyData": history_data,
        },
    }


def _macro_stats_row_to_pandas_shape(row: dict[str, Any]) -> dict[str, Any]:
    """与 pandas read_csv(描述性统计.csv).to_json(orient='records') 键名一致。"""
    return {
        "Unnamed: 0": row["variable_name"],
        "count": _safe_float(row["count"]),
        "mean": _safe_float(row["mean"]),
        "std": _safe_float(row["std"]),
        "min": _safe_float(row["min"]),
        "25%": _safe_float(row["q25"]),
        "50%": _safe_float(row["q50"]),
        "75%": _safe_float(row["q75"]),
        "max": _safe_float(row["max"]),
    }


@app.get("/api/dashboard/macro-stats")
def get_macro_stats():
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": None}

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
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": None}
    finally:
        conn.close()

    records = [_macro_stats_row_to_pandas_shape(r) for r in rows]
    return {"code": 200, "msg": "success", "data": records}
