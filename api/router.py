"""
FastAPI 路由定义
提供对话、知识库管理等 HTTP 接口
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from api.schemas import (
    ChatRequest,
    ChatResponse,
    ChatStreamResponse,
    KnowledgeUploadRequest,
    HealthResponse,
    ToolListResponse,
)
from api.dependencies import get_workflow, get_knowledge_base
from workflows.customer_flow import CustomerFlow
from rag.knowledge_base import get_knowledge_base as get_kb_instance

logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="企业智能客服系统 API",
    description="基于 LangGraph 的多智能体协作企业智能客服系统",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# 健康检查
# ─────────────────────────────────────────────
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查接口"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
    )


# ─────────────────────────────────────────────
# 对话接口（非流式）
# ─────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    workflow: CustomerFlow = Depends(get_workflow),
) -> ChatResponse:
    """
    对话接口

    处理用户输入，返回 AI 回复
    """
    try:
        result = workflow.process(
            user_input=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
        )

        return ChatResponse(
            conversation_id=result["conversation_id"],
            answer=result["answer"],
            intent=result["intent"],
            intent_confidence=result["intent_confidence"],
            tool_call_count=result["tool_call_count"],
            sources=result.get("sources", []),
        )
    except Exception as exc:
        logger.error(f"对话处理异常: {exc}")
        raise HTTPException(status_code=500, detail=f"对话处理失败: {str(exc)}")


# ─────────────────────────────────────────────
# 对话接口（流式）
# ─────────────────────────────────────────────
@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    workflow: CustomerFlow = Depends(get_workflow),
) -> StreamingResponse:
    """
    流式对话接口

    以 SSE (Server-Sent Events) 格式返回结果
    """
    async def generate_events() -> AsyncIterator[str]:
        try:
            # 发送开始事件
            yield format_sse({"type": "start", "data": {"conversation_id": request.conversation_id or "new"}})

            # 执行对话（模拟流式输出）
            result = workflow.process(
                user_input=request.message,
                conversation_id=request.conversation_id,
                user_id=request.user_id,
            )

            # 发送意图识别结果
            yield format_sse({
                "type": "intent",
                "data": {
                    "intent": result["intent"],
                    "confidence": result["intent_confidence"],
                }
            })

            # 发送答案（逐字输出模拟流式）
            answer = result["answer"]
            for i in range(0, len(answer), 10):
                chunk = answer[i:i + 10]
                yield format_sse({"type": "chunk", "data": {"text": chunk}})
                await asyncio.sleep(0.05)  # 模拟流式延迟

            # 发送结束事件
            yield format_sse({
                "type": "end",
                "data": {
                    "conversation_id": result["conversation_id"],
                    "sources": result.get("sources", []),
                }
            })
        except Exception as exc:
            logger.error(f"流式对话异常: {exc}")
            yield format_sse({"type": "error", "data": {"message": str(exc)}})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────
# 知识库管理接口
# ─────────────────────────────────────────────
@app.post("/api/knowledge/upload")
async def upload_knowledge(
    request: KnowledgeUploadRequest,
    kb = Depends(get_knowledge_base),
) -> JSONResponse:
    """
    上传知识库文档

    支持从文本或文件上传知识库内容
    """
    try:
        if request.content:
            # 直接提供文本内容
            count = kb.load_from_text(
                text=request.content,
                knowledge_type=request.knowledge_type,
                source_name=request.source_name or "api_upload",
                metadata=request.metadata,
            )
        elif request.file_path:
            # 从文件路径加载
            count = kb.load_from_file(
                file_path=request.file_path,
                knowledge_type=request.knowledge_type,
                metadata=request.metadata,
            )
        else:
            raise HTTPException(status_code=400, detail="请提供 content 或 file_path")

        return JSONResponse(content={
            "success": True,
            "message": f"成功上传 {count} 个文档块到 {request.knowledge_type} 知识库",
            "count": count,
        })
    except Exception as exc:
        logger.error(f"知识库上传异常: {exc}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(exc)}")


@app.get("/api/knowledge/stats")
async def knowledge_stats(kb = Depends(get_knowledge_base)) -> JSONResponse:
    """获取知识库统计信息"""
    stats = kb.get_stats()
    return JSONResponse(content={"statistics": stats})


@app.delete("/api/knowledge/clear")
async def clear_knowledge(
    knowledge_type: str,
    kb = Depends(get_knowledge_base),
) -> JSONResponse:
    """清空指定知识库"""
    success = kb.clear_collection(knowledge_type)
    if not success:
        raise HTTPException(status_code=400, detail=f"无效的知识库类型: {knowledge_type}")
    return JSONResponse(content={"success": True, "message": f"已清空 {knowledge_type} 知识库"})


# ─────────────────────────────────────────────
# 工具接口
# ─────────────────────────────────────────────
@app.get("/api/tools/list", response_model=ToolListResponse)
async def list_tools() -> ToolListResponse:
    """获取所有可用工具列表"""
    from tools import TOOL_REGISTRY
    tools = [
        {
            "name": name,
            "description": tool.description,
            "type": type(tool).__name__,
        }
        for name, tool in TOOL_REGISTRY.items()
    ]
    return ToolListResponse(tools=tools, total=len(tools))


# ─────────────────────────────────────────────
# 会话管理接口
# ─────────────────────────────────────────────
@app.get("/api/conversations")
async def list_conversations(
    workflow: CustomerFlow = Depends(get_workflow),
) -> JSONResponse:
    """列出所有会话"""
    conversations = workflow.list_conversations()
    return JSONResponse(content={"conversations": conversations, "total": len(conversations)})


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    workflow: CustomerFlow = Depends(get_workflow),
) -> JSONResponse:
    """删除指定会话"""
    success = workflow.clear_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话不存在: {conversation_id}")
    return JSONResponse(content={"success": True, "message": f"已删除会话 {conversation_id}"})


# ─────────────────────────────────────────────
# 辅助函数
# ─────────────────────────────────────────────
def format_sse(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
