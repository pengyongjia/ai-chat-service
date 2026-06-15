"""
查询重写模块测试
"""

from app.core.query_rewriter import QueryRewriter


def test_query_rewriter_disabled():
    """测试关闭状态下返回原查询"""
    rewriter = QueryRewriter(enabled=False)
    assert rewriter.rewrite("  这个怎么弄  ") == "  这个怎么弄  "


def test_query_rewriter_empty_query():
    """测试空查询"""
    rewriter = QueryRewriter(enabled=True)
    assert rewriter.rewrite("") == ""


def test_query_rewriter_expand_disabled():
    """测试关闭状态下扩展返回原查询"""
    rewriter = QueryRewriter(enabled=False)
    assert rewriter.expand("测试") == ["测试"]


def test_parse_variants_json():
    """测试 JSON 变体解析"""
    rewriter = QueryRewriter(enabled=True)
    variants = rewriter._parse_variants('["变体1", "变体2"]')
    assert variants == ["变体1", "变体2"]


def test_parse_variants_lines():
    """测试行变体解析兜底"""
    rewriter = QueryRewriter(enabled=True)
    variants = rewriter._parse_variants("扩展查询一\n扩展查询二\n短")
    assert "扩展查询一" in variants
    assert "扩展查询二" in variants


def test_query_rewriter_mock(monkeypatch):
    """测试启用状态下的重写（mock LLM）"""
    rewriter = QueryRewriter(enabled=True)

    def mock_complete(*args, **kwargs):
        return '"如何进行成本核算"'

    monkeypatch.setattr(
        "app.core.query_rewriter.llm_client", type("M", (), {"complete": mock_complete})()
    )

    result = rewriter.rewrite("成本核算咋做")
    assert result == "如何进行成本核算"
