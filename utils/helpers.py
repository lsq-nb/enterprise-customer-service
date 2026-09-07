"""
通用工具函数
提供项目中常用的辅助函数
"""
import re
import uuid
from datetime import datetime


def format_timestamp(timestamp: datetime | None = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间戳

    Args:
        timestamp: 时间对象，默认为当前时间
        fmt: 时间格式字符串

    Returns:
        格式化后的时间字符串
    """
    if timestamp is None:
        timestamp = datetime.now()
    return timestamp.strftime(fmt)


def generate_conversation_id(prefix: str = "conv") -> str:
    """
    生成会话ID

    Args:
        prefix: ID 前缀

    Returns:
        格式化的会话ID
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def sanitize_text(text: str, max_length: int = 2000) -> str:
    """
    文本清洗

    - 去除首尾空白
    - 限制最大长度
    - 移除特殊控制字符

    Args:
        text: 原始文本
        max_length: 最大长度限制

    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    # 去除控制字符
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    # 限制长度
    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text.strip()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_json_safe(json_str: str) -> dict | None:
    """
    安全解析 JSON 字符串

    Args:
        json_str: JSON 字符串

    Returns:
        解析后的字典，失败返回 None
    """
    import json
    try:
        # 尝试从 Markdown 代码块中提取 JSON
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', json_str)
        if match:
            json_str = match.group(1)
        return json.loads(json_str)
    except (json.JSONDecodeError, AttributeError):
        return None
