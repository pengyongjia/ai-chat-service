"""
聊天接口测试
"""

import json


def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["status"] == "healthy"


def test_root_endpoint(client):
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()


def test_ask_question_validation(client):
    """测试问题参数校验"""
    # 空问题
    response = client.post("/v1/chat/ask", json={"question": ""})
    assert response.status_code == 422

    # 问题过长
    response = client.post("/v1/chat/ask", json={"question": "x" * 2001})
    assert response.status_code == 422


def test_faq_count(client):
    """测试 FAQ 数量接口"""
    response = client.get("/v1/faq/count")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert data["count"] >= 0


def _parse_sse(response_text: str) -> list[dict]:
    """解析 SSE 响应文本为事件列表"""
    events = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_stream_faq_direct_hit(client):
    """测试流式接口直接命中 FAQ"""
    # 先导入一条 FAQ
    client.post(
        "/v1/faq/seed",
        json={
            "faqs": [
                {
                    "question": "什么是应有成本",
                    "answer": "应有成本是指基于合理设计计算出的目标成本。",
                }
            ]
        },
    )

    response = client.post(
        "/v1/chat/stream",
        json={"question": "什么是应有成本"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    assert len(events) >= 2
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
    assert events[-1]["source"] == "faq"
    assert events[-1]["answer"] == "应有成本是指基于合理设计计算出的目标成本。"

    # 合并所有 chunk 内容应等于最终答案
    chunks = [e.get("content", "") for e in events if e.get("type") == "chunk"]
    assert "".join(chunks) == events[-1]["answer"]


def test_stream_validation(client):
    """测试流式接口参数校验"""
    response = client.post("/v1/chat/stream", json={"question": ""})
    assert response.status_code == 422


def test_stream_with_session(client):
    """测试流式接口携带 session_id"""
    # 创建会话
    resp = client.post("/v1/chat/sessions")
    session_id = resp.json()["data"]["session_id"]

    # 导入 FAQ
    client.post(
        "/v1/faq/seed",
        json={
            "faqs": [
                {
                    "question": "如何联系客服",
                    "answer": "拨打 400-xxx-xxxx 联系客服。",
                }
            ]
        },
    )

    response = client.post(
        "/v1/chat/stream",
        json={"question": "如何联系客服", "session_id": session_id},
    )
    assert response.status_code == 200
    events = _parse_sse(response.text)
    assert events[-1]["type"] == "done"
    assert events[-1]["source"] == "faq"

    # 验证会话历史已保存
    history_resp = client.get(f"/v1/chat/history/{session_id}")
    history = history_resp.json()["data"]["messages"]
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
