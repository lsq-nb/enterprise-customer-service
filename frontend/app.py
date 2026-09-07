"""
企业智能客服系统 - Streamlit 前端主页面
对话界面 + 历史记录展示
"""
import logging
import os
from datetime import datetime

import requests
import streamlit as st

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="企业智能客服系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 样式配置
# ─────────────────────────────────────────────
CSS = """
<style>
.stMainBlockContainer { padding-top: 2rem; }
.chat-message { padding: 10px 15px; border-radius: 10px; margin-bottom: 10px; }
.user-message { background-color: #e3f2fd; text-align: right; }
.bot-message { background-color: #f5f5f5; text-align: left; }
.intent-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin-left: 8px; }
.confidence-high { background-color: #c8e6c9; color: #2e7d32; }
.confidence-medium { background-color: #fff9c4; color: #f57f17; }
.confidence-low { background-color: #ffcdd2; color: #c62828; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 初始化会话状态
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "api_url" not in st.session_state:
    st.session_state.api_url = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────
# 侧边栏
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 智能客服系统")
    st.markdown("---")

    # API 配置
    api_url = st.text_input("API 地址", value=st.session_state.api_url)
    if st.button("测试连接"):
        try:
            resp = requests.get(f"{api_url}/api/health", timeout=5)
            if resp.status_code == 200:
                st.success("✅ 连接成功")
            else:
                st.error(f"❌ 连接失败: {resp.status_code}")
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")

    st.markdown("---")

    # 操作按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ 清空对话"):
            st.session_state.messages = []
            st.session_state.conversation_id = None
            st.rerun()
    with col2:
        if st.button("📊 知识库"):
            st.switch_page("frontend/pages/knowledge.py")

    st.markdown("---")
    st.markdown("### 系统信息")
    st.info("""
    **技术栈**
    - LangGraph 多智能体
    - BM25 + 向量混合检索
    - RAG 检索增强
    - Function Call 工具调用

    **支持的意图**
    - 📱 产品咨询
    - 📦 订单查询
    - 🔧 售后服务
    - 💬 投诉反馈
    """)

# ─────────────────────────────────────────────
# 主区域 - 对话历史
# ─────────────────────────────────────────────
st.markdown("## 💬 智能客服对话")

# 显示欢迎语
if not st.session_state.messages:
    from config.prompts import WELCOME_MESSAGE
    st.markdown(WELCOME_MESSAGE)

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("intent"):
            confidence = msg.get("confidence", 0)
            level = "high" if confidence >= 0.8 else ("medium" if confidence >= 0.5 else "low")
            st.markdown(
                f'<span class="intent-badge confidence-{level}">意图: {msg["intent"]} ({confidence:.0%})</span>',
                unsafe_allow_html=True,
            )

# ─────────────────────────────────────────────
# 输入区域
# ─────────────────────────────────────────────
if prompt := st.chat_input("请输入您的问题..."):
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 API
    with st.chat_message("assistant"):
        with st.spinner("正在思考..."):
            try:
                resp = requests.post(
                    f"{api_url}/api/chat",
                    json={
                        "message": prompt,
                        "conversation_id": st.session_state.conversation_id,
                        "stream": False,
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("answer", "抱歉，暂时无法回答。")
                    st.markdown(answer)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "intent": data.get("intent"),
                        "confidence": data.get("intent_confidence", 0),
                    })
                    st.session_state.conversation_id = data.get("conversation_id")
                else:
                    st.error(f"请求失败: {resp.status_code}")
                    st.error(resp.text)
            except Exception as e:
                st.error(f"请求异常: {e}")
