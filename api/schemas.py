"""
API 请求/响应模型
使用 Pydantic 定义数据结构
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# 请求模型
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    """对话请求模型"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户输入消息")
    conversation_id: Optional[str] = Field(None, description="会话ID，不传则自动生成")
    user_id: Optional[str] = Field("", description="用户标识")
    stream: bool = Field(False, description="是否使用流式响应")


class KnowledgeUploadRequest(BaseModel):
    """知识库上传请求模型"""
    content: Optional[str] = Field(None, description="文档文本内容")
    file_path: Optional[str] = Field(None, description="文档文件路径")
    knowledge_type: str = Field("basic", description="知识库类型：basic/professional/faq")
    source_name: Optional[str] = Field(None, description="来源名称")
    metadata: Optional[dict[str, Any]] = Field(default_factory=dict, description="额外元数据")


class ComplaintRequest(BaseModel):
    """投诉提交请求模型"""
    category: str = Field(..., description="投诉类别")
    content: str = Field(..., min_length=10, description="投诉内容")
    order_id: Optional[str] = Field(None, description="关联订单号")
    contact_phone: Optional[str] = Field(None, description="联系电话")


# ─────────────────────────────────────────────
# 响应模型
# ─────────────────────────────────────────────
class ChatResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str
    answer: str
    intent: str
    intent_confidence: float
    tool_call_count: int
    sources: list[str]
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatStreamResponse(BaseModel):
    """流式对话响应模型"""
    type: str  # start, intent, chunk, end, error
    data: dict[str, Any]


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str
    timestamp: str
    version: str


class ToolListResponse(BaseModel):
    """工具列表响应模型"""
    tools: list[dict[str, Any]]
    total: int


class KnowledgeStatsResponse(BaseModel):
    """知识库统计响应模型"""
    statistics: dict[str, Any]
    total_documents: int


class ComplaintResponse(BaseModel):
    """投诉提交响应模型"""
    success: bool
    complaint_id: str
    message: str
    expected_response_time: str
