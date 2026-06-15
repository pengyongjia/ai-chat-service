"""
真实 API 端到端测试脚本

用法：
    python scripts/test_real_api.py

本脚本使用项目根目录的 .env 配置，但会把向量数据库指向临时目录，
避免破坏已有数据。仅用于本地验证，不提交任何代码。
"""

import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
load_dotenv(Path(__file__).parent.parent / ".env")

# 把向量库指向临时目录，避免覆盖真实数据
TEST_CHROMA_DIR = "./chroma_db_real_test"
os.environ["CHROMA_PERSIST_DIR"] = TEST_CHROMA_DIR
os.environ["CONVERSATION_PERSIST_DIR"] = "./conversations_real_test"

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.db.vector_store import Chunk
from app.services.chat_service import ChatService
from app.services.conversation_service import conversation_service

SAMPLE_FAQS = [
    {
        "question": "什么是应有成本",
        "answer": "应有成本（Should Be Cost）是指基于合理设计、工艺和市场价格计算出的目标成本。",
    },
    {
        "question": "支持哪些文件格式",
        "answer": "系统支持 PDF、Word、Excel、CSV、Markdown、TXT 等常见格式。",
    },
    {
        "question": "如何联系客服",
        "answer": "拨打 400-xxx-xxxx 或发送邮件至 support@example.com。",
    },
]

SAMPLE_DOCUMENT = """
应有成本估算平台是一款面向制造业的 SaaS 产品。
核心功能包括：BOM 成本拆解、工艺路线估算、供应商报价管理、模具费用分摊等。
用户可以通过上传 Excel 报价单，系统自动识别材料、工序、工时，并生成成本分析报告。
系统支持多租户模式，不同企业之间的数据完全隔离。
AI 客服模块可以基于企业上传的产品手册和 FAQ 回答客户咨询。
"""


def clean_test_dirs():
    """清理测试目录"""
    for path in [TEST_CHROMA_DIR, "./conversations_real_test"]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
            except PermissionError:
                # Windows 下 chroma 的 sqlite 句柄可能未释放，忽略
                print(f"警告：无法删除 {path}，可能文件被占用")


def build_vector_store():
    """构建测试向量库"""
    print("正在构建测试向量库（调用真实 Embedding API）...")
    from app.db.vector_store import vector_store as store

    store.clear()
    store.add_faqs(SAMPLE_FAQS)

    chunks = []
    for i, para in enumerate(SAMPLE_DOCUMENT.strip().split("\n")):
        para = para.strip()
        if para:
            chunks.append(
                Chunk(
                    text=para,
                    source="产品手册.txt",
                    doc_type="document",
                    chunk_index=i,
                )
            )
    store.add_chunks(chunks)
    print(f"已导入 {len(SAMPLE_FAQS)} 条 FAQ，{len(chunks)} 个文档 chunks\n")
    return store


def check_config():
    """检查配置"""
    errors = []
    if not config.DEEPSEEK_API_KEY or "your" in config.DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY 未配置或无效")
    if (
        config.EMBEDDING_MODE != "api"
        or not config.EMBEDDING_API_KEY
        or "your" in config.EMBEDDING_API_KEY
    ):
        errors.append("EMBEDDING_MODE 必须设为 api 并配置有效 EMBEDDING_API_KEY")

    if errors:
        print("配置检查失败：")
        for e in errors:
            print(f"  - {e}")
        return False
    print("配置检查通过\n")
    return True


def test_faq_direct_hit():
    """测试 FAQ 直接命中"""
    print("=" * 60)
    print("测试 1: FAQ 直接命中")
    print("=" * 60)
    service = ChatService()
    result = service.answer("什么是应有成本")
    print("问题：什么是应有成本")
    print(f"来源：{result['source']}")
    print(f"置信度：{result['confidence']:.4f}")
    print(f"回答：{result['answer'][:200]}...")
    assert result["source"] == "faq", f"期望 source=faq，实际 {result['source']}"
    assert result["confidence"] >= config.FAQ_THRESHOLD_HIGH, "置信度应高于高阈值"
    print("[OK] FAQ 直接命中测试通过\n")


def test_llm_generation():
    """测试 LLM 生成"""
    print("=" * 60)
    print("测试 2: LLM 基于文档生成")
    print("=" * 60)
    service = ChatService()
    result = service.answer("这个平台有哪些核心功能")
    print("问题：这个平台有哪些核心功能")
    print(f"来源：{result['source']}")
    print(f"置信度：{result['confidence']:.4f}")
    print(f"回答：{result['answer'][:300]}...")
    assert result["source"] == "llm", f"期望 source=llm，实际 {result['source']}"
    print("[OK] LLM 生成测试通过\n")


def test_multi_turn():
    """测试多轮对话"""
    print("=" * 60)
    print("测试 3: 多轮对话")
    print("=" * 60)
    service = ChatService()
    session_id = conversation_service.create_session()["session_id"]
    print(f"创建会话：{session_id}")

    r1 = service.answer("什么是应有成本", session_id=session_id)
    print("Q1: 什么是应有成本")
    print(f"A1: {r1['answer'][:150]}...")

    r2 = service.answer("它适用于哪些行业", session_id=session_id)
    print("Q2: 它适用于哪些行业")
    print(f"A2: {r2['answer'][:300]}...")

    history = conversation_service.get_history(session_id)
    print(f"历史消息数：{len(history)}")
    assert len(history) >= 4, f"期望至少 4 条消息，实际 {len(history)}"
    print("[OK] 多轮对话测试通过\n")


def test_stream():
    """测试流式接口"""
    print("=" * 60)
    print("测试 4: 流式接口（SSE）")
    print("=" * 60)
    service = ChatService()

    events = list(service.answer_stream("这个平台有哪些核心功能"))
    print(f"事件数量：{len(events)}")

    # 找到 done 事件
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1, f"期望 1 个 done 事件，实际 {len(done_events)}"

    done = done_events[0]
    print(f"来源：{done.get('source')}")
    print(f"置信度：{done.get('confidence')}")

    # 合并 chunk
    chunks = [e.get("content", "") for e in events if e["type"] == "chunk"]
    full = "".join(chunks)
    print(f"流式输出总长度：{len(full)} 字符")
    assert len(full) > 0, "流式输出不应为空"
    assert full == done.get("answer"), "chunk 合并后应等于 done 中的 answer"

    print("[OK] 流式接口测试通过\n")


def main():
    clean_test_dirs()
    try:
        if not check_config():
            return

        # 初始化测试向量库
        build_vector_store()

        test_faq_direct_hit()
        test_llm_generation()
        test_multi_turn()
        test_stream()

        print("=" * 60)
        print("[OK] 所有真实 API 测试通过")
        print("=" * 60)
    finally:
        clean_test_dirs()


if __name__ == "__main__":
    main()
