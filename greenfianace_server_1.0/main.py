"""兼容入口：与 uvicorn main:app 一致，实际应用定义在 server.py。"""
from server import app

__all__ = ["app"]
