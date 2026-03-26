from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymysql

app = FastAPI()
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