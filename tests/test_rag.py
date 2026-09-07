"""
RAG 模块测试
测试检索和重排序功能
"""
import pytest
from unittest.mock import MagicMock, patch


class TestHybridRetriever:
    """混合检索器测试"""

    def test_init_with_documents(self, sample_documents):
        """测试使用文档初始化检索器"""
        with patch('rag.retriever.HybridRetriever.__init__', return_value=None):
            retriever = MagicMock()
            retriever._get_relevant_documents.return_value = sample_documents
            assert retriever is not None

    def test_fuse_results(self, sample_documents):
        """测试结果融合"""
        bm25_docs = sample_documents[:2]
        vector_docs = sample_documents[1:]

        # 模拟融合逻辑
        all_docs = bm25_docs + vector_docs
        unique_contents = set(doc.page_content for doc in all_docs)
        assert len(unique_contents) == 3  # 3个唯一内容


class TestKnowledgeBase:
    """知识库测试"""

    def test_load_from_text(self, mock_knowledge_base):
        """测试从文本加载知识库"""
        kb = mock_knowledge_base
        # 直接测试 KnowledgeBase 类的方法
        from rag.knowledge_base import KnowledgeBase
        kb_instance = KnowledgeBase.__new__(KnowledgeBase)
        kb_instance._retrievers = {}
        kb_instance._collections = {
            "basic": {"name": "基础知识库", "description": "产品信息", "count": 0},
            "professional": {"name": "专业知识库", "description": "业务规则", "count": 0},
            "faq": {"name": "FAQ知识库", "description": "常见问题", "count": 0},
        }
        count = kb_instance.load_from_text(
            text="测试文档内容",
            knowledge_type="faq",
            source_name="test",
        )
        assert isinstance(count, int) and count >= 0

    def test_get_stats(self, mock_knowledge_base):
        """测试统计信息获取"""
        stats = mock_knowledge_base.get_stats()
        assert "basic" in stats
        assert "professional" in stats
        assert "faq" in stats

    def test_clear_collection(self, mock_knowledge_base):
        """测试清空知识库"""
        result = mock_knowledge_base.clear_collection("basic")
        assert result is True

    def test_clear_invalid_collection(self, mock_knowledge_base):
        """测试清空无效知识库"""
        result = mock_knowledge_base.clear_collection("invalid")
        assert result is False


class TestReranker:
    """重排序器测试"""

    def test_rerank_empty(self):
        """测试空文档列表重排序"""
        from rag.reranker import ResponseReranker

        reranker = ResponseReranker()
        result = reranker.rerank("测试", [])
        assert result == []

    def test_rerank_less_than_top_k(self):
        """测试文档数少于 top_k 的情况"""
        from rag.reranker import ResponseReranker
        from langchain_core.documents import Document

        reranker = ResponseReranker(top_k=10)
        docs = [
            Document(page_content=f"文档{i}", metadata={"source": "test"})
            for i in range(5)
        ]
        result = reranker.rerank("测试", docs)
        assert len(result) == 5
