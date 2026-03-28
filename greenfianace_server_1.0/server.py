"""
绿色金融大屏：MySQL 省级/地级/宏观 + data/*.csv 仪表盘接口。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymysql

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

app = FastAPI(title="绿色金融碳减排可视化大屏 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# MySQL（与旧 main.py 一致）
# ---------------------------------------------------------------------------
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "123456",
    "db": "green_finance",
    "charset": "utf8mb4",
}


def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    except Exception:
        return None


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
# SDM 系数：CSV 行名 → 前端五维滑块 + rho（与 BizCarbonPrediction.vue 对齐）
# gfi_std→core；能源强度→control；W_gfi_std→spatial；W_碳排放强度→rho；
# DID 不在 SDM 系数表中时用 0；人均能源消耗→mediator（控制型替代）
# ---------------------------------------------------------------------------
def _load_sdm_coef_pairs() -> tuple[dict[str, float], list[tuple[str, float]]]:
    """返回 name->value 字典，以及文件行顺序列表（供行号回退）。"""
    path = DATA_DIR / "SDM_碳排放强度_系数.csv"
    text = path.read_text(encoding="utf-8-sig")
    raw: dict[str, float] = {}
    ordered: list[tuple[str, float]] = []
    for line in text.strip().splitlines()[1:]:
        parts = line.split(",", 1)
        if len(parts) != 2:
            continue
        name = parts[0].strip()
        try:
            v = float(parts[1].strip())
        except ValueError:
            continue
        raw[name] = v
        ordered.append((name, v))
    return raw, ordered


def _build_coefficients_for_frontend(raw: dict[str, float], ordered: list[tuple[str, float]]) -> dict[str, Any]:
    """
    映射说明：
    - core: gfi_std（绿色金融标准化）
    - control: 能源强度（主控制）
    - control_ln_pop: ln_pop（人口对数，供展示区间）
    - policy: 系数表中无 DID/Post，置 0（前端仍可做情景倍率）
    - spatial: W_gfi_std（空间滞后绿色金融）
    - rho: W_碳排放强度（空间滞后因变量，空间自回归）
    - mediator: 人均能源消耗（作中介/结构替代）
    """
    # 行序回退：与 data/SDM_碳排放强度_系数.csv 约定顺序一致
    # 0 Intercept, 1 W_碳排放强度, 2 gfi_std, 3 ln_pop, 4 能源强度, 5 人均能源消耗, 6 W_gfi_std, ...
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
    try:
        panel_path = DATA_DIR / "最终面板数据集.csv"
        df = pd.read_csv(panel_path, encoding="utf-8-sig")
        if "省份" not in df.columns or "年份" not in df.columns or "碳排放强度" not in df.columns:
            return {
                "code": 500,
                "msg": "最终面板数据集缺少列：省份、年份、碳排放强度",
                "data": None,
            }

        df = df.copy()
        df["年份"] = pd.to_numeric(df["年份"], errors="coerce").fillna(0).astype(int)
        df["碳排放强度"] = pd.to_numeric(df["碳排放强度"], errors="coerce")

        history_data: dict[str, list[dict[str, Any]]] = {}
        for province in df["省份"].dropna().unique():
            prov_df = df[df["省份"] == province].sort_values("年份")
            history_data[str(province)] = [
                {"year": int(row["年份"]), "value": float(row["碳排放强度"])}
                for _, row in prov_df.iterrows()
                if pd.notna(row["碳排放强度"])
            ]

        national = df.groupby("年份", as_index=False)["碳排放强度"].mean()
        national = national.sort_values("年份")
        history_data["全国"] = [
            {"year": int(row["年份"]), "value": float(row["碳排放强度"])}
            for _, row in national.iterrows()
            if pd.notna(row["碳排放强度"])
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
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": None}


@app.get("/api/dashboard/macro-stats")
def get_macro_stats():
    try:
        desc_path = DATA_DIR / "描述性统计.csv"
        desc_df = pd.read_csv(desc_path, encoding="utf-8-sig")
        records = json.loads(desc_df.to_json(orient="records", force_ascii=False))
        return {"code": 200, "msg": "success", "data": records}
    except Exception as e:
        return {"code": 500, "msg": str(e), "data": None}
