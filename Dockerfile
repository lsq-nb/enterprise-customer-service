# ============================================
# 企业智能客服系统 - Dockerfile
# 多阶段构建，优化镜像大小
# ============================================

# ─────────────────────────────────────────────
# 阶段 1: 构建阶段 - 安装依赖
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 创建工作目录
WORKDIR /build

# 复制依赖文件
COPY requirements.txt .
COPY requirements-dev.txt .

# 安装 Python 依赖到独立目录
RUN pip install --target=/app/libs -r requirements.txt && \
    pip install --target=/app/libs -r requirements-dev.txt

# ─────────────────────────────────────────────
# 阶段 2: 运行阶段
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runner

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONPATH=/app/libs

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# 设置工作目录
WORKDIR /app

# 复制 Python 包
COPY --from=builder /app/libs /app/libs

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录
RUN mkdir -p /app/data/knowledge /app/logs && \
    chown -R appuser:appuser /app

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE 8000 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 默认启动命令（可通过 docker-compose 覆盖）
CMD ["python", "-m", "main"]
