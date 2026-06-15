"""
知识库接口测试
"""

import pytest


@pytest.fixture
def sample_txt_file(tmp_path):
    """创建测试用的 TXT 文件"""
    file_path = tmp_path / "test_doc.txt"
    file_path.write_text(
        "直接材料成本 = 材料用量 × 材料单价 - 废料回收量 × 废料单价。\n\n"
        "直接人工成本 = 人工费率 × 人工工时。",
        encoding="utf-8",
    )
    return file_path


def test_upload_txt_document(client, sample_txt_file):
    """测试上传 TXT 文档"""
    with open(sample_txt_file, "rb") as f:
        response = client.post(
            "/v1/knowledge/upload",
            files={"file": ("test_doc.txt", f, "text/plain")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True
    assert data["data"]["chunk_count"] > 0


def test_list_documents(client, sample_txt_file):
    """测试文档列表"""
    # 先上传一个文档
    with open(sample_txt_file, "rb") as f:
        client.post(
            "/v1/knowledge/upload",
            files={"file": ("test_doc.txt", f, "text/plain")},
        )

    response = client.get("/v1/knowledge/list")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["total"] >= 1


def test_knowledge_stats(client, sample_txt_file):
    """测试知识库统计"""
    with open(sample_txt_file, "rb") as f:
        client.post(
            "/v1/knowledge/upload",
            files={"file": ("test_doc.txt", f, "text/plain")},
        )

    response = client.get("/v1/knowledge/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "document_count" in data["data"]
    assert "faq_count" in data["data"]


def test_upload_unsupported_format(client):
    """测试上传不支持的文件格式"""
    response = client.post(
        "/v1/knowledge/upload",
        files={"file": ("test.exe", b"binary content", "application/octet-stream")},
    )
    assert response.status_code == 400


def test_delete_document(client, sample_txt_file):
    """测试删除文档"""
    # 上传
    with open(sample_txt_file, "rb") as f:
        client.post(
            "/v1/knowledge/upload",
            files={"file": ("delete_test.txt", f, "text/plain")},
        )

    # 删除
    response = client.post(
        "/v1/knowledge/delete",
        json={"filename": "delete_test.txt"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["success"] is True


def test_chat_with_document_context(client, sample_txt_file):
    """测试基于上传文档的问答上下文构建"""
    # 上传文档
    with open(sample_txt_file, "rb") as f:
        client.post(
            "/v1/knowledge/upload",
            files={"file": ("material_doc.txt", f, "text/plain")},
        )

    # 验证知识库统计中 document 数量增加
    response = client.get("/v1/knowledge/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["document_count"] > 0

    # 注意：实际 LLM 问答需要真实 API Key，单元测试中不直接调用
    # 问答逻辑已在 test_chat.py 中覆盖参数校验和健康检查
