"""
测试夹具
提供测试所需的公共 fixtures
"""
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_env():
    """自动设置测试环境变量，避免缺少 .env 文件时报错"""
    os.environ.setdefault("OPENAI_API_KEY", "test-key-for-ci")
    os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
    os.environ.setdefault("OPENAI_MODEL", "gpt-4o")
    os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")
    yield


@pytest.fixture
def mock_settings():
    """Mock 配置对象"""
    with patch('config.settings.get_settings') as mock:
        mock_instance = MagicMock()
        mock_instance.openai_api_key = "test-api-key"
        mock_instance.openai_base_url = "https://test.api.com/v1"
        mock_instance.openai_model = "gpt-4o"
        mock_instance.embedding_model = "text-embedding-3-small"
        mock_instance.temperature = 0.3
        mock_instance.max_tokens = 2048
        mock_instance.top_p = 0.9
        mock_instance.retrieval_top_k = 5
        mock_instance.bm25_weight = 0.4
        mock_instance.rerank_top_k = 3
        mock_instance.chunk_size = 500
        mock_instance.chunk_overlap = 50
        mock_instance.chroma_collection = "test_knowledge"
        mock_instance.chroma_persist_dir = "./data/knowledge/test_chroma"
        mock_instance.knowledge_dir = "./data/knowledge"
        mock.return_value = mock_instance
        yield mock_instance


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
        kb.clear_collection.return_value = True
        mock.return_value = kb
        yield kb
