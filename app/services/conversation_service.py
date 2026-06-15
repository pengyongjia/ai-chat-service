"""
会话服务层
处理多轮对话的会话创建、历史管理、上下文构建等业务逻辑
"""

from app.config import config
from app.db.conversation_store import Message, conversation_store


class ConversationService:
    """会话服务"""

    def create_session(self) -> dict:
        """创建新会话"""
        session_id = conversation_store.create_session()
        return {
            "session_id": session_id,
            "created_at": (
                conversation_store.get_history(session_id, limit=1)[0].timestamp
                if conversation_store.get_history(session_id, limit=1)
                else ""
            ),
        }

    def add_user_message(self, session_id: str, question: str):
        """添加用户消息"""
        if session_id and config.ENABLE_CONVERSATION:
            conversation_store.add_message(session_id, "user", question)

    def add_assistant_message(self, session_id: str, answer: str):
        """添加助手消息"""
        if session_id and config.ENABLE_CONVERSATION:
            conversation_store.add_message(session_id, "assistant", answer)

    def get_history(self, session_id: str, limit: int | None = None) -> list[Message]:
        """
        获取会话历史

        Args:
            session_id: 会话 ID
            limit: 限制返回最近 N 条

        Returns:
            消息列表
        """
        if not session_id or not config.ENABLE_CONVERSATION:
            return []

        return conversation_store.get_history(
            session_id,
            include_system=False,
            limit=limit or config.SESSION_MAX_HISTORY * 2,
        )

    def build_llm_messages(
        self,
        system_prompt: str,
        question: str,
        session_id: str | None = None,
    ) -> list[dict]:
        """
        构建给 LLM 的消息列表

        Args:
            system_prompt: 系统提示词
            question: 当前用户问题
            session_id: 会话 ID

        Returns:
            OpenAI 格式的 messages 列表
        """
        messages = [{"role": "system", "content": system_prompt}]

        if session_id and config.ENABLE_CONVERSATION:
            history = self.get_history(session_id)
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": question})
        return messages

    def clear_session(self, session_id: str) -> bool:
        """清空会话历史"""
        if not session_id:
            return False
        return conversation_store.clear_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if not session_id:
            return False
        return conversation_store.delete_session(session_id)

    def list_sessions(self) -> list[dict]:
        """列出所有会话"""
        return conversation_store.list_sessions()

    def cleanup_expired(self) -> int:
        """清理过期会话"""
        return conversation_store.cleanup_expired()


# 全局会话服务实例
conversation_service = ConversationService()
