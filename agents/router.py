"""
意图识别路由器 Agent
判断用户输入意图类型，分流到对应处理流程
"""
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.prompts import INTENT_ROUTER_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


class IntentRouterAgent:
    """
    意图识别路由器 Agent

    职责：
    - 分析用户输入的意图类型
    - 输出结构化路由决策
    - 支持置信度评估和推理说明
    """

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0,
        )
        logger.info("意图路由器 Agent 初始化完成")

    def route(self, user_input: str) -> dict[str, Any]:
        """
        执行意图路由

        Args:
            user_input: 用户输入文本

        Returns:
            路由决策：{intent, confidence, reasoning}
        """
        logger.info(f"意图路由分析: {user_input[:50]}...")

        prompt = INTENT_ROUTER_PROMPT.format(user_input=user_input)

        messages = [
            SystemMessage(content="你是一个专业的意图识别专家，请严格按照要求返回 JSON。"),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()

        # 解析 JSON 响应
        result = self._parse_response(content)
        logger.info(f"意图路由结果: {result.get('intent')} (置信度: {result.get('confidence', 0):.2f})")
        return result

    def _parse_response(self, content: str) -> dict[str, Any]:
        """解析 LLM 返回的 JSON 响应"""
        try:
            # 尝试直接解析
            result = json.loads(content)
            if "intent" in result:
                return result
        except json.JSONDecodeError:
            pass

        # 尝试从 Markdown 代码块中提取 JSON
        try:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                result = json.loads(match.group(1))
                if "intent" in result:
                    return result
        except (json.JSONDecodeError, AttributeError):
            pass

        # 解析失败，返回默认值
        logger.warning(f"意图路由 JSON 解析失败，使用默认值。原始内容: {content[:200]}")
        return {
            "intent": "general_qa",
            "confidence": 0.5,
            "reasoning": "解析失败，默认归类为一般咨询",
        }
