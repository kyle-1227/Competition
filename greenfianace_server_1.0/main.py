from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import pandas as pd
import numpy as np
from analysis_models.data_loader import load_raw_data
from analysis_models.config import core_vars

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据和模型
try:
    panel_data = load_raw_data()
    # 计算基准回归系数（使用能源强度作为因变量）
    dep_var = '能源强度'
    core_x = core_vars['core_x']['raw']
    
    # 简单线性回归计算系数
    valid_data = panel_data[[core_x, dep_var]].dropna()
    X = valid_data[core_x].values
    Y = valid_data[dep_var].values
    
    # 计算回归系数 β1 (slope)
    n = len(X)
    beta_1 = (n * np.sum(X * Y) - np.sum(X) * np.sum(Y)) / (n * np.sum(X**2) - np.sum(X)**2)
    beta_0 = (np.sum(Y) - beta_1 * np.sum(X)) / n
    
    print(f"✅ 模型初始化成功 - 回归系数 β1: {beta_1:.6f}")
except Exception as e:
    print(f"⚠️ 模型初始化失败: {e}")
    panel_data = None
    beta_1 = -0.5  # 默认系数
    beta_0 = 1.0

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "123456",
    "db": "green_finance",
    "charset": "utf8mb4"
}


# 连接数据库
def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)
    except:
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
        # 查询指定省份的历年数据
        sql = """
        SELECT year, gdp, carbonEmission
        FROM province_green_finance
        WHERE province=%s
        ORDER BY year ASC
        """
        cursor.execute(sql, (province,))
    else:
        # 查询全国历年数据（各省求和）
        sql = """
        SELECT year, SUM(gdp) as gdp, SUM(carbonEmission) as carbonEmission
        FROM province_green_finance
        GROUP BY year
        ORDER BY year ASC
        """
        cursor.execute(sql)
    
    data = cursor.fetchall()
    conn.close()
    
    # 将碳排放从吨转换为万吨
    for row in data:
        if row.get('carbonEmission'):
            row['carbonEmission'] = round(row['carbonEmission'] / 10000, 2)
    
    return {"code": 200, "msg": "success", "data": data}



# 4. 能耗强度预测接口（反事实推断 + 省份专属基准线）
@app.get("/api/energy/predict")
def predict_energy_intensity(
    intensity_increment: float = Query(0.0, description="绿色金融投入追加比例"),
    province: str = Query(None, description="指定省份（可选，不传则使用全国平均）"),
    year: int = Query(None, description="基准年份（可选，不传则使用最新年份）")
):
    """
    反事实推断：预测追加绿色金融投入后的能耗强度变化
    支持省份专属基准线（固定效应）
    
    参数:
        intensity_increment: 绿色金融投入追加比例（0.2 表示追加 20%）
        province: 指定省份名称（如"浙江省"），不传则使用全国平均
        year: 基准年份，不传则使用最新年份
    
    返回:
        scatter_data: 历史散点数据 [[gfi, outcome, province, year], ...]
        predict_point: 预测点 [new_gfi, new_outcome]
        trendline: 专属趋势线 [[start_gfi, start_outcome], [end_gfi, end_outcome]]
        predicted_drop_percent: 预计能耗强度下降百分比
        base_province: 基准省份名称（"全国平均" 或具体省份）
    """
    try:
        if panel_data is None:
            return {"code": 500, "msg": "数据未加载", "data": {}}
        
        # 确定基准年份
        if year is None:
            year = panel_data['年份'].max()
        
        # 获取指定年份的数据
        df_current = panel_data[panel_data['年份'] == year].copy()
        
        core_x = core_vars['core_x']['raw']
        dep_var = '能源强度'
        
        # 准备散点数据（所有历史数据，包含省份和年份）
        valid_data = panel_data[[core_x, dep_var, '省份', '年份']].dropna()
        scatter_data = []
        for _, row in valid_data.iterrows():
            gfi_val = round(float(row[core_x]), 4)
            outcome_val = round(float(row[dep_var]), 4)
            prov_name = str(row['省份'])
            year_val = int(row['年份'])
            scatter_data.append([gfi_val, outcome_val, prov_name, year_val])
        
        # 【核心逻辑】确定基准点（推演起点）
        if province and province in df_current['省份'].values:
            # 省份专属基准点（固定效应）
            province_row = df_current[df_current['省份'] == province].iloc[0]
            base_gfi = float(province_row[core_x])
            base_outcome = float(province_row[dep_var])
            base_province = province
        else:
            # 全国平均基准点
            base_gfi = df_current[core_x].mean()
            base_outcome = df_current[dep_var].mean()
            base_province = "全国平均"
        
        # 计算反事实预测
        new_gfi = base_gfi * (1 + intensity_increment)
        delta_gfi = new_gfi - base_gfi
        new_outcome = base_outcome + (beta_1 * delta_gfi)
        
        # 计算下降百分比
        if base_outcome != 0:
            drop_percent = ((base_outcome - new_outcome) / base_outcome) * 100
        else:
            drop_percent = 0.0
        
        # 【固定效应】计算专属趋势线
        # 固定效应模型：各省斜率相同（beta_1）但截距不同
        # 专属截距 = 基准点的 outcome - beta_1 * 基准点的 gfi
        local_intercept = base_outcome - (beta_1 * base_gfi)
        
        # 计算趋势线的 X 轴范围（覆盖所有数据点 + 预测点）
        all_gfi_values = valid_data[core_x].values.tolist() + [new_gfi]
        x_min = float(min(all_gfi_values))
        x_max = float(max(all_gfi_values))
        
        # 使用专属截距和共同斜率生成趋势线
        trendline = [
            [x_min, float(beta_1 * x_min + local_intercept)],
            [x_max, float(beta_1 * x_max + local_intercept)]
        ]
        
        result = {
            "scatter_data": scatter_data,
            "predict_point": [float(new_gfi), float(new_outcome)],
            "trendline": trendline,
            "predicted_drop_percent": round(float(drop_percent), 2),
            "current_gfi": round(float(base_gfi), 4),
            "current_outcome": round(float(base_outcome), 4),
            "beta_coefficient": round(float(beta_1), 6),
            "base_province": base_province,
            "base_year": int(year)
        }
        
        return {"code": 200, "msg": "success", "data": result}
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 预测接口错误: {error_detail}")
        return {"code": 500, "msg": f"预测失败: {str(e)}", "data": {}}
