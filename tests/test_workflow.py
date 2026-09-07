"""
工作流测试
测试 LangGraph 工作流各节点逻辑
"""
import pytest
from unittest.mock import MagicMock, patch


class TestIntentRouter:
    """意图路由器测试"""

    def test_route_product_query(self, mock_llm):
        """测试产品咨询意图路由"""
        from agents.router import IntentRouterAgent

        agent = IntentRouterAgent(llm=mock_llm)
        result = agent.route("这款手机多少钱？")

        assert result["intent"] == "product_info"
        assert result["confidence"] > 0
        assert "reasoning" in result

    def test_route_order_query(self, mock_llm):
        """测试订单查询意图路由"""
        from agents.router import IntentRouterAgent

        mock_llm.invoke.return_value = MagicMock(
            content='{"intent": "order_query", "confidence": 0.98, "reasoning": "用户询问订单信息"}'
        )
        agent = IntentRouterAgent(llm=mock_llm)
        result = agent.route("帮我查一下订单 ORD123456 的状态")

        assert result["intent"] == "order_query"
        assert result["confidence"] >= 0.9

    def test_route_chitchat(self, mock_llm):
        """测试闲聊意图路由"""
        from agents.router import IntentRouterAgent

        mock_llm.invoke.return_value = MagicMock(
            content='{"intent": "chitchat", "confidence": 0.99, "reasoning": "问候语"}'
        )
        agent = IntentRouterAgent(llm=mock_llm)
        result = agent.route("你好")

        assert result["intent"] == "chitchat"


class TestQAAgent:
    """知识问答 Agent 测试"""

    def test_answer_generation(self, mock_llm):
        """测试回答生成"""
        from agents.qa_agent import QA_agent

        mock_llm.invoke.return_value = MagicMock(
            content="这款手机支持100W快充，30分钟可充满80%电量。"
        )
        agent = QA_agent(llm=mock_llm)

        docs = [
            MagicMock(
                page_content="XX Pro Max 支持100W超级快充。",
                metadata={"source": "test.txt"},
            )
        ]
        result = agent.answer("手机支持多少瓦快充？", docs)

        assert "answer" in result
        assert result["confidence"] > 0

    def test_answer_with_no_context(self, mock_llm):
        """测试无上下文时的回答"""
        from agents.qa_agent import QA_agent

        mock_llm.invoke.return_value = MagicMock(content="抱歉，我没有找到相关信息。")
        agent = QA_agent(llm=mock_llm)
        result = agent.answer("你是谁？", [])

        assert "answer" in result


class TestToolAgent:
    """工具执行 Agent 测试"""

    def test_tool_decision_no_tool(self, mock_llm):
        """测试不需要工具的场景"""
        from agents.tool_agent import ToolAgent

        mock_llm.invoke.return_value = MagicMock(
            content='{"need_tool": false, "tools": [], "reasoning": "不需要工具"}'
        )
        agent = ToolAgent(llm=mock_llm)
        result = agent.decide_and_execute("你们的产品有哪些？")

        assert result["need_tool"] is False

    def test_tool_decision_with_tool(self, mock_llm):
        """测试需要工具调用的场景"""
        from agents.tool_agent import ToolAgent

        mock_llm.invoke.return_value = MagicMock(
            content='{"need_tool": true, "tools": [{"name": "query_order", "arguments": {"order_id": "ORD123"}}], "reasoning": "需要查询订单"}'
        )
        agent = ToolAgent(llm=mock_llm)
        result = agent.decide_and_execute("帮我查订单 ORD123")

        assert result["need_tool"] is True
        assert len(result["tool_results"]) > 0


class TestWorkflow:
    """工作流集成测试"""

    def test_build_workflow(self):
        """测试工作流构建"""
        from graph.workflow import build_workflow

        graph = build_workflow()
        assert graph is not None

    def test_state_initialization(self):
        """测试状态初始化"""
        from graph.state import AgentState

        state = AgentState()
        assert state.intent == "general_qa"
        assert state.tool_call_count == 0
        assert state.messages == []
