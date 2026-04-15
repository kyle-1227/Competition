from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from ai_agent import stream_chat_agent_events, stream_summary_agent_events
from ai_context import build_chat_messages, build_summary_messages
from ai_service import AiServiceError, request_deepseek_completion
from ai_types import AiChatRequest, AiSummaryRequest
from data_service import (
    get_city_rows,
    get_macro_rows,
    get_macro_stats_records,
    get_predict_payload,
    get_province_rows,
)

app = FastAPI(title="绿色金融碳减排可视化大屏 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/macro/data")
def get_macro_data(province: str | None = None):
    rows = get_macro_rows(province)
    if rows is None:
        return {"code": 500, "msg": "数据库连接失败", "data": []}
    return {"code": 200, "msg": "success", "data": rows}


@app.get("/api/dashboard/predict-data")
def get_predict_data():
    payload = get_predict_payload()
    if payload is None:
        return {"code": 500, "msg": "数据库连接失败", "data": None}
    return {"code": 200, "msg": "success", "data": payload}


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
