"""
应用自定义异常
"""


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ConfigError(AppException):
    """配置错误"""

    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")


class LLMError(AppException):
    """大模型调用错误"""

    def __init__(self, message: str):
        super().__init__(message, code="LLM_ERROR")


class VectorStoreError(AppException):
    """向量数据库错误"""

    def __init__(self, message: str):
        super().__init__(message, code="VECTOR_STORE_ERROR")


class FAQNotFoundError(AppException):
    """FAQ 未找到"""

    def __init__(self, message: str = "未找到相关 FAQ"):
        super().__init__(message, code="FAQ_NOT_FOUND")
