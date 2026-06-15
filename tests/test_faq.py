"""
FAQ 接口测试
"""


def test_add_faq(client):
    """测试添加 FAQ"""
    response = client.post(
        "/v1/faq/add",
        json={"question": "测试问题", "answer": "测试答案"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True


def test_seed_faqs_validation(client):
    """测试批量导入参数校验"""
    response = client.post("/v1/faq/seed", json={"faqs": []})
    assert response.status_code == 422


def test_count_after_add(client):
    """测试添加后数量增加"""
    # 先获取当前数量
    response = client.get("/v1/faq/count")
    before = response.json()["count"]

    # 添加一条
    client.post(
        "/v1/faq/add",
        json={"question": "数量测试", "answer": "测试答案"},
    )

    # 验证数量
    response = client.get("/v1/faq/count")
    after = response.json()["count"]
    assert after == before + 1
