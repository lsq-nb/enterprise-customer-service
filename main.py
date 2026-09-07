"""
企业智能客服系统 - 主入口
启动 FastAPI 服务
"""
import logging
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# 导入 API 应用
from api.router import app
from config.settings import settings


@app.on_event("startup")
async def startup_event() -> None:
    """应用启动时执行初始化"""
    logger.info("🚀 企业智能客服系统启动中...")
    logger.info(f"📦 模型: {settings.openai_model}")
    logger.info(f"🔍 检索: BM25 + 向量混合召回")
    logger.info(f"📚 知识库: {settings.chroma_collection}")
    logger.info("✅ 启动完成")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """应用关闭时执行清理"""
    logger.info("🛑 系统关闭中...")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
    )
