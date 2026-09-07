"""
业务工具实现
包含订单查询、退换货、产品推荐、投诉记录、预约等服务工具

注意：使用类方法直接实现，避免 @tool 装饰器在实例方法上的兼容性问题
"""
import logging
from datetime import datetime
from typing import Any

from tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 模拟数据（实际项目中应连接数据库）
# ─────────────────────────────────────────────
MOCK_ORDERS: dict[str, dict[str, Any]] = {
    "ORD20241201001": {
        "order_id": "ORD20241201001",
        "user_id": "user_001",
        "product": "XX Pro Max 旗舰手机 256GB 曜石黑",
        "amount": 6999,
        "status": "shipped",
        "status_desc": "已发货",
        "create_time": "2024-12-01 10:30:00",
        "shipping_company": "顺丰快递",
        "tracking_number": "SF1234567890",
        "logistics": [
            {"time": "2024-12-01 10:30", "desc": "订单已提交"},
            {"time": "2024-12-01 14:00", "desc": "仓库已发货"},
            {"time": "2024-12-02 08:15", "desc": "快件已到达上海市转运中心"},
            {"time": "2024-12-02 16:30", "desc": "快件正在派送途中"},
            {"time": "2024-12-03 09:45", "desc": "已签收，签收人：本人"},
        ],
    },
    "ORD20241201002": {
        "order_id": "ORD20241201002",
        "user_id": "user_002",
        "product": "XX Pad 平板电脑 256GB",
        "amount": 3299,
        "status": "processing",
        "status_desc": "处理中",
        "create_time": "2024-12-05 15:20:00",
        "shipping_company": "",
        "tracking_number": "",
        "logistics": [
            {"time": "2024-12-05 15:20", "desc": "订单已提交"},
            {"time": "2024-12-05 16:00", "desc": "订单审核通过，正在配货"},
        ],
    },
}

MOCK_COMPLAINTS: list[dict[str, Any]] = [
    {
        "complaint_id": "CMP20241201001",
        "order_id": "ORD20241201001",
        "type": "物流延迟",
        "content": "快递配送时间过长，已超过3天未送达",
        "status": "resolved",
        "create_time": "2024-12-01 18:00:00",
        "resolve_time": "2024-12-02 10:00:00",
        "resolve_note": "已加急处理，次日送达并赠送优惠券补偿",
    }
]


# ─────────────────────────────────────────────
# 工具实现
# ─────────────────────────────────────────────
class OrderQueryTool(BaseTool):
    """订单查询工具"""

    name = "query_order"
    description = "查询订单信息，包括订单状态、物流详情等。适用场景：用户询问订单状态、物流进度、发货时间等。"

    def execute(self, order_id: str) -> str:
        """查询指定订单的详细信息"""
        logger.info(f"订单查询工具被调用，订单号: {order_id}")
        order = MOCK_ORDERS.get(order_id)
        if not order:
            return f"未找到订单号为 {order_id} 的订单，请检查订单号是否正确。"
        return self._format_order_info(order)

    def _format_order_info(self, order: dict[str, Any]) -> str:
        """格式化订单信息为可读文本"""
        lines = [
            "【订单信息】",
            f"订单编号: {order['order_id']}",
            f"商品: {order['product']}",
            f"金额: ¥{order['amount']:,}",
            f"下单时间: {order['create_time']}",
            f"当前状态: {order['status_desc']}",
            "",
            "【物流追踪】",
        ]
        for log in order.get("logistics", []):
            lines.append(f"{log['time']} - {log['desc']}")
        return "\n".join(lines)


class ReturnExchangeTool(BaseTool):
    """退换货政策查询工具"""

    name = "query_return_policy"
    description = "查询退换货政策和流程。适用场景：用户询问如何退货、换货、保修等售后问题。"

    def execute(self, action_type: str = "return") -> str:
        """查询退换货政策"""
        logger.info(f"退换货查询工具被调用，类型: {action_type}")
        policies = {
            "return": """【七天无理由退货政策】
            1. 退货条件：签收后7天内，商品完好、包装齐全
            2. 退货流程：APP订单页面 → 申请售后 → 填写原因 → 寄回商品 → 审核退款
            3. 运费承担：退货运费由消费者承担
            4. 退款时效：商品签收后3-5个工作日内退还至原支付账户
            5. 不支持退货的情况：定制商品、已激活的手机（无质量问题）、服装已穿着洗涤

            【退货地址】
            XX科技售后服务中心
            地址：XX省XX市XX区XX路XX号
            联系人：售后部
            电话：400-XXX-XXXX""",
            "exchange": """【十五天换货政策】
            1. 换货条件：签收后15天内，出现性能故障
            2. 换货流程：APP订单页面 → 申请售后 → 选择换货 → 寄回商品 → 检测确认 → 更换新品
            3. 运费承担：换货运费由平台承担
            4. 换货时效：收到退回商品后7个工作日内完成更换
            5. 换货限制：同型号同款商品，库存不足时可更换同价值商品

            【注意事项】
            - 换货仅支持一次
            - 换货后保修期从换货完成之日起重新计算""",
            "warranty": """【保修政策】
            1. 整机保修：12个月（自签收之日起算）
            2. 主要部件保修：24个月（屏幕、主板、电池）
            3. 配件保修：6个月（充电器、数据线、耳机）

            【保修范围】
            - 非人为损坏的性能故障
            - 材料或制造工艺缺陷
            - 正常使用情况下电池衰减超过80%

            【不保修范围】
            - 人为损坏（摔落、进水、私自拆修）
            - 外观磨损（划痕、掉漆）
            - 消耗品正常老化

            【保修方式】
            - 官方售后网点：全国300+城市授权维修点
            - 寄修服务：邮寄维修，来回运费平台承担
            - VIP上门维修：专属VIP用户免费上门服务""",
        }
        return policies.get(action_type, "不支持的操作类型，请使用 return、exchange 或 warranty")


class ProductRecommendTool(BaseTool):
    """产品推荐工具"""

    name = "recommend_product"
    description = "根据用户需求推荐合适的产品。适用场景：用户咨询产品选择、对比不同型号、预算范围内推荐等。"

    def execute(self, budget: float = 0, usage: str = "日常使用") -> str:
        """根据预算和使用场景推荐产品"""
        logger.info(f"产品推荐工具被调用，预算: {budget}, 场景: {usage}")

        products = [
            {
                "name": "XX Pro Max",
                "price": 6999,
                "features": ["120Hz高刷屏", "100W超级快充", "5倍光学变焦", "旗舰芯片"],
                "suitable_for": ["商务办公", "摄影创作", "游戏娱乐", "日常使用"],
            },
            {
                "name": "XX Pro",
                "price": 4999,
                "features": ["90Hz屏幕", "67W快充", "5000万主摄", "旗舰芯片"],
                "suitable_for": ["日常使用", "商务办公", "摄影创作"],
            },
            {
                "name": "XX Pad",
                "price": 3299,
                "features": ["11寸大屏", "手写笔支持", "8000mAh大电池", "轻便设计"],
                "suitable_for": ["商务办公", "在线学习", "娱乐追剧"],
            },
        ]

        # 筛选符合预算的产品
        filtered = [p for p in products if budget == 0 or p["price"] <= budget]
        if not filtered:
            return f"抱歉，在您的预算（{budget}元）内没有找到合适产品。建议提高预算或查看促销活动。"

        # 按使用场景排序
        suitable = [p for p in filtered if usage in p["suitable_for"]]
        if not suitable:
            suitable = filtered

        # 格式化推荐结果
        result_lines = ["【根据您的需求和预算，为您推荐以下产品】", ""]
        for i, p in enumerate(suitable[:2], 1):
            result_lines.append(f"推荐{i}: {p['name']}")
            result_lines.append(f"  价格: ¥{p['price']:,}")
            result_lines.append(f"  核心特点: {'、'.join(p['features'][:3])}")
            result_lines.append("")

        result_lines.append("如需了解更多详情，请告诉我具体型号！")
        return "\n".join(result_lines)


class ComplaintRecordTool(BaseTool):
    """投诉记录工具"""

    name = "submit_complaint"
    description = "提交投诉或建议。适用场景：用户对服务或产品不满，需要正式投诉或反馈建议。"

    def execute(
        self,
        category: str,
        content: str,
        order_id: str = "",
        contact_phone: str = "",
    ) -> str:
        """提交投诉"""
        logger.info(f"投诉工具被调用，类别: {category}, 订单: {order_id}")

        complaint_id = f"CMP{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = f"""【投诉受理成功】

        投诉编号: {complaint_id}
        投诉类别: {category}
        关联订单: {order_id or "无"}
        提交时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        处理时效:
        - 一般投诉: 1-3个工作日内回复
        - 紧急投诉: 24小时内回复

        请保持手机畅通，我们的客服人员将尽快与您联系处理。
        您也可以通过以下渠道跟进处理进度:
        - 客服电话: 400-XXX-XXXX
        - 在线客服: 官方APP"帮助与反馈"
        """
        return result


class AppointmentTool(BaseTool):
    """预约工具"""

    name = "make_appointment"
    description = "预约售后服务或线下门店 visit。适用场景：用户需要预约维修、以旧换新、到店体验等服务。"

    def execute(
        self,
        service_type: str,
        preferred_time: str,
        city: str = "",
        phone: str = "",
        name: str = "",
    ) -> str:
        """预约服务"""
        logger.info(f"预约工具被调用，类型: {service_type}, 时间: {preferred_time}")

        appointment_id = f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = f"""【预约成功】

        预约编号: {appointment_id}
        服务类型: {service_type}
        期望时间: {preferred_time}
        预约城市: {city or "待确认"}
        预约人: {name or "待确认"}
        联系电话: {phone or "待确认"}

        温馨提示:
        1. 我们将在预约前1天通过短信确认预约信息
        2. 如需取消或修改预约，请提前24小时联系客服
        3. 请携带相关凭证（如购机发票、保修卡）前往服务点

        如有疑问，请拨打客服热线: 400-XXX-XXXX
        """
        return result
