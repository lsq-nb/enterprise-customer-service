"""
主管协调 Agent
协调多个子 Agent，管理对话流程
"""
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.prompts import SUPERVISOR_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    主管协调 Agent

    职责：
    - 根据当前对话状态决定下一步操作
    - 协调意图路由、知识问答、工具执行等子 Agent
    - 处理异常情况和人工转接
    """

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0,
        )
        logger.info("主管协调 Agent 初始化完成")

    def decide_next_step(
        self,
        user_input: str,
        intent: str,
        retrieved_docs_count: int,
        last_answer: str,
        tool_call_count: int,
    ) -> dict[str, Any]:
        """
        决定下一步操作

        Args:
            user_input: 用户输入
            intent: 已识别的意图
            retrieved_docs_count: 检索到的文档数
            last_answer: 上一轮回答
            tool_call_count: 已执行的工具调用次数

        Returns:
            {"next_agent": str, "reasoning": str}
        """
        logger.info(f"主管决策: intent={intent}, docs={retrieved_docs_count}, tools={tool_call_count}")

        prompt = SUPERVISOR_PROMPT.format(
            user_input=user_input,
            intent=intent,
            retrieved_docs_count=retrieved_docs_count,
            last_answer=last_answer[:200] if last_answer else "无",
            tool_call_count=tool_call_count,
        )

        messages = [
            SystemMessage(content="你是企业客服系统的主管协调员，负责调度各子Agent完成任务。"),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        content = response.content.strip()

        decision = self._parse_decision(content)
        logger.info(f"主管决策结果: next_agent={decision.get('next_agent')}")

        return decision

    def handle_escalation(
        self,
        user_input: str,
        context: dict[str, Any],
    ) -> str:
        """
        处理人工转接请求

        Args:
            user_input: 用户输入
            context: 对话上下文

        Returns:
            转接提示文本
        """
        logger.info("触发人工转接流程")

        # 构建转接摘要
        intent = context.get("intent", "未识别")
        tool_calls = context.get("tool_calls", [])
        last_answer = context.get("last_answer", "")

        transfer_message = f"""【人工客服转接】

尊敬的客户，您的问题需要人工客服进一步处理。

【问题摘要】
- 您的诉求: {user_input}
- 系统识别意图: {intent}
- 已尝试方案:
  {chr(10).join([f"  • {call.get('tool', '')}: {call.get('result', '')[:100]}" for call in tool_calls])}

【等待人工服务】
- 预计等待时间: 5-10分钟
- 服务热线: 400-XXX-XXXX
- 服务时间: 工作日 9:00-18:00

感谢您的耐心等候，我们的客服人员即将为您服务！
"""
        return transfer_message

    @staticmethod
    def _parse_decision(content: str) -> dict[str, Any]:
        """解析主管决策 JSON"""
        try:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                return json.loads(match.group(1))
            return json.loads(content)
        except (json.JSONDecodeError, AttributeError):
            logger.warning(f"主管决策解析失败: {content[:200]}")
            return {"next_agent": "qa_agent", "reasoning": "解析失败，默认使用问答Agent"}
