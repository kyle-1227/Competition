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



# 4. 能耗强度预测接口（反事实推断）
@app.get("/api/energy/predict")
def predict_energy_intensity(intensity_increment: float = Query(0.0, description="绿色金融投入追加比例")):
    """
    反事实推断：预测追加绿色金融投入后的能耗强度变化
    
    参数:
        intensity_increment: 绿色金融投入追加比例（0.2 表示追加 20%）
    
    返回:
        scatter_data: 历史散点数据 [[gfi, outcome], ...]
        predict_point: 预测点 [new_gfi, new_outcome]
        trendline: 趋势线 [[start_gfi, start_outcome], [end_gfi, end_outcome]]
        predicted_drop_percent: 预计能耗强度下降百分比
    """
    try:
        if panel_data is None:
            return {"code": 500, "msg": "数据未加载", "data": {}}
        
        # 获取最新年份数据
        latest_year = panel_data['年份'].max()
        latest_data = panel_data[panel_data['年份'] == latest_year].copy()
        
        core_x = core_vars['core_x']['raw']
        dep_var = '能源强度'
        
        # 准备散点数据（所有历史数据）
        valid_data = panel_data[[core_x, dep_var, '省份']].dropna()
        scatter_data = valid_data[[core_x, dep_var]].values.tolist()
        
        # 计算当前平均值
        current_gfi = latest_data[core_x].mean()
        current_outcome = latest_data[dep_var].mean()
        
        # 计算反事实预测
        new_gfi = current_gfi * (1 + intensity_increment)
        delta_gfi = new_gfi - current_gfi
        new_outcome = current_outcome + (beta_1 * delta_gfi)
        
        # 计算下降百分比
        if current_outcome != 0:
            drop_percent = ((current_outcome - new_outcome) / current_outcome) * 100
        else:
            drop_percent = 0.0
        
        # 计算趋势线（包含预测点的新拟合线）
        all_x = np.append(valid_data[core_x].values, new_gfi)
        all_y = np.append(valid_data[dep_var].values, new_outcome)
        
        # 重新计算趋势线
        n_new = len(all_x)
        slope_new = (n_new * np.sum(all_x * all_y) - np.sum(all_x) * np.sum(all_y)) / (n_new * np.sum(all_x**2) - np.sum(all_x)**2)
        intercept_new = (np.sum(all_y) - slope_new * np.sum(all_x)) / n_new
        
        x_min = float(np.min(all_x))
        x_max = float(np.max(all_x))
        trendline = [
            [x_min, float(slope_new * x_min + intercept_new)],
            [x_max, float(slope_new * x_max + intercept_new)]
        ]
        
        result = {
            "scatter_data": [[float(x), float(y)] for x, y in scatter_data],
            "predict_point": [float(new_gfi), float(new_outcome)],
            "trendline": trendline,
            "predicted_drop_percent": round(float(drop_percent), 2),
            "current_gfi": round(float(current_gfi), 4),
            "current_outcome": round(float(current_outcome), 4),
            "beta_coefficient": round(float(beta_1), 6)
        }
        
        return {"code": 200, "msg": "success", "data": result}
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"❌ 预测接口错误: {error_detail}")
        return {"code": 500, "msg": f"预测失败: {str(e)}", "data": {}}
