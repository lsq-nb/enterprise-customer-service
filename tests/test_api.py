"""
API 接口测试
测试 FastAPI 接口功能
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestAPIRoutes:
    """API 路由测试"""

    @pytest.fixture
    def client(self):
        """测试客户端"""
        from api.router import app
        with TestClient(app) as test_client:
            yield test_client

    def test_health_check(self, client):
        """测试健康检查接口"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    @patch('api.dependencies._workflow')
    def test_chat_endpoint(self, mock_workflow, client):
        """测试对话接口"""
        mock_workflow.process.return_value = {
            "conversation_id": "test123",
            "answer": "这是测试回答",
            "intent": "product_info",
            "intent_confidence": 0.95,
            "tool_call_count": 0,
            "sources": ["sample.txt"],
        }

        response = client.post(
            "/api/chat",
            json={"message": "你好", "conversation_id": "test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "这是测试回答"
        assert data["intent"] == "product_info"

    @patch('api.dependencies._workflow')
    def test_chat_stream_endpoint(self, mock_workflow, client):
        """测试流式对话接口"""
        mock_workflow.process.return_value = {
            "conversation_id": "test123",
            "answer": "测试流式回答",
            "intent": "general_qa",
            "intent_confidence": 0.9,
            "tool_call_count": 0,
            "sources": [],
        }

        response = client.post(
            "/api/chat/stream",
            json={"message": "测试流式", "stream": True},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_tools_list(self, client):
        """测试工具列表接口"""
        response = client.get("/api/tools/list")
        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert "total" in data
        assert data["total"] > 0

    @patch('api.router.get_knowledge_base')
    def test_knowledge_stats(self, mock_kb, client):
        """测试知识库统计接口"""
        mock_kb.return_value.get_stats.return_value = {
            "basic": {"document_count": 10, "status": "active"},
            "professional": {"document_count": 5, "status": "active"},
            "faq": {"document_count": 20, "status": "active"},
        }
        response = client.get("/api/knowledge/stats")
        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data

    def test_chat_missing_message(self, client):
        """测试缺少消息参数的情况"""
        response = client.post("/api/chat", json={})
        assert response.status_code == 422  # Pydantic 验证失败


class TestSchemas:
    """Pydantic 模型测试"""

    def test_chat_request_valid(self):
        """测试有效聊天请求"""
        from api.schemas import ChatRequest

        request = ChatRequest(message="你好")
        assert request.message == "你好"
        assert request.stream is False

    def test_chat_request_invalid(self):
        """测试无效聊天请求"""
        from api.schemas import ChatRequest

        with pytest.raises(Exception):
            ChatRequest(message="")  # 空消息

    def test_health_response(self):
        """测试健康检查响应"""
        from api.schemas import HealthResponse

        response = HealthResponse(status="healthy", timestamp="2024-01-01T00:00:00", version="1.0.0")
        assert response.status == "healthy"
