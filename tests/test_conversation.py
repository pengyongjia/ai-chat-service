"""
多轮对话与会话管理测试
"""

import time

from app.db.conversation_store import ConversationStore


def test_create_session():
    """测试创建会话"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=3600, max_history=5)
    session_id = store.create_session()
    assert session_id.startswith("sess_")
    assert len(session_id) > 5


def test_add_and_get_messages():
    """测试添加和获取消息"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=3600, max_history=5)
    session_id = store.create_session()

    store.add_message(session_id, "user", "你好")
    store.add_message(session_id, "assistant", "您好，有什么可以帮您？")

    history = store.get_history(session_id)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[0].content == "你好"
    assert history[1].role == "assistant"


def test_history_limit():
    """测试历史消息数量限制"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=3600, max_history=2)
    session_id = store.create_session()

    for i in range(6):
        store.add_message(session_id, "user", f"问题{i}")
        store.add_message(session_id, "assistant", f"回答{i}")

    # max_history=2，保留最近 2 轮 = 4 条消息
    history = store.get_history(session_id)
    assert len(history) == 4
    assert history[-1].content == "回答5"


def test_clear_session():
    """测试清空会话"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=3600, max_history=5)
    session_id = store.create_session()
    store.add_message(session_id, "user", "测试")

    assert store.clear_session(session_id)
    assert len(store.get_history(session_id)) == 0


def test_delete_session():
    """测试删除会话"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=3600, max_history=5)
    session_id = store.create_session()
    store.add_message(session_id, "user", "测试")

    assert store.delete_session(session_id)
    assert len(store.get_history(session_id)) == 0


def test_cleanup_expired():
    """测试清理过期会话"""
    store = ConversationStore(persist_dir="./test_conversations", ttl_seconds=1, max_history=5)
    session_id = store.create_session()
    store.add_message(session_id, "user", "测试")

    time.sleep(1.1)
    count = store.cleanup_expired()
    assert count >= 1
    assert len(store.list_sessions()) == 0


def test_conversation_service_create_session(client):
    """测试 API 创建会话"""
    response = client.post("/v1/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "session_id" in data["data"]


def test_chat_with_session(client):
    """测试带 session_id 的对话"""
    # 创建会话
    response = client.post("/v1/chat/sessions")
    session_id = response.json()["data"]["session_id"]

    # 第一次提问
    response = client.post(
        "/v1/chat/ask",
        json={"question": "你好", "session_id": session_id},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["session_id"] == session_id

    # 获取历史
    response = client.get(f"/v1/chat/history/{session_id}")
    assert response.status_code == 200
    history = response.json()["data"]
    assert history["total"] == 2  # user + assistant


def test_clear_session_api(client):
    """测试清空会话 API"""
    response = client.post("/v1/chat/sessions")
    session_id = response.json()["data"]["session_id"]

    client.post("/v1/chat/ask", json={"question": "测试", "session_id": session_id})

    response = client.post("/v1/chat/clear", json={"session_id": session_id})
    assert response.status_code == 200

    response = client.get(f"/v1/chat/history/{session_id}")
    assert response.json()["data"]["total"] == 0
