"""
FastAPI 应用入口
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health
from app.api.v1 import api_router
from app.config import config
from app.core.exceptions import AppException
from app.core.logging import log
from app.core.responses import error_response

# 创建 FastAPI 应用
app = FastAPI(
    title=config.APP_NAME,
    description="基于 RAG + DeepSeek 的企业级 AI 客服服务",
    version=config.APP_VERSION,
)

# 允许跨域（门户网站直接调用）
# TODO: 生产环境应配置具体的域名，而不是 *
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理应用自定义异常"""
    log.error(f"业务异常 [{exc.code}]: {exc.message}")
    return JSONResponse(
        status_code=400,
        content=error_response(message=exc.message, code=400),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """处理未知异常"""
    log.exception("未捕获的全局异常")
    return JSONResponse(
        status_code=500,
        content=error_response(message="服务器内部错误", code=500),
    )


# 注册路由
app.include_router(api_router)
app.include_router(health.router)


@app.get("/")
async def root():
    """根路径：服务信息"""
    return {
        "service": config.APP_NAME,
        "version": config.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    # 启动前校验配置
    config.validate()
    log.info(f"🚀 {config.APP_NAME} v{config.APP_VERSION} 启动成功")
    log.info(f"环境: {config.APP_ENV}, Embedding 模式: {config.EMBEDDING_MODE}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    log.info(f"👋 {config.APP_NAME} 已关闭")
