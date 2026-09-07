"""
知识库管理页面
上传、查看和管理知识库文档
"""
import logging
import os
from pathlib import Path

import requests
import streamlit as st

logger = logging.getLogger(__name__)

st.set_page_config(page_title="知识库管理", page_icon="📚", layout="wide")

# 默认 API 地址
API_URL = os.getenv("API_URL", "http://localhost:8000")


def get_knowledge_stats() -> dict:
    """获取知识库统计"""
    try:
        resp = requests.get(f"{API_URL}/api/knowledge/stats", timeout=10)
        if resp.status_code == 200:
            return resp.json().get("statistics", {})
    except Exception as e:
        st.error(f"获取统计失败: {e}")
    return {}


def upload_knowledge(content: str, kb_type: str, source: str) -> bool:
    """上传知识库内容"""
    try:
        resp = requests.post(
            f"{API_URL}/api/knowledge/upload",
            json={"content": content, "knowledge_type": kb_type, "source_name": source},
            timeout=30,
        )
        if resp.status_code == 200:
            st.success(resp.json().get("message", "上传成功"))
            return True
        else:
            st.error(f"上传失败: {resp.status_code}")
            return False
    except Exception as e:
        st.error(f"上传异常: {e}")
        return False


# ─────────────────────────────────────────────
# 页面标题
# ─────────────────────────────────────────────
st.markdown("## 📚 知识库管理")
st.markdown("上传和管理企业知识库文档，支持三种知识库类型：")

# ─────────────────────────────────────────────
# 统计信息
# ─────────────────────────────────────────────
stats = get_knowledge_stats()
if stats:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("基础知识库", stats.get("basic", {}).get("document_count", 0))
    with col2:
        st.metric("专业知识库", stats.get("professional", {}).get("document_count", 0))
    with col3:
        st.metric("FAQ 知识库", stats.get("faq", {}).get("document_count", 0))
else:
    st.info("知识库统计加载中...")

st.markdown("---")

# ─────────────────────────────────────────────
# 上传区域
# ─────────────────────────────────────────────
tab1, tab2 = st.tabs(["文本上传", "文件上传"])

with tab1:
    st.subheader("📝 直接上传文本内容")
    kb_type = st.selectbox("知识库类型", ["basic", "professional", "faq"],
                           help="basic: 产品信息 | professional: 业务规则 | faq: 常见问题")
    source_name = st.text_input("来源名称", value="manual_input")
    content = st.text_area("文档内容", height=200,
                           placeholder="请粘贴或输入知识库文档内容...")
    if st.button("上传到知识库", type="primary"):
        if content.strip():
            upload_knowledge(content, kb_type, source_name)
        else:
            st.warning("请输入文档内容")

with tab2:
    st.subheader("📁 上传文件")
    kb_type_file = st.selectbox("知识库类型", ["basic", "professional", "faq"], key="kb_type_file")
    uploaded_file = st.file_uploader("选择文件", type=["txt", "md", "csv", "json"])
    if uploaded_file is not None:
        if st.button("上传文件", type="primary"):
            # 保存临时文件
            temp_path = f"./data/knowledge/temp_{uploaded_file.name}"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            try:
                resp = requests.post(
                    f"{API_URL}/api/knowledge/upload",
                    json={"file_path": temp_path, "knowledge_type": kb_type_file},
                    timeout=30,
                )
                if resp.status_code == 200:
                    st.success(resp.json().get("message", "上传成功"))
                else:
                    st.error(f"上传失败: {resp.text}")
            except Exception as e:
                st.error(f"上传异常: {e}")
            finally:
                Path(temp_path).unlink(missing_ok=True)

st.markdown("---")

# ─────────────────────────────────────────────
# 知识库操作
# ─────────────────────────────────────────────
st.subheader("🛠️ 知识库操作")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("清空基础知识库", type="secondary"):
        if st.checkbox("确认清空？"):
            requests.delete(f"{API_URL}/api/knowledge/clear?knowledge_type=basic")
            st.success("已清空")
with col2:
    if st.button("清空专业知识库", type="secondary"):
        if st.checkbox("确认清空？"):
            requests.delete(f"{API_URL}/api/knowledge/clear?knowledge_type=professional")
            st.success("已清空")
with col3:
    if st.button("清空 FAQ 知识库", type="secondary"):
        if st.checkbox("确认清空？"):
            requests.delete(f"{API_URL}/api/knowledge/clear?knowledge_type=faq")
            st.success("已清空")

# 返回按钮
st.markdown("[← 返回对话页面](/)")
