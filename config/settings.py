"""
系统配置管理模块
基于 Pydantic Settings，支持环境变量和 .env 文件加载
"""
import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """系统配置类"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ────────────────────────────────────────────
    # 大模型配置
    # ────────────────────────────────────────────
    openai_api_key: str = Field(default="", description="OpenAI API 密钥")
    openai_base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI API 基础 URL")
    openai_model: str = Field(default="gpt-4o", description="默认对话模型")
    embedding_model: str = Field(default="text-embedding-3-small", description="嵌入向量模型")

    # 国内模型配置（可选）
    dashscope_api_key: Optional[str] = Field(default=None, description="阿里云 DashScope API 密钥")
    dashscope_model: Optional[str] = Field(default="qwen-max", description="阿里云通义千问模型")
    tencent_secret_id: Optional[str] = Field(default=None, description="腾讯云 Secret ID")
    tencent_secret_key: Optional[str] = Field(default=None, description="腾讯云 Secret Key")

    # 推理参数
    temperature: float = Field(default=0.3, ge=0.0, le=1.0, description="模型生成温度")
    max_tokens: int = Field(default=2048, ge=1, description="最大生成 token 数")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="核采样参数")

    # ────────────────────────────────────────────
    # 向量数据库配置
    # ────────────────────────────────────────────
    chroma_persist_dir: str = Field(default="./data/knowledge/chroma_db", description="ChromaDB 持久化存储路径")
    chroma_collection: str = Field(default="enterprise_knowledge", description="ChromaDB 集合名称")

    # 检索参数
    retrieval_top_k: int = Field(default=5, ge=1, description="混合检索返回文档数")
    bm25_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="BM25 检索结果权重")
    rerank_top_k: int = Field(default=3, ge=1, description="重排序后保留文档数")
    chunk_size: int = Field(default=500, ge=100, le=2000, description="文档分块大小（token）")
    chunk_overlap: int = Field(default=50, ge=0, le=200, description="文档分块重叠大小（token）")

    # ────────────────────────────────────────────
    # 服务配置
    # ────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", description="FastAPI 监听地址")
    api_port: int = Field(default=8000, ge=1, le=65535, description="FastAPI 监听端口")
    api_debug: bool = Field(default=False, description="是否开启调试模式")

    streamlit_port: int = Field(default=8501, description="Streamlit 前端端口")
    streamlit_headless: bool = Field(default=True, description="Streamlit 无头模式")

    # ────────────────────────────────────────────
    # 日志配置
    # ────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="./logs/app.log", description="日志文件路径")

    # ────────────────────────────────────────────
    # 知识库配置
    # ────────────────────────────────────────────
    knowledge_dir: str = Field(default="./data/knowledge", description="知识库文档存储目录")
    allowed_upload_extensions: list[str] = Field(default=[".txt", ".md", ".csv", ".pdf"], description="允许上传的文件扩展名")

    # ────────────────────────────────────────────
    # 验证方法
    # ────────────────────────────────────────────
    def is_configured(self) -> bool:
        """检查是否已配置必要的 API Key"""
        return bool(self.openai_api_key.strip())

    @property
    def api_key(self) -> str:
        """获取 API Key（兼容旧属性名）"""
        return self.openai_api_key


# 全局配置单例
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置实例（懒加载）"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 向后兼容的 lazy settings 对象
class _LazySettings:
    """惰性配置对象，首次访问时才加载实际配置"""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)

    def __repr__(self) -> str:
        return repr(get_settings())

    def is_configured(self) -> bool:
        return get_settings().is_configured()


settings = _LazySettings()
