# 企业智能客服系统

> 基于 LangGraph 的多智能体协作企业智能客服系统

## 📋 项目简介

本项目是一个企业级智能客服系统，采用先进的 **LangGraph** 多智能体架构，融合 **RAG（检索增强生成）** 和 **Function Call（工具调用）** 能力，实现用户咨询的自动化分流与精准答复。

### 核心特性

- 🧠 **多智能体协作**：基于 LangGraph 状态机的多 Agent 分工协作
- 🔍 **混合检索**：BM25 关键词 + 向量语义 混合召回策略
- 📚 **三层知识库**：基础知识库 / 专业知识库 / FAQ 知识库
- 🔄 **重排序优化**：CrossEncoder 语义重排序提升检索质量
- 🛠️ **工具调用**：订单查询、退换货、产品推荐等 5 种业务工具
- 💬 **流式对话**：SSE 流式响应，实时交互体验
- 📊 **可视化监控**：Streamlit 运营配置与监控后台
- 🐳 **容器化部署**：Docker Compose 一键部署

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit 前端界面                        │
│  (对话界面 / 知识库管理 / 监控仪表板)                         │
└─────────────────────────────────────────────────────────────┘
                          ↓↑ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 服务层                            │
│  /api/chat (对话) / /api/knowledge (知识库) / /api/tools   │
└─────────────────────────────────────────────────────────────┘
                          ↓↑
┌─────────────────────────────────────────────────────────────┐
│              LangGraph 多智能体工作流                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 路由Agent │→│ RAG检索  │→│ 答案生成 │→│ 答案验证 │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│       ↓           ↓           ↓             ↓               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │工具Agent │  │三层知识库│  │重排序器  │  │人工转接 │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
└─────────────────────────────────────────────────────────────┘
                          ↓↑
┌─────────────────────────────────────────────────────────────┐
│                   向量数据库 (ChromaDB)                      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Docker & Docker Compose（可选，用于容器化部署）

### 方式一：本地运行

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd enterprise_customer_service

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key 等信息

# 4. 启动 API 服务
python main.py

# 5. 启动前端界面（另一个终端）
streamlit run frontend/app.py
```

### 方式二：Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key 等信息

# 2. 一键启动所有服务
docker-compose up -d

# 3. 访问服务
# API: http://localhost:8000
# 前端: http://localhost:8501
# API文档: http://localhost:8000/docs
```

## 📡 API 接口

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/chat` | POST | 对话接口 |
| `/api/chat/stream` | POST | 流式对话接口 |
| `/api/knowledge/upload` | POST | 上传知识库文档 |
| `/api/knowledge/stats` | GET | 知识库统计 |
| `/api/knowledge/clear` | DELETE | 清空知识库 |
| `/api/tools/list` | GET | 获取工具列表 |
| `/api/conversations` | GET | 列出所有会话 |
| `/api/conversations/{id}` | DELETE | 删除会话 |

### 对话接口示例

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "这款手机支持多少瓦快充？",
    "conversation_id": "conv_abc123"
  }'
```

## 🛠️ 技术栈

| 类别 | 技术选型 |
|------|---------|
| **LLM 框架** | LangChain, LangGraph |
| **向量数据库** | ChromaDB |
| **检索策略** | BM25 + 向量混合检索 + CrossEncoder 重排序 |
| **Web 框架** | FastAPI, Streamlit |
| **容器化** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **测试** | pytest |

## 📁 项目结构

```
enterprise_customer_service/
├── agents/                  # 多智能体定义
│   ├── router.py           # 意图识别路由器
│   ├── qa_agent.py         # 知识问答 Agent
│   ├── tool_agent.py       # 工具执行 Agent
│   └── supervisor.py       # 主管协调 Agent
├── api/                     # FastAPI 服务
│   ├── router.py           # 路由定义
│   ├── schemas.py          # 数据模型
│   └── dependencies.py     # 依赖注入
├── config/                  # 配置管理
│   ├── settings.py         # 环境配置
│   └── prompts.py          # Prompt 模板
├── data/knowledge/         # 知识库数据
├── graph/                   # LangGraph 工作流
│   ├── state.py            # 状态定义
│   └── workflow.py         # 工作流图
├── rag/                     # RAG 检索模块
│   ├── retriever.py        # 混合检索器
│   ├── knowledge_base.py   # 知识库管理
│   └── reranker.py         # 重排序器
├── tools/                   # 业务工具
│   ├── base_tool.py        # 工具基类
│   └── business_tools.py   # 业务工具实现
├── workflows/               # 工作流封装
│   └── customer_flow.py    # 客户交互流程
├── frontend/                # Streamlit 前端
│   ├── app.py              # 主页面
│   └── pages/              # 子页面
├── tests/                   # 测试文件
├── utils/                   # 工具函数
├── main.py                  # 应用入口
├── docker-compose.yml      # Docker 编排
├── Dockerfile              # 容器构建
└── requirements.txt        # 依赖清单
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行测试并生成覆盖率报告
pytest tests/ -v --cov=. --cov-report=html

# 运行特定测试
pytest tests/test_workflow.py -v
```

## 📝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。

## 🔗 相关链接

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 官方文档](https://python.langchain.com/)
- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Streamlit 官方文档](https://docs.streamlit.io/)

---

**开发者**：Agnes (Sapiens AI)  
**版本**：1.0.0  
**最后更新**：2026-09-07
