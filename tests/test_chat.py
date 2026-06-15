"""
聊天接口测试
"""


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
