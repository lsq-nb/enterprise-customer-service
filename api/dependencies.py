"""
API 依赖注入模块
提供共享服务的依赖注入
"""
import logging

from fastapi import Depends

from workflows.customer_flow import CustomerFlow
from rag.knowledge_base import get_knowledge_base

logger = logging.getLogger(__name__)

# 全局工作流实例
_workflow: CustomerFlow | None = None


def get_workflow() -> CustomerFlow:
    """获取客户交互工作流实例"""
    global _workflow
    if _workflow is None:
        _workflow = CustomerFlow()
        logger.info("工作流实例已初始化")
    return _workflow


def get_knowledge_base():
    """获取知识库实例"""
    return get_knowledge_base()
