"""
LangGraph 主工作流图
基于状态机的多智能体协作流程
"""
import logging
from typing import Any

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agents.router import IntentRouterAgent
from agents.qa_agent import QA_agent
from agents.tool_agent import ToolAgent
from agents.supervisor import SupervisorAgent
from rag.knowledge_base import get_knowledge_base
from rag.reranker import ResponseReranker
from config.prompts import ANSWER_VERIFY_PROMPT
from config.settings import settings

logger = logging.getLogger(__name__)


def build_workflow() -> StateGraph:
    """
    构建 LangGraph 工作流状态图

    返回配置好的 StateGraph 实例，包含所有节点和边
    """
    # 初始化各 Agent
    router_agent = IntentRouterAgent()
    qa_agent_instance = QA_agent()
    tool_agent_instance = ToolAgent()
    supervisor_agent = SupervisorAgent()
    reranker = ResponseReranker()
    knowledge_base = get_knowledge_base()

    # 创建状态图
    graph = StateGraph(AgentState)

    # ────────────────────────────────────────────
    # 定义节点函数
    # ────────────────────────────────────────────

    def route_step(state: AgentState) -> dict[str, Any]:
        """意图路由节点：分析用户意图"""
        user_input = _get_last_user_message(state)
        if not user_input:
            return {"error": "未检测到用户输入", "step": "route"}

        result = router_agent.route(user_input)
        return {
            "intent": result.get("intent", "general_qa"),
            "intent_confidence": result.get("confidence", 0.0),
            "intent_reasoning": result.get("reasoning", ""),
            "step": "route",
        }

    def retrieve_step(state: AgentState) -> dict[str, Any]:
        """RAG 检索节点：从知识库检索相关信息"""
        user_input = _get_last_user_message(state)
        if not user_input:
            return {"step": "retrieve"}

        # 根据意图选择合适的知识库类型
        kb_type = _intent_to_kb_type(state["intent"])
        docs = knowledge_base.retrieve(query=user_input, knowledge_type=kb_type)

        # 重排序
        if docs:
            docs = reranker.rerank(query=user_input, documents=docs)

        return {
            "retrieved_docs": docs,
            "retrieval_source": kb_type or "all",
            "step": "retrieve",
        }

    def execute_tools_step(state: AgentState) -> dict[str, Any]:
        """工具执行节点：调用业务工具获取实时数据"""
        user_input = _get_last_user_message(state)
        if not user_input:
            return {"step": "execute_tools"}

        # 检查是否已达工具调用上限
        if state["tool_call_count"] >= state["max_tool_calls"]:
            return {
                "need_escalation": True,
                "error": "工具调用次数已达上限，请转接人工客服",
                "step": "execute_tools",
            }

        result = tool_agent_instance.decide_and_execute(
            user_input=user_input,
            conversation_history=_extract_history(state),
        )

        tool_results = result.get("tool_results", [])
        return {
            "tool_calls": tool_results,
            "tool_call_count": state["tool_call_count"] + len(tool_results),
            "need_tool": result.get("need_tool", False),
            "step": "execute_tools",
        }

    def generate_answer_step(state: AgentState) -> dict[str, Any]:
        """答案生成节点：基于 RAG 结果生成回答"""
        user_input = _get_last_user_message(state)
        if not user_input:
            return {"step": "generate_answer"}

        # 合并工具执行结果作为补充上下文
        context_docs = list(state["retrieved_docs"])
        for tool_call in state["tool_calls"]:
            if tool_call.get("result"):
                from langchain_core.documents import Document
                context_docs.append(
                    Document(
                        page_content=f"[工具执行结果 - {tool_call.get('tool', '')}]\n{tool_call['result']}",
                        metadata={"source": f"tool:{tool_call.get('tool', '')}"},
                    )
                )

        answer_result = qa_agent_instance.answer(
            question=user_input,
            context_docs=context_docs,
            conversation_history=_extract_history(state),
        )

        return {
            "answer": answer_result.get("answer", ""),
            "answer_sources": answer_result.get("sources", []),
            "answer_confidence": answer_result.get("confidence", 0.0),
            "step": "generate_answer",
        }

    def verify_answer_step(state: AgentState) -> dict[str, Any]:
        """答案验证节点：验证生成答案的质量"""
        if not state["answer"]:
            return {"step": "verify_answer"}

        user_input = _get_last_user_message(state)
        context_text = "\n".join([
            doc.page_content if hasattr(doc, "page_content") else str(doc)
            for doc in state["retrieved_docs"]
        ])

        verify_llm = settings.openai_model
        from langchain_openai import ChatOpenAI
        verify_llm_instance = ChatOpenAI(
            model=verify_llm,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            temperature=0,
        )

        prompt = ANSWER_VERIFY_PROMPT.format(
            context=context_text,
            question=user_input,
            answer=state["answer"],
        )

        try:
            response = verify_llm_instance.invoke([
                SystemMessage(content="请验证以下回答的质量。"),
                HumanMessage(content=prompt),
            ])
            import json
            import re
            content = response.content.strip()
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
            if match:
                verification = json.loads(match.group(1))
                if not verification.get("verified", True) and verification.get("final_answer"):
                    logger.info("答案验证未通过，使用修正版本")
                    return {
                        "answer": verification["final_answer"],
                        "step": "verify_answer",
                    }
        except Exception as exc:
            logger.warning(f"答案验证异常: {exc}")

        return {"step": "verify_answer"}

    def finalize_step(state: AgentState) -> dict[str, Any]:
        """输出节点：整理最终输出"""
        final_answer = state["answer"] or "抱歉，暂时无法回答您的问题。"
        sources = state.get("answer_sources", [])

        # 构建最终输出
        output_lines = [final_answer]
        if sources:
            output_lines.append(f"\n\n参考来源：{', '.join(sources)}")

        return {
            "answer": "\n".join(output_lines),
            "step": "finalize",
        }

    def escalate_step(state: AgentState) -> dict[str, Any]:
        """人工转接节点：转接人工客服"""
        transfer_msg = supervisor_agent.handle_escalation(
            user_input=_get_last_user_message(state),
            context={
                "intent": state["intent"],
                "tool_calls": state["tool_calls"],
                "last_answer": state["answer"],
            },
        )
        return {
            "answer": transfer_msg,
            "step": "escalate",
        }

    # ────────────────────────────────────────────
    # 添加节点
    # ────────────────────────────────────────────
    graph.add_node("route", route_step)
    graph.add_node("retrieve", retrieve_step)
    graph.add_node("execute_tools", execute_tools_step)
    graph.add_node("generate_answer", generate_answer_step)
    graph.add_node("verify_answer", verify_answer_step)
    graph.add_node("finalize", finalize_step)
    graph.add_node("escalate", escalate_step)

    # ────────────────────────────────────────────
    # 设置入口和条件边
    # ────────────────────────────────────────────
    graph.set_entry_point("route")

    # route → 根据意图分流
    graph.add_conditional_edges(
        "route",
        _route_conditional_edges,
        {
            "retrieve": "retrieve",
            "execute_tools": "execute_tools",
            "finalize": "finalize",
            "escalate": "escalate",
        },
    )

    # retrieve → generate_answer
    graph.add_edge("retrieve", "generate_answer")

    # execute_tools → generate_answer（工具执行后生成答案）
    graph.add_edge("execute_tools", "generate_answer")

    # generate_answer → verify_answer
    graph.add_edge("generate_answer", "verify_answer")

    # verify_answer → finalize（验证通过）或 generate_answer（需要重新生成）
    graph.add_conditional_edges(
        "verify_answer",
        _verify_conditional_edges,
        {"finalize": "finalize", "generate_answer": "generate_answer"},
    )

    # finalize → END
    graph.add_edge("finalize", END)

    # escalate → END
    graph.add_edge("escalate", END)

    logger.info("LangGraph 工作流图构建完成")
    return graph


def _get_last_user_message(state: AgentState) -> str:
    """从状态中提取最后一条用户消息"""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _extract_history(state: AgentState) -> list[dict[str, str]]:
    """从状态中提取对话历史"""
    history = []
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage):
            history.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            history.append({"role": "assistant", "content": msg.content})
    return history


def _route_conditional_edges(state: AgentState) -> str:
    """根据意图决定路由分支"""
    intent = state["intent"]
    if intent == "chitchat":
        return "finalize"
    elif intent in ("tool_use",):
        return "execute_tools"
    elif intent == "complaint" and state["tool_call_count"] >= state["max_tool_calls"]:
        return "escalate"
    else:
        return "retrieve"


def _verify_conditional_edges(state: AgentState) -> str:
    """根据验证结果决定是否重新生成答案"""
    # 简化逻辑：置信度低于阈值则重新生成
    if state["answer_confidence"] < 0.5 and state["tool_call_count"] < state["max_tool_calls"]:
        return "generate_answer"
    return "finalize"


def _intent_to_kb_type(intent: str) -> str | None:
    """将意图映射到知识库类型"""
    mapping = {
        "product_info": "basic",
        "order_query": "professional",
        "after_sales": "professional",
        "complaint": "faq",
        "general_qa": None,
    }
    return mapping.get(intent)


# 编译工作流
workflow = build_workflow()
compiled_graph = workflow.compile()
