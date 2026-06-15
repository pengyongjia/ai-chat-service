"""
LLM 客户端封装
提供统一的对话补全接口，供查询重写、上下文压缩等模块复用
"""

from openai import OpenAI

from app.config import config
from app.core.exceptions import LLMError
from app.core.logging import log


class LLMClient:
    """
    通用 LLM 客户端

    基于 OpenAI 兼容接口，默认使用 DeepSeek 配置。
    支持延迟初始化，避免测试环境导入时失败。
    """

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None:
            if not config.DEEPSEEK_API_KEY:
                raise LLMError("DEEPSEEK_API_KEY 未配置")
            self._client = OpenAI(
                api_key=config.DEEPSEEK_API_KEY,
                base_url=config.DEEPSEEK_BASE_URL,
            )
        return self._client

    def complete(
        self,
        prompt: str = "",
        system_prompt: str | None = None,
        messages: list[dict] | None = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
    ) -> str:
        """
        调用 LLM 获取文本补全

        Args:
            prompt: 用户提示词（与 messages 二选一）
            system_prompt: 可选的系统提示词
            messages: 完整的 OpenAI 格式消息列表（与 prompt 二选一）
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本内容
        """
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        if not messages:
            raise LLMError("messages 或 prompt 至少提供一个")

        try:
            response = self.client.chat.completions.create(
                model=config.DEEPSEEK_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            log.debug(f"LLM 调用完成，生成 {len(content)} 字符")
            return content
        except Exception as e:
            log.error(f"LLM 调用失败: {e}")
            raise LLMError(f"大模型调用失败: {e}")


# 全局 LLM 客户端实例
llm_client = LLMClient()
