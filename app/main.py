from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, faq

app = FastAPI(
    title="应有成本估算 AI 助手",
    description="基于 DeepSeek + RAG 的智能客服服务",
    version="0.1.0"
)

# 允许跨域（门户网站直接调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router)
app.include_router(faq.router)


@app.get("/")
async def root():
    return {
        "service": "应有成本估算 AI 助手",
        "version": "0.1.0",
        "docs": "/docs"
    }
