"""
监控仪表板页面
显示对话统计和系统状态
"""
import logging
import os
from datetime import datetime

import requests
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

st.set_page_config(page_title="监控仪表板", page_icon="📊", layout="wide")

API_URL = os.getenv("API_URL", "http://localhost:8000")


# ─────────────────────────────────────────────
# 获取统计数据
# ─────────────────────────────────────────────
def get_stats() -> dict:
    """获取系统统计"""
    try:
        conv_resp = requests.get(f"{API_URL}/api/conversations", timeout=10)
        knowledge_resp = requests.get(f"{API_URL}/api/knowledge/stats", timeout=10)
        return {
            "conversations": conv_resp.json().get("conversations", []),
            "knowledge": knowledge_resp.json().get("statistics", {}),
        }
    except Exception as e:
        st.error(f"获取统计失败: {e}")
        return {"conversations": [], "knowledge": {}}


# ─────────────────────────────────────────────
# 页面布局
# ─────────────────────────────────────────────
st.markdown("## 📊 系统监控仪表板")
st.markdown(f"**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

stats = get_stats()

# ─────────────────────────────────────────────
# 关键指标卡片
# ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    total_convs = len(stats["conversations"])
    st.metric("总对话数", total_convs)
with col2:
    basic_count = stats["knowledge"].get("basic", {}).get("document_count", 0)
    st.metric("基础文档", basic_count)
with col3:
    prof_count = stats["knowledge"].get("professional", {}).get("document_count", 0)
    st.metric("专业文档", prof_count)
with col4:
    faq_count = stats["knowledge"].get("faq", {}).get("document_count", 0)
    st.metric("FAQ 文档", faq_count)

st.markdown("---")

# ─────────────────────────────────────────────
# 对话历史表格
# ─────────────────────────────────────────────
st.subheader("💬 最近对话记录")
if stats["conversations"]:
    conv_data = []
    for conv in stats["conversations"][-10:]:  # 最近10条
        conv_data.append({
            "会话ID": conv.get("conversation_id", ""),
            "轮次": conv.get("turn_count", 0),
            "创建时间": conv.get("created_at", "")[:19],
            "最后消息": conv.get("last_message", "")[:30] + "..." if len(conv.get("last_message", "")) > 30 else conv.get("last_message", ""),
        })
    st.dataframe(conv_data, use_container_width=True)
else:
    st.info("暂无对话记录")

st.markdown("---")

# ─────────────────────────────────────────────
# 知识库状态图表
# ─────────────────────────────────────────────
st.subheader("📚 知识库状态")

kb_data = stats["knowledge"]
if kb_data:
    fig = go.Figure(data=[
        go.Bar(
            name="文档数量",
            x=["基础知识库", "专业知识库", "FAQ知识库"],
            y=[
                kb_data.get("basic", {}).get("document_count", 0),
                kb_data.get("professional", {}).get("document_count", 0),
                kb_data.get("faq", {}).get("document_count", 0),
            ],
            marker_color=["#2196F3", "#4CAF50", "#FF9800"],
        )
    ])
    fig.update_layout(
        title="各知识库文档数量",
        barmode="group",
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("知识库数据加载中...")

st.markdown("---")

# ─────────────────────────────────────────────
# 系统健康检查
# ─────────────────────────────────────────────
st.subheader("🏥 系统健康状态")
try:
    health_resp = requests.get(f"{API_URL}/api/health", timeout=5)
    if health_resp.status_code == 200:
        health_data = health_resp.json()
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            st.success(f"✅ 服务状态: {health_data.get('status', 'unknown')}")
        with col_h2:
            st.info(f"📦 版本: {health_data.get('version', 'unknown')}")
        with col_h3:
            st.info(f"⏰ 时间: {health_data.get('timestamp', '')[:19]}")
    else:
        st.error(f"❌ 健康检查失败: {health_resp.status_code}")
except Exception as e:
    st.error(f"❌ 无法连接到 API 服务: {e}")

# 返回按钮
st.markdown("[← 返回对话页面](/)")
