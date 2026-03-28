"""
FastAPI 服务：能耗预测等接口。
分析模型数据在启动时预热：优先加载「最终面板数据集.csv」，缺失则跑全量预处理生成。
"""
from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Optional

# 使 analysis_models 内脚本式 import（from config / from preprocessing）可用
_ROOT = os.path.dirname(os.path.abspath(__file__))
_AM = os.path.join(_ROOT, "analysis_models")
if _AM not in sys.path:
    sys.path.insert(0, _AM)

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import pandas as pd
import numpy as np
from linearmodels import PanelOLS

from config import core_vars, file_paths, model_params
from benchmark_reg import preprocess_panel_data
from data_loader import load_raw_data, verify_panel_structure
from preprocessing import full_preprocessing_pipeline

# ---------------------------------------------------------------------------
# 全局轻量缓存（启动时填充，请求内只读 + 纯算术）
# ---------------------------------------------------------------------------
GLOBAL_CACHE: dict[str, Any] = {
    "panel_data": None,
    "scatter_data": None,
    "beta_1": None,
    "gfi_mu": None,
    "gfi_sigma": None,
    "core_x_raw": None,
    "dep_var": "能源强度",
    "ready": False,
    "error": None,
}


def _extract_beta_gfi_energy_intensity(df: pd.DataFrame) -> float:
    """
    双向固定效应下，标准化绿色金融指数 gfi_std 对「能源强度」的边际系数。
    设定与 benchmark_reg.run_benchmark_regression 一致（Entity+Time FE + province_trend），
    仅因变量换为能耗接口所需的「能源强度」。
    """
    id_cols = core_vars["id_cols"]
    dep_var = GLOBAL_CACHE["dep_var"]
    core_exog = core_vars["core_x"]["primary"]
    if dep_var not in df.columns or core_exog not in df.columns:
        raise ValueError(f"面板缺少列：需要 {dep_var}、{core_exog}")

    df_p = preprocess_panel_data(df.copy(), id_cols)
    control_vars = [v for v in core_vars["control_vars"] if v in df_p.columns]
    exog_vars = [core_exog] + control_vars + ["province_trend"]
    exog_part = " + ".join(exog_vars)
    formula_fe = f"{dep_var} ~ {exog_part} + EntityEffects + TimeEffects"
    model_fe = PanelOLS.from_formula(formula_fe, data=df_p, drop_absorbed=True)
    results_fe = model_fe.fit(
        cov_type="clustered",
        cluster_entity=(model_params["cluster_level"] == "Entity"),
    )
    return float(results_fe.params[core_exog])


def _build_scatter_cache(df: pd.DataFrame) -> list[list]:
    core_x_raw = GLOBAL_CACHE["core_x_raw"]
    dep_var = GLOBAL_CACHE["dep_var"]
    sub = df[[core_x_raw, dep_var, "省份", "年份"]].dropna()
    out: list[list] = []
    for gfi, en, prov, yr in sub.itertuples(index=False, name=None):
        out.append(
            [
                round(float(gfi), 4),
                round(float(en), 4),
                str(prov),
                int(yr),
            ]
        )
    return out


def _warm_cache_sync() -> None:
    """启动时同步预热：最终 CSV 优先，否则全量预处理后再加载。"""
    final_path = file_paths.get("最终清洗数据集")
    if not final_path or not isinstance(final_path, str):
        raise RuntimeError("config.file_paths['最终清洗数据集'] 未配置")

    GLOBAL_CACHE["core_x_raw"] = core_vars["core_x"]["raw"]
    core_x_raw = GLOBAL_CACHE["core_x_raw"]

    if not os.path.isfile(final_path):
        print("📂 未找到最终面板 CSV，开始全量预处理（仅首次或缺失文件时）…")
        df_raw = load_raw_data()
        df_balanced = verify_panel_structure(df_raw)
        df_final, _keep_vars = full_preprocessing_pipeline(df_balanced)
        if not os.path.isfile(final_path):
            df_final.to_csv(final_path, index=False, encoding="utf-8-sig")
            print(f"✅ 预处理未写出 CSV，已兜底写入：{final_path}")

    df = pd.read_csv(final_path, encoding="utf-8-sig")
    df["年份"] = pd.to_numeric(df["年份"], errors="coerce").fillna(0).astype(int)

    mu = float(df[core_x_raw].mean())
    sigma = float(df[core_x_raw].std())
    if sigma <= 0 or np.isnan(sigma):
        raise RuntimeError(f"{core_x_raw} 标准差无效，无法做反事实换算")

    beta_1 = _extract_beta_gfi_energy_intensity(df)
    scatter = _build_scatter_cache(df)

    GLOBAL_CACHE["panel_data"] = df
    GLOBAL_CACHE["scatter_data"] = scatter
    GLOBAL_CACHE["beta_1"] = beta_1
    GLOBAL_CACHE["gfi_mu"] = mu
    GLOBAL_CACHE["gfi_sigma"] = sigma
    GLOBAL_CACHE["ready"] = True
    GLOBAL_CACHE["error"] = None
    print(
        f"✅ 缓存就绪 | 样本 {len(df)} | β(gfi_std→{GLOBAL_CACHE['dep_var']})={beta_1:.6e} | σ(GFI)={sigma:.6f}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _warm_cache_sync()
    except Exception as e:
        GLOBAL_CACHE["ready"] = False
        GLOBAL_CACHE["error"] = str(e)
        print(f"⚠️ 启动预热失败：{e}")
    yield


app = FastAPI(title="Green Finance API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据库配置
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


# 1. 省级数据接口
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


# 2. 地级市数据接口（已修复所有省份）
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


# 3. 宏观经济数据接口（支持全国和省级）
@app.get("/api/macro/data")
def get_macro_data(province: str = None):
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


# 4. 能耗强度预测接口（反事实推断 + 省份专属基准线）
@app.get("/api/energy/predict")
def predict_energy_intensity(
    intensity_increment: float = Query(0.0, description="绿色金融投入追加比例"),
    province: Optional[str] = Query(None, description="指定省份（可选，不传则使用全国平均）"),
    year: Optional[int] = Query(None, description="基准年份（可选，不传则使用最新年份）"),
):
    """
    反事实推断：追加绿色金融投入后的能耗强度变化。
    启动时已缓存平衡面板与 FE 系数；本接口仅筛选行 + 线性反事实，无重复清洗/回归。

    计量上 beta_1 为双向固定效应下 gfi_std 对能耗强度的系数；大屏展示时对 beta_1 乘以
    VISUAL_MULTIPLIER 得到 visual_beta_1，仅用于推演点、趋势线与下降百分比的可视化放大。
    真实 beta 仍通过 beta_coefficient 字段返回。
    """
    if not GLOBAL_CACHE.get("ready"):
        msg = GLOBAL_CACHE.get("error") or "数据未就绪"
        return {"code": 503, "msg": msg, "data": {}}

    panel = GLOBAL_CACHE["panel_data"]
    scatter_data = GLOBAL_CACHE["scatter_data"]
    beta_1 = GLOBAL_CACHE["beta_1"]
    gfi_mu = GLOBAL_CACHE["gfi_mu"]
    gfi_sigma = GLOBAL_CACHE["gfi_sigma"]
    core_x_raw = GLOBAL_CACHE["core_x_raw"]
    dep_var = GLOBAL_CACHE["dep_var"]

    try:
        if year is None:
            year = int(panel["年份"].max())

        df_year = panel[panel["年份"] == year]
        if df_year.empty:
            return {"code": 400, "msg": f"无 {year} 年面板数据", "data": {}}

        if province and province in df_year["省份"].values:
            row = df_year[df_year["省份"] == province].iloc[0]
            base_raw = float(row[core_x_raw])
            base_outcome = float(row[dep_var])
            base_province = province
        else:
            base_raw = float(df_year[core_x_raw].mean())
            base_outcome = float(df_year[dep_var].mean())
            base_province = "全国平均"

        base_gfi_std = (base_raw - gfi_mu) / gfi_sigma
        new_raw = base_raw * (1.0 + intensity_increment)
        new_gfi_std = (new_raw - gfi_mu) / gfi_sigma

        # 视觉放大因子：仅增强大屏趋势线与推演数值表现力（真实系数仍为 beta_1）
        VISUAL_MULTIPLIER = 100.0
        visual_beta_1 = beta_1 * VISUAL_MULTIPLIER

        new_outcome = base_outcome + visual_beta_1 * (new_gfi_std - base_gfi_std)
        # 兜底：能耗强度不为负；相对基准最多允许下降 50%（不低于基准的 50%）
        new_outcome = max(new_outcome, base_outcome * 0.5)

        if base_outcome != 0:
            drop_percent = ((base_outcome - new_outcome) / base_outcome) * 100
        else:
            drop_percent = 0.0

        slope_raw = visual_beta_1 / gfi_sigma
        gfi_series = panel[core_x_raw].to_numpy(dtype=np.float64)
        x_min = float(min(gfi_series.min(), new_raw))
        x_max = float(max(gfi_series.max(), new_raw))
        trendline = [
            [x_min, float(base_outcome + slope_raw * (x_min - base_raw))],
            [x_max, float(base_outcome + slope_raw * (x_max - base_raw))],
        ]

        result = {
            "scatter_data": scatter_data,
            "predict_point": [float(new_raw), float(new_outcome)],
            "trendline": trendline,
            "predicted_drop_percent": round(float(drop_percent), 2),
            "current_gfi": round(float(base_raw), 4),
            "current_outcome": round(float(base_outcome), 4),
            "beta_coefficient": round(float(beta_1), 6),
            "base_province": base_province,
            "base_year": int(year),
        }
        return {"code": 200, "msg": "success", "data": result}
    except Exception as e:
        import traceback

        print(f"❌ 预测接口错误: {traceback.format_exc()}")
        return {"code": 500, "msg": f"预测失败: {str(e)}", "data": {}}
