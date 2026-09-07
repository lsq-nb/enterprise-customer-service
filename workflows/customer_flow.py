"""
客户交互工作流封装
提供高层 API 接口
"""
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncIterator

from graph.workflow import compiled_graph
from graph.state import AgentState

logger = logging.getLogger(__name__)


class CustomerFlow:
    """
    客户交互工作流封装类

    提供完整的客户对话流程管理：
    - 单轮对话处理
    - 多轮对话状态维护
    - 流式响应支持
    """

    def __init__(self) -> None:
        self._conversations: dict[str, dict[str, Any]] = {}
        logger.info("客户交互工作流初始化完成")

    def process(
        self,
        user_input: str,
        conversation_id: str | None = None,
        user_id: str = "",
    ) -> dict[str, Any]:
        """
        处理单轮用户输入

        Args:
            user_input: 用户输入文本
            conversation_id: 会话ID（可选，自动生成）
            user_id: 用户标识

        Returns:
            包含 answer、intent、confidence 等字段的字典
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())[:8]

        # 初始化或获取会话状态
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "turn_count": 0,
            }

        conv = self._conversations[conversation_id]

        # 构建状态
        state = AgentState(
            messages=[user_input],
            conversation_id=conversation_id,
            user_id=user_id,
            created_at=datetime.now().isoformat(),
        )

        # 执行工作流
        result = compiled_graph.invoke(state)

        # 更新会话
        conv["messages"].append({"role": "user", "content": user_input})
        conv["messages"].append({"role": "assistant", "content": result["answer"]})
        conv["turn_count"] += 1

        logger.info(
            f"会话 {conversation_id} 处理完成，意图: {result['intent']}，"
            f"轮次: {conv['turn_count']}"
        )

        return {
            "conversation_id": conversation_id,
            "answer": result["answer"],
            "intent": result["intent"],
            "intent_confidence": result["intent_confidence"],
            "tool_call_count": result["tool_call_count"],
            "sources": result.get("answer_sources", []),
        }

    async def process_stream(
        self,
        user_input: str,
        conversation_id: str | None = None,
        user_id: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        """
        流式处理用户输入

        Args:
            user_input: 用户输入文本
            conversation_id: 会话ID
            user_id: 用户标识

        Yields:
            流式事件：{"type": str, "data": Any}
        """
        # 流式处理简化为单轮处理
        # 实际项目中可以使用 langgraph 的 stream 接口
        result = self.process(user_input, conversation_id, user_id)

        yield {"type": "start", "data": {"conversation_id": result["conversation_id"]}}
        yield {"type": "intent", "data": {"intent": result["intent"], "confidence": result["intent_confidence"]}}
        yield {"type": "answer", "data": {"answer": result["answer"]}}
        yield {"type": "end", "data": {"conversation_id": result["conversation_id"]}}

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """获取会话信息"""
        return self._conversations.get(conversation_id)

    def clear_conversation(self, conversation_id: str) -> bool:
        """清空会话"""
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    def list_conversations(self) -> list[dict[str, Any]]:
        """列出所有会话"""
        return [
            {
                "conversation_id": cid,
                "turn_count": conv["turn_count"],
                "created_at": conv["created_at"],
                "last_message": conv["messages"][-1]["content"] if conv["messages"] else "",
            }
            for cid, conv in self._conversations.items()
        ]
