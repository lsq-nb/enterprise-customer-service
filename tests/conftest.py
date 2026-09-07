"""
测试夹具
提供测试所需的公共 fixtures
"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_settings():
    """Mock 配置对象"""
    with patch('config.settings.settings') as mock:
        mock.openai_api_key = "test-api-key"
        mock.openai_base_url = "https://test.api.com/v1"
        mock.openai_model = "gpt-4o"
        mock.embedding_model = "text-embedding-3-small"
        mock.temperature = 0.3
        mock.max_tokens = 2048
        mock.top_p = 0.9
        mock.retrieval_top_k = 5
        mock.bm25_weight = 0.4
        mock.rerank_top_k = 3
        mock.chunk_size = 500
        mock.chunk_overlap = 50
        mock.chroma_collection = "test_knowledge"
        mock.chroma_persist_dir = "./data/knowledge/test_chroma"
        mock.knowledge_dir = "./data/knowledge"
        yield mock


@pytest.fixture
def mock_llm():
    """Mock LLM 客户端"""
    with patch('langchain_openai.ChatOpenAI') as mock:
        mock_instance = MagicMock()
        mock_instance.invoke.return_value = MagicMock(
            content='{"intent": "product_info", "confidence": 0.95, "reasoning": "测试"}'
        )
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_documents():
    """样本文档数据"""
    from langchain_core.documents import Document
    return [
        Document(
            page_content="XX Pro Max 旗舰手机，售价6999元起，支持100W快充。",
            metadata={"source": "sample.txt", "knowledge_type": "basic"},
        ),
        Document(
            page_content="退换货政策：七天无理由退货，十五天换货。",
            metadata={"source": "sample.txt", "knowledge_type": "professional"},
        ),
        Document(
            page_content="常见问题：手机进水不在保修范围内。",
            metadata={"source": "sample.txt", "knowledge_type": "faq"},
        ),
    ]


@pytest.fixture
def mock_knowledge_base(mock_settings):
    """Mock 知识库实例"""
    with patch('rag.knowledge_base.get_knowledge_base') as mock:
        kb = MagicMock()
        kb.retrieve.return_value = []
        kb.get_stats.return_value = {
            "basic": {"document_count": 10, "status": "active"},
            "professional": {"document_count": 5, "status": "active"},
            "faq": {"document_count": 20, "status": "active"},
        }
        mock.return_value = kb
        yield kb
