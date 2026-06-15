"""
应用配置管理
支持环境变量覆盖，启动时自动校验必填项
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


class ConfigError(Exception):
    """配置错误"""

    pass


@dataclass
class Config:
    """应用配置类"""

    # DeepSeek 对话 API
    DEEPSEEK_API_KEY: str = field(default="")
    DEEPSEEK_BASE_URL: str = field(default="https://api.deepseek.com/v1")
    DEEPSEEK_MODEL: str = field(default="deepseek-chat")

    # Embedding 配置
    EMBEDDING_MODE: str = field(default="api")
    EMBEDDING_API_KEY: str = field(default="")
    EMBEDDING_API_URL: str = field(default="https://api.siliconflow.cn/v1")
    EMBEDDING_API_MODEL: str = field(default="BAAI/bge-large-zh-v1.5")

    # ChromaDB
    CHROMA_PERSIST_DIR: str = field(default="./chroma_db")

    # FAQ 匹配阈值
    FAQ_THRESHOLD_HIGH: float = field(default=0.75)
    FAQ_THRESHOLD_LOW: float = field(default=0.40)
    FAQ_TOP_K: int = field(default=3)

    # 第三阶段：检索优化开关
    ENABLE_RERANK: bool = field(default=True)
    ENABLE_HYBRID_SEARCH: bool = field(default=True)
    ENABLE_QUERY_REWRITE: bool = field(default=False)
    ENABLE_LLM_CONTEXT_COMPRESS: bool = field(default=False)

    # 重排序权重
    RERANK_VECTOR_WEIGHT: float = field(default=0.6)
    RERANK_KEYWORD_WEIGHT: float = field(default=0.3)
    RERANK_LENGTH_WEIGHT: float = field(default=0.1)

    # 上下文压缩参数
    CONTEXT_SIMILARITY_THRESHOLD: float = field(default=0.35)
    CONTEXT_MAX_CHUNK_LENGTH: int = field(default=600)

    # 应用配置
    APP_NAME: str = field(default="应有成本估算 AI 助手")
    APP_VERSION: str = field(default="0.1.0")
    APP_ENV: str = field(default="development")
    LOG_LEVEL: str = field(default="INFO")

    def __post_init__(self):
        """从环境变量加载配置"""
        for key in self.__dataclass_fields__:
            env_value = os.getenv(key)
            if env_value is not None:
                # 类型转换
                current_value = getattr(self, key)
                field_type = type(current_value)
                if field_type == bool:
                    setattr(self, key, env_value.lower() in ("true", "1", "yes"))
                elif field_type in (int,):
                    setattr(self, key, int(env_value))
                elif field_type in (float,):
                    setattr(self, key, float(env_value))
                else:
                    setattr(self, key, env_value)

    def validate(self) -> None:
        """
        校验配置有效性
        启动时调用，必填项缺失则抛出 ConfigError
        """
        errors = []

        if not self.DEEPSEEK_API_KEY:
            errors.append("DEEPSEEK_API_KEY 不能为空")

        if self.EMBEDDING_MODE == "api" and not self.EMBEDDING_API_KEY:
            errors.append("EMBEDDING_MODE=api 时，EMBEDDING_API_KEY 不能为空")

        if self.FAQ_THRESHOLD_HIGH <= self.FAQ_THRESHOLD_LOW:
            errors.append("FAQ_THRESHOLD_HIGH 必须大于 FAQ_THRESHOLD_LOW")

        if self.FAQ_TOP_K <= 0:
            errors.append("FAQ_TOP_K 必须大于 0")

        if errors:
            raise ConfigError("配置校验失败：\n" + "\n".join(f"  - {e}" for e in errors))


# 全局配置实例
# 注意：不在模块导入时验证配置，以便测试环境可以灵活导入
# 验证在 app.main 的 startup 事件中显式调用
config = Config()
