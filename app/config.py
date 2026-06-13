import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # DeepSeek 对话 API
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Embedding 配置（可选升级）
    # mode: "local" | "api"
    # local = 本地字符串匹配（默认，零依赖）
    # api   = 调用 Embedding API（需配置下方 API Key）
    EMBEDDING_MODE = os.getenv("EMBEDDING_MODE", "local")
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_API_URL = os.getenv("EMBEDDING_API_URL", "")
    EMBEDDING_API_MODEL = os.getenv("EMBEDDING_API_MODEL", "text-embedding-3-small")

    # ChromaDB
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # FAQ 匹配
    FAQ_THRESHOLD_HIGH = float(os.getenv("FAQ_THRESHOLD_HIGH", "0.75"))   # 直接命中
    FAQ_THRESHOLD_LOW = float(os.getenv("FAQ_THRESHOLD_LOW", "0.50"))     # 半相关，调 DeepSeek
    FAQ_TOP_K = int(os.getenv("FAQ_TOP_K", "3"))


config = Config()
