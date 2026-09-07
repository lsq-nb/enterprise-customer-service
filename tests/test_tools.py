"""
工具模块测试
测试业务工具功能
"""
import pytest
from unittest.mock import MagicMock, patch


class TestOrderQueryTool:
    """订单查询工具测试"""

    def test_query_existing_order(self):
        """测试查询存在的订单"""
        from tools.business_tools import OrderQueryTool

        tool = OrderQueryTool()
        result = tool.query_order.invoke({"order_id": "ORD20241201001"})
        assert "ORD20241201001" in result
        assert "已签收" in result

    def test_query_nonexistent_order(self):
        """测试查询不存在的订单"""
        from tools.business_tools import OrderQueryTool

        tool = OrderQueryTool()
        result = tool.query_order.invoke({"order_id": "NOT_EXIST"})
        assert "未找到" in result or "NOT_EXIST" in result


class TestReturnExchangeTool:
    """退换货工具测试"""

    def test_return_policy(self):
        """测试退货政策查询"""
        from tools.business_tools import ReturnExchangeTool

        tool = ReturnExchangeTool()
        result = tool.query_return_policy.invoke({"action_type": "return"})
        assert "七天" in result or "退货" in result

    def test_warranty_policy(self):
        """测试保修政策查询"""
        from tools.business_tools import ReturnExchangeTool

        tool = ReturnExchangeTool()
        result = tool.query_return_policy.invoke({"action_type": "warranty"})
        assert "保修" in result


class TestProductRecommendTool:
    """产品推荐工具测试"""

    def test_recommend_with_budget(self):
        """测试预算内推荐"""
        from tools.business_tools import ProductRecommendTool

        tool = ProductRecommendTool()
        result = tool.recommend_product.invoke({"budget": 5000, "usage": "日常使用"})
        assert "推荐" in result or "产品" in result

    def test_recommend_no_budget(self):
        """测试不限预算推荐"""
        from tools.business_tools import ProductRecommendTool

        tool = ProductRecommendTool()
        result = tool.recommend_product.invoke({"budget": 0, "usage": "商务办公"})
        assert "推荐" in result or "产品" in result


class TestComplaintRecordTool:
    """投诉记录工具测试"""

    def test_submit_complaint(self):
        """测试提交投诉"""
        from tools.business_tools import ComplaintRecordTool

        tool = ComplaintRecordTool()
        result = tool.submit_complaint.invoke({
            "category": "物流问题",
            "content": "快递配送时间过长",
            "order_id": "ORD123",
        })
        assert "投诉受理成功" in result
        assert "CMP" in result


class TestAppointmentTool:
    """预约工具测试"""

    def test_make_appointment(self):
        """测试预约服务"""
        from tools.business_tools import AppointmentTool

        tool = AppointmentTool()
        result = tool.make_appointment.invoke({
            "service_type": "维修服务",
            "preferred_time": "2024-12-15 14:00",
            "city": "北京",
        })
        assert "预约成功" in result
        assert "APT" in result
