from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ai_agent import stream_chat_agent_events, stream_summary_agent_events
from ai_context import build_chat_messages, build_summary_messages, build_tooltip_messages
from ai_service import AiServiceError, request_deepseek_completion
from ai_types import AiChatRequest, AiSummaryRequest, AiTooltipRequest
from data_service import (
    get_city_carbon_rows,
    get_city_rows,
    get_db_connection,
    get_macro_stats_records,
    get_province_rows,
    safe_float,
)
from predict_results_service import get_predict_data_payload, get_predict_meta_payload

app = FastAPI(title="绿色金融碳减排可视化大屏 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.get("/api/city-carbon/data")
def get_city_carbon_data(province: str, year: int = 2024):
    rows = get_city_carbon_rows(province, year)
    if rows is None:
        return {"code": 500, "msg": "数据库连接失败", "data": None}

    total_carbon = round(sum(safe_float(row.get("carbonEmission")) for row in rows), 2)
    total_wan_ton = round(sum(safe_float(row.get("carbonEmissionWanTon")) for row in rows), 2)
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "province": province,
            "year": year,
            "cityCount": len(rows),
            "carbonEmission": total_carbon,
            "carbonEmissionWanTon": total_wan_ton,
            "rows": rows,
        },
    }


@app.get("/api/province/data")
def get_province_data(year: int = 2024):
    rows = get_province_rows(year)
    if rows is None:
        return {"code": 500, "msg": "数据库连接失败", "data": []}
    return {"code": 200, "msg": "success", "data": rows}


@app.get("/api/city/data")
def get_city_data(province: str, year: int = 2024):
    rows = get_city_rows(province, year)
    if rows is None:
        return {"code": 500, "msg": "数据库连接失败", "data": []}
    if not rows:
        return {"code": 200, "msg": f"暂未获取到 {province} 的地级市数据", "data": []}
    return {"code": 200, "msg": "success", "data": rows}


@app.get("/api/macro/cities")
def get_macro_cities(province: Optional[str] = None):
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": []}

    try:
        cursor = conn.cursor()
        if province and province != "全国":
            cursor.execute(
                """
                SELECT DISTINCT province, city
                FROM city_carbon_gdp
                WHERE province=%s
                ORDER BY city ASC
                """,
                (province,),
            )
        else:
            cursor.execute(
                """
                SELECT DISTINCT province, city
                FROM city_carbon_gdp
                ORDER BY province ASC, city ASC
                """
            )
        data = cursor.fetchall()
        return {"code": 200, "msg": "success", "data": data}
    except Exception as exc:
        return {"code": 500, "msg": f"宏观城市列表查询失败: {exc}", "data": []}
    finally:
        conn.close()


@app.get("/api/macro/data")
def get_macro_data(province: Optional[str] = None, city: Optional[str] = None):
    conn = get_db_connection()
    if not conn:
        return {"code": 500, "msg": "数据库连接失败", "data": []}

    try:
        cursor = conn.cursor()
        carbon_needs_wanton = True
        if city:
            carbon_needs_wanton = False
            if province and province != "全国":
                cursor.execute(
                    """
                    SELECT year, gdp / 10000 AS gdp, co2_emission / 10000 AS carbonEmission
                    FROM city_carbon_gdp
                    WHERE province=%s AND city=%s
                    ORDER BY year ASC
                    """,
                    (province, city),
                )
            else:
                cursor.execute(
                    """
                    SELECT year, gdp / 10000 AS gdp, co2_emission / 10000 AS carbonEmission
                    FROM city_carbon_gdp
                    WHERE city=%s
                    ORDER BY year ASC
                    """,
                    (city,),
                )
        elif province and province != "全国":
            cursor.execute(
                """
                SELECT year, gdp, carbonEmission
                FROM province_green_finance
                WHERE province=%s
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

        data = cursor.fetchall()
        for row in data:
            if row.get("carbonEmission") is not None:
                if carbon_needs_wanton:
                    row["carbonEmission"] = round(safe_float(row["carbonEmission"]) / 10000, 2)
                else:
                    row["carbonEmission"] = round(safe_float(row["carbonEmission"]), 2)
            if row.get("gdp") is not None:
                row["gdp"] = round(safe_float(row["gdp"]), 2)

        return {"code": 200, "msg": "success", "data": data}
    except Exception as exc:
        return {"code": 500, "msg": f"宏观时间序列查询失败: {exc}", "data": []}
    finally:
        conn.close()


@app.get("/api/dashboard/predict-meta")
def get_predict_meta():
    try:
        payload = get_predict_meta_payload()
        return {"code": 200, "msg": "success", "data": payload}
    except Exception as exc:
        return {"code": 500, "msg": f"预测元数据读取失败: {exc}", "data": None}


@app.get("/api/dashboard/predict-data")
def get_predict_data(
    level: str = "province",
    target: str = "carbonIntensity",
    province: Optional[str] = None,
    city: Optional[str] = None,
):
    try:
        payload = get_predict_data_payload(level=level, target=target, province=province, city=city)
        return {"code": 200, "msg": "success", "data": payload}
    except ValueError as exc:
        return {"code": 400, "msg": str(exc), "data": None}
    except Exception as exc:
        return {"code": 500, "msg": f"预测结果读取失败: {exc}", "data": None}


@app.get("/api/dashboard/macro-stats")
def get_macro_stats():
    records = get_macro_stats_records()
    if records is None:
        return {"code": 500, "msg": "数据库连接失败", "data": None}
    return {"code": 200, "msg": "success", "data": records}


@app.post("/api/ai/chat")
def ai_chat(payload: AiChatRequest):
    try:
        result = request_deepseek_completion(
            build_chat_messages(payload),
            temperature=0.3,
        )
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "content": result["content"],
                "model": result["model"],
                "kind": "chat",
            },
        }
    except AiServiceError as exc:
        return {"code": 500, "msg": str(exc), "data": None}
    except Exception as exc:  # pragma: no cover
        return {"code": 500, "msg": f"AI 聊天调用失败: {exc}", "data": None}


@app.post("/api/ai/summary")
def ai_summary(payload: AiSummaryRequest):
    try:
        result = request_deepseek_completion(
            build_summary_messages(payload),
            temperature=0.4,
        )
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "content": result["content"],
                "model": result["model"],
                "kind": "summary",
            },
        }
    except AiServiceError as exc:
        return {"code": 500, "msg": str(exc), "data": None}
    except Exception as exc:  # pragma: no cover
        return {"code": 500, "msg": f"AI 总结调用失败: {exc}", "data": None}


@app.post("/api/ai/tooltip")
def ai_tooltip(payload: AiTooltipRequest):
    try:
        result = request_deepseek_completion(
            build_tooltip_messages(payload),
            temperature=0.2,
        )
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "content": result["content"],
                "model": result["model"],
                "kind": "tooltip",
            },
        }
    except AiServiceError as exc:
        return {"code": 500, "msg": str(exc), "data": None}
    except Exception as exc:  # pragma: no cover
        return {"code": 500, "msg": f"AI Tooltip 调用失败: {exc}", "data": None}


@app.post("/api/ai/chat/stream")
def ai_chat_stream(payload: AiChatRequest):
    return StreamingResponse(
        stream_chat_agent_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/ai/summary/stream")
def ai_summary_stream(payload: AiSummaryRequest):
    return StreamingResponse(
        stream_summary_agent_events(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
