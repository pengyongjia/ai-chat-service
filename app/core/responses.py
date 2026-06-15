"""
统一 API 响应格式
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ResponseModel(BaseModel):
    """统一响应模型"""

    code: int = Field(default=0, description="状态码，0 表示成功")
    message: str = Field(default="success", description="状态说明")
    data: Optional[Any] = Field(default=None, description="响应数据")


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data,
    }


def error_response(message: str, code: int = 500, data: Any = None) -> dict:
    """错误响应"""
    return {
        "code": code,
        "message": message,
        "data": data,
    }
