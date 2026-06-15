"""
测试 fixtures 和配置
"""

import os
import shutil

import pytest
from fastapi.testclient import TestClient

# 设置测试环境变量（避免启动时配置校验失败）
os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test-deepseek-key")
os.environ.setdefault("EMBEDDING_MODE", "local")
os.environ.setdefault("EMBEDDING_API_KEY", "sk-test-embedding-key")
os.environ.setdefault("CHROMA_PERSIST_DIR", "./chroma_db_test")
os.environ.setdefault("CONVERSATION_PERSIST_DIR", "./conversations_test")

# 必须在设置环境变量后导入 app
from app.main import app


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    # 清理测试目录
    for path in ["./chroma_db_test", "./conversations_test", "./test_conversations"]:
        if os.path.exists(path):
            shutil.rmtree(path)

    with TestClient(app) as c:
        yield c

    # 测试结束后再清理
    for path in ["./chroma_db_test", "./conversations_test", "./test_conversations"]:
        if os.path.exists(path):
            shutil.rmtree(path)
