"""
知识问答 Agent
基于 RAG 检索结果生成专业、准确的回答
"""
import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from config.prompts import RAG_ANSWER_PROMPT, CONTEXT_AUGMENT_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


class QA_agent:
    """
    知识问答 Agent

    职责：
    - 接收 RAG 检索结果
    - 结合对话历史生成专业回答
    - 约束回答质量和格式
    """

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        self.llm = llm or ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
            top_p=settings.top_p,
        )
        logger.info("知识问答 Agent 初始化完成")

    def answer(
        self,
        question: str,
        context_docs: list[Any],
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """
        基于 RAG 结果生成回答

        Args:
            question: 用户问题
            context_docs: RAG 检索到的文档列表
            conversation_history: 对话历史

        Returns:
            {answer: str, sources: list[str], confidence: float}
        """
        # 构建参考资料文本
        context_text = self._format_context(context_docs)

        # 构建对话历史
        history_text = self._format_history(conversation_history)

        # 调用 LLM 生成回答
        prompt = RAG_ANSWER_PROMPT.format(context=context_text, question=question)

        messages = [
            SystemMessage(content="你是一位专业的企业客服助手，请根据参考资料给出准确、友好的回答。"),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        answer = response.content.strip()

        # 提取引用来源
        sources = self._extract_sources(context_docs)

        # 计算置信度
        confidence = self._estimate_confidence(answer, context_text)

        logger.info(f"问答 Agent 生成回答，置信度: {confidence:.2f}")

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
        }

    def answer_with_history(
        self,
        question: str,
        context_docs: list[Any],
        conversation_history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """
        结合对话历史生成回答（多轮对话场景）
        """
        # 先澄清用户意图
        clarify_prompt = CONTEXT_AUGMENT_PROMPT.format(
            history=history_text,
            current_input=question,
        )

        clarify_response = self.llm.invoke([
            SystemMessage(content="请分析用户意图并补全省略信息。"),
            HumanMessage(content=clarify_prompt),
        ])

        clarified_input = question  # 默认使用原问题
        try:
            content = clarify_response.content.strip()
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                parsed = json.loads(match.group(1))
                clarified_input = parsed.get("clarified_input", question)
        except (json.JSONDecodeError, AttributeError):
            pass

        # 基于澄清后的输入生成回答
        return self.answer(clarified_input, context_docs, conversation_history)

    def _format_context(self, docs: list[Any]) -> str:
        """将文档列表格式化为文本"""
        if not docs:
            return "（暂无参考资料）"
        lines = []
        for i, doc in enumerate(docs, 1):
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            source = doc.metadata.get("source", "未知来源") if hasattr(doc, "metadata") else "未知来源"
            lines.append(f"[来源{i} - {source}]\n{content}")
        return "\n\n".join(lines)

    def _format_history(self, history: list[dict[str, str]] | None) -> str:
        """格式化对话历史"""
        if not history:
            return "无历史记录"
        lines = []
        for turn in history[-5:]:  # 只取最近5轮
            role = turn.get("role", "user")
            content = turn.get("content", "")
            prefix = "用户" if role == "user" else "助手"
            lines.append(f"{prefix}: {content}")
        return "\n".join(lines) if lines else "无历史记录"

    @staticmethod
    def _extract_sources(docs: list[Any]) -> list[str]:
        """提取引用来源列表"""
        sources = []
        for doc in docs:
            if hasattr(doc, "metadata"):
                source = doc.metadata.get("source", "未知")
                if source not in sources:
                    sources.append(source)
        return sources

    @staticmethod
    def _estimate_confidence(answer: str, context: str) -> float:
        """
        基于回答和上下文的匹配度估算置信度
        """
        if not context or context == "（暂无参考资料）":
            return 0.3
        if len(answer) < 10:
            return 0.4
        # 简单启发式：回答越长且上下文越丰富，置信度越高
        context_length = len(context)
        answer_length = len(answer)
        confidence = min(0.95, 0.5 + (answer_length / 500) * 0.3 + (context_length / 2000) * 0.2)
        return round(confidence, 2)
