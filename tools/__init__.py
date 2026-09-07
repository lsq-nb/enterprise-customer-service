"""
工具模块包
"""
from tools.business_tools import (
    OrderQueryTool,
    ReturnExchangeTool,
    ProductRecommendTool,
    ComplaintRecordTool,
    AppointmentTool,
)

TOOL_REGISTRY = {
    "query_order": OrderQueryTool(),
    "query_return_policy": ReturnExchangeTool(),
    "recommend_product": ProductRecommendTool(),
    "submit_complaint": ComplaintRecordTool(),
    "make_appointment": AppointmentTool(),
}

__all__ = [
    "OrderQueryTool",
    "ReturnExchangeTool",
    "ProductRecommendTool",
    "ComplaintRecordTool",
    "AppointmentTool",
    "TOOL_REGISTRY",
]
