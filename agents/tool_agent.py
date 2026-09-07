"""
工具执行 Agent
负责工具调用决策和工具执行
"""
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.prompts import TOOL_CALL_PROMPT
from config.settings import settings
from tools.business_tools import (
    OrderQueryTool,
    ReturnExchangeTool,
    ProductRecommendTool,
    ComplaintRecordTool,
    AppointmentTool,
)

logger = logging.getLogger(__name__)


# 工具实例映射
TOOL_REGISTRY: dict[str, Any] = {
    "query_order": OrderQueryTool(),
    "query_return_policy": ReturnExchangeTool(),
    "recommend_product": ProductRecommendTool(),
    "submit_complaint": ComplaintRecordTool(),
    "make_appointment": AppointmentTool(),
}


class ToolAgent:
    """
    工具执行 Agent

    职责：
    - 判断是否需要调用工具
    - 选择正确的工具并构造参数
    - 执⼯工具调用
    - 返回工具执行结果
    """

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0,
        )
        self.tools = TOOL_REGISTRY
        self.tool_descriptions = self._build_tool_descriptions()
        logger.info(f"工具 Agent 初始化完成，已注册 {len(self.tools)} 个工具")

    def decide_and_execute(
        self,
        user_input: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        决策是否需要调用工具并执行

        Args:
            user_input: 用户输入
            conversation_history: 对话历史

        Returns:
            {"need_tool": bool, "tool_result": str, "tool_name": str | None}
        """
        logger.info(f"工具 Agent 决策: {user_input[:50]}...")

        # 构建对话历史文本
        history_text = "\n".join([
            f"{turn.get('role', 'user')}: {turn.get('content', '')}"
            for turn in (conversation_history or [])[-10:]
        ])

        # 调用 LLM 决策
        prompt = TOOL_CALL_PROMPT.format(
            tool_descriptions=self.tool_descriptions,
            conversation_history=history_text or "无",
            user_input=user_input,
        )

        messages = [
            SystemMessage(content="你是一个工具调用决策器，请根据用户需求判断是否需要调用工具。"),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()

        # 解析决策结果
        decision = self._parse_decision(content)
        logger.info(f"工具决策: need_tool={decision.get('need_tool')}, tools={decision.get('tools')}")

        if not decision.get("need_tool"):
            return {
                "need_tool": False,
                "tool_result": "",
                "tool_name": None,
                "reasoning": decision.get("reasoning", ""),
            }

        # 执行工具调用
        tool_results = []
        for tool_call in decision.get("tools", []):
            tool_name = tool_call.get("name", "")
            arguments = tool_call.get("arguments", {})
            result = self._execute_tool(tool_name, arguments)
            tool_results.append({
                "tool": tool_name,
                "result": result,
            })

        return {
            "need_tool": True,
            "tool_results": tool_results,
            "reasoning": decision.get("reasoning", ""),
        }

    def _execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """执行指定工具"""
        tool = self.tools.get(tool_name)
        if not tool:
            error_msg = f"未找到工具: {tool_name}，可用工具: {list(self.tools.keys())}"
            logger.warning(error_msg)
            return error_msg

        try:
            result = tool.execute(**arguments)
            logger.info(f"工具 {tool_name} 执行成功")
            return str(result)
        except Exception as exc:
            error_msg = f"工具 {tool_name} 执行失败: {exc}"
            logger.error(error_msg)
            return error_msg

    def _build_tool_descriptions(self) -> str:
        """构建工具描述文本（供 LLM 理解）"""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(
                f"- {name}: {tool.description}"
            )
        return "\n".join(descriptions)

    @staticmethod
    def _parse_decision(content: str) -> dict[str, Any]:
        """解析工具调用决策 JSON"""
        try:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                return json.loads(match.group(1))
            return json.loads(content)
        except (json.JSONDecodeError, AttributeError):
            logger.warning(f"工具决策解析失败: {content[:200]}")
            return {"need_tool": False, "tools": [], "reasoning": "解析失败"}
