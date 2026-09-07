# API 文档

## 1. 健康检查

```http
GET /api/health
```

**响应：**
```json
{
  "status": "healthy",
  "timestamp": "2026-09-07T10:00:00",
  "version": "1.0.0"
}
```

## 2. 对话接口

### 2.1 普通对话

```http
POST /api/chat
Content-Type: application/json
```

**请求体：**
```json
{
  "message": "这款手机支持多少瓦快充？",
  "conversation_id": "conv_abc123",
  "user_id": "user_001",
  "stream": false
}
```

**响应：**
```json
{
  "conversation_id": "conv_abc123",
  "answer": "XX Pro Max 支持 100W 超级快充...",
  "intent": "product_info",
  "intent_confidence": 0.95,
  "tool_call_count": 0,
  "sources": ["sample_knowledge.txt"],
  "timestamp": "2026-09-07T10:00:00"
}
```

### 2.2 流式对话

```http
POST /api/chat/stream
Content-Type: application/json
```

**响应：** SSE (Server-Sent Events) 格式

```
data: {"type": "start", "data": {"conversation_id": "conv_abc123"}}

data: {"type": "intent", "data": {"intent": "product_info", "confidence": 0.95}}

data: {"type": "chunk", "data": {"text": "XX Pro Max 支持"}}

data: {"type": "chunk", "data": {"text": " 100W 超级快充..."}}

data: {"type": "end", "data": {"conversation_id": "conv_abc123"}}
```

## 3. 知识库管理

### 3.1 上传文档

```http
POST /api/knowledge/upload
Content-Type: application/json
```

**请求体：**
```json
{
  "content": "产品说明书内容...",
  "knowledge_type": "basic",
  "source_name": "manual_input",
  "metadata": {}
}
```

### 3.2 获取统计

```http
GET /api/knowledge/stats
```

**响应：**
```json
{
  "statistics": {
    "basic": {"document_count": 10, "status": "active"},
    "professional": {"document_count": 5, "status": "active"},
    "faq": {"document_count": 20, "status": "active"}
  }
}
```

### 3.3 清空知识库

```http
DELETE /api/knowledge/clear?knowledge_type=basic
```

## 4. 工具管理

### 4.1 获取工具列表

```http
GET /api/tools/list
```

**响应：**
```json
{
  "tools": [
    {"name": "query_order", "description": "订单查询...", "type": "OrderQueryTool"},
    {"name": "query_return_policy", "description": "退换货政策...", "type": "ReturnExchangeTool"},
    {"name": "recommend_product", "description": "产品推荐...", "type": "ProductRecommendTool"},
    {"name": "submit_complaint", "description": "投诉提交...", "type": "ComplaintRecordTool"},
    {"name": "make_appointment", "description": "预约服务...", "type": "AppointmentTool"}
  ],
  "total": 5
}
```

## 5. 会话管理

### 5.1 列出会话

```http
GET /api/conversations
```

### 5.2 删除会话

```http
DELETE /api/conversations/{conversation_id}
```
