"""
基础工具类定义
所有业务工具的基类，规范工具接口
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    """
    工具基类

    所有业务工具继承此类，实现标准化的工具接口。
    工具通过 LangChain 的 @tool 装饰器注册，支持 Function Calling。
    """

    # 工具名称（用于 Function Call 识别）
    name: str = ""
    # 工具描述（用于 LLM 理解工具用途）
    description: str = ""
    # 工具参数 schema（JSON Schema 格式）
    args_schema: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs.get("name", self.name)
        self.description = kwargs.get("description", self.description)
        logger.debug(f"工具初始化: {self.name}")

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """
        执行工具的核心逻辑

        Args:
            **kwargs: 工具调用参数

        Returns:
            工具执行结果（字符串或字典）
        """
        pass

    def safe_execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        安全的工具执行包装，包含异常处理

        Returns:
            {"success": bool, "result": str, "error": str | None}
        """
        try:
            result = self.execute(**kwargs)
            return {"success": True, "result": str(result), "error": None}
        except Exception as exc:
            logger.error(f"工具 {self.name} 执行失败: {exc}")
            return {"success": False, "result": "", "error": str(exc)}

    def get_tool_info(self) -> dict[str, Any]:
        """获取工具的元信息（名称、描述、参数）"""
        return {
            "name": self.name,
            "description": self.description,
            "args_schema": self.args_schema,
        }

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
