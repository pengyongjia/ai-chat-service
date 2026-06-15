"""
会话存储层
管理多轮对话的会话数据，支持内存 + JSON 文件持久化
"""

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from app.config import config
from app.core.logging import log


@dataclass
class Message:
    """单条消息"""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Conversation:
    """会话"""

    session_id: str
    messages: list[Message] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "messages": [asdict(m) for m in self.messages],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        return cls(
            session_id=data["session_id"],
            messages=[Message(**m) for m in data.get("messages", [])],
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class ConversationStore:
    """
    会话存储器

    特点：
    - 内存为主，JSON 文件持久化
    - 线程安全
    - 自动清理过期会话
    """

    def __init__(
        self,
        persist_dir: str = "./conversations",
        ttl_seconds: int | None = None,
        max_history: int = 10,
    ):
        """
        Args:
            persist_dir: 持久化目录
            ttl_seconds: 会话过期时间（秒），None 表示不过期
            max_history: 保留的最大历史消息轮数（user + assistant 算一轮）
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_history = max_history
        self._conversations: dict[str, Conversation] = {}
        self._lock = threading.RLock()

        self._load_from_disk()

    def create_session(self) -> str:
        """创建新会话"""
        session_id = f"sess_{uuid.uuid4().hex[:16]}"
        conversation = Conversation(session_id=session_id)

        with self._lock:
            self._conversations[session_id] = conversation
            self._persist(conversation)

        log.info(f"创建会话: {session_id}")
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """
        向会话添加消息

        Args:
            session_id: 会话 ID
            role: 角色
            content: 内容
        """
        if not session_id:
            return

        with self._lock:
            conversation = self._conversations.get(session_id)
            if not conversation:
                conversation = Conversation(session_id=session_id)
                self._conversations[session_id] = conversation

            conversation.messages.append(Message(role=role, content=content))
            conversation.updated_at = datetime.now().isoformat()

            # 限制历史长度，保留最近 max_history 轮
            self._trim_history(conversation)
            self._persist(conversation)

    def get_history(
        self,
        session_id: str,
        include_system: bool = False,
        limit: int | None = None,
    ) -> list[Message]:
        """
        获取会话历史消息

        Args:
            session_id: 会话 ID
            include_system: 是否包含 system 消息
            limit: 限制返回消息数量（最近 N 条）

        Returns:
            消息列表
        """
        if not session_id:
            return []

        with self._lock:
            conversation = self._conversations.get(session_id)
            if not conversation:
                return []

            messages = conversation.messages
            if not include_system:
                messages = [m for m in messages if m.role != "system"]

            if limit and limit > 0:
                messages = messages[-limit:]

            return messages

    def clear_session(self, session_id: str) -> bool:
        """清空指定会话"""
        if not session_id:
            return False

        with self._lock:
            conversation = self._conversations.get(session_id)
            if not conversation:
                return False

            conversation.messages = []
            conversation.updated_at = datetime.now().isoformat()
            self._persist(conversation)

        log.info(f"清空会话: {session_id}")
        return True

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if not session_id:
            return False

        with self._lock:
            if session_id not in self._conversations:
                return False

            del self._conversations[session_id]
            file_path = self._get_file_path(session_id)
            if file_path.exists():
                file_path.unlink()

        log.info(f"删除会话: {session_id}")
        return True

    def list_sessions(self) -> list[dict]:
        """列出所有会话"""
        with self._lock:
            return [
                {
                    "session_id": c.session_id,
                    "message_count": len(c.messages),
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in self._conversations.values()
            ]

    def cleanup_expired(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        if not self.ttl_seconds:
            return 0

        cutoff = datetime.now() - timedelta(seconds=self.ttl_seconds)
        expired_ids = []

        with self._lock:
            for session_id, conversation in self._conversations.items():
                updated_at = datetime.fromisoformat(conversation.updated_at)
                if updated_at < cutoff:
                    expired_ids.append(session_id)

            for session_id in expired_ids:
                del self._conversations[session_id]
                file_path = self._get_file_path(session_id)
                if file_path.exists():
                    file_path.unlink()

        if expired_ids:
            log.info(f"清理 {len(expired_ids)} 个过期会话")
        return len(expired_ids)

    def _trim_history(self, conversation: Conversation):
        """修剪历史消息，保留最近 max_history 轮"""
        if self.max_history <= 0:
            return

        # 统计轮数（user + assistant 为一轮）
        rounds = []
        current_round = []
        for msg in conversation.messages:
            current_round.append(msg)
            if msg.role == "assistant" and current_round:
                rounds.append(current_round)
                current_round = []
        if current_round:
            rounds.append(current_round)

        if len(rounds) <= self.max_history:
            return

        # 保留最近 max_history 轮
        kept = []
        for r in rounds[-self.max_history :]:
            kept.extend(r)
        conversation.messages = kept

    def _persist(self, conversation: Conversation):
        """持久化会话到文件"""
        file_path = self._get_file_path(conversation.session_id)
        try:
            # 运行时目录可能被外部删除，写入前确保存在
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(
                json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            log.error(f"会话持久化失败 {conversation.session_id}: {e}")

    def _load_from_disk(self):
        """从磁盘加载会话"""
        if not self.persist_dir.exists():
            return

        for file_path in self.persist_dir.glob("*.json"):
            try:
                data = json.loads(file_path.read_text(encoding="utf-8"))
                conversation = Conversation.from_dict(data)
                self._conversations[conversation.session_id] = conversation
            except Exception as e:
                log.warning(f"加载会话失败 {file_path}: {e}")

    def _get_file_path(self, session_id: str) -> Path:
        """获取会话文件路径"""
        return self.persist_dir / f"{session_id}.json"


# 全局会话存储实例
conversation_store = ConversationStore(
    persist_dir=config.CONVERSATION_PERSIST_DIR,
    ttl_seconds=config.SESSION_TTL_SECONDS,
    max_history=config.SESSION_MAX_HISTORY,
)
