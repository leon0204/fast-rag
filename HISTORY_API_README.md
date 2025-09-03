# 历史记录API功能说明

## 概述

FastRAG 现在支持完整的聊天历史记录功能，包括：
- 自动保存用户和AI的对话记录
- 历史记录查询和管理
- 会话统计信息
- 前端历史记录显示和删除

## API 端点

### 1. 获取历史记录列表

```http
GET /history/list
```

**查询参数:**
- `query` (可选): 搜索关键词
- `limit` (可选): 返回数量上限，默认50，最大200
- `offset` (可选): 偏移量，默认0

**响应示例:**
```json
[
  {
    "id": "session_123",
    "title": "关于Docker的讨论",
    "updated_at": "2024-01-01T10:00:00",
    "message_count": 6
  }
]
```

### 2. 获取会话详情

```http
GET /history/session/{session_id}
```

**查询参数:**
- `limit` (可选): 返回消息数量上限，默认100，最大500
- `offset` (可选): 偏移量，默认0

**响应示例:**
```json
{
  "session_id": "session_123",
  "title": "关于Docker的讨论",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:30:00",
  "message_count": 6,
  "messages": [
    {
      "role": "user",
      "content": "什么是Docker？",
      "timestamp": "2024-01-01T10:00:00"
    },
    {
      "role": "assistant",
      "content": "Docker是一个开源的容器化平台...",
      "timestamp": "2024-01-01T10:00:30"
    }
  ]
}
```

### 3. 删除会话

```http
DELETE /history/session/{session_id}
```

**响应示例:**
```json
{
  "message": "成功删除会话 session_123",
  "deleted_messages": 6
}
```

### 4. 清空所有历史

```http
DELETE /history/all
```

**响应示例:**
```json
{
  "message": "成功清空所有聊天历史",
  "deleted_sessions": 5,
  "deleted_messages": 25
}
```

### 5. 获取统计信息

```http
GET /history/stats
```

**响应示例:**
```json
{
  "total_sessions": 5,
  "total_messages": 25,
  "user_messages": 13,
  "ai_messages": 12,
  "last_activity": "2024-01-01T10:30:00"
}
```

## 数据库结构

### 会话表 (chat_sessions)
```sql
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER DEFAULT 0
);
```

### 消息表 (chat_messages)
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    role TEXT CHECK(role IN ('user', 'assistant')),
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
);
```

## 前端集成

### 1. 自动保存

每次聊天完成后，系统会自动：
- 保存用户输入到历史数据库
- 保存AI完整回复到历史数据库
- 更新会话的消息计数和最后更新时间

### 2. 历史记录显示

前端会自动：
- 调用 `/history/list` 获取历史记录
- 显示会话标题、消息数量和更新时间
- 支持搜索和分页

### 3. 会话管理

用户可以：
- 点击历史记录项切换到对应会话
- 删除不需要的会话
- 开启新的对话

## 使用方法

### 1. 启动服务

```bash
# 启动后端服务
python main.py

# 启动前端服务
cd frontend-app
npm run dev
```

### 2. 测试API

```bash
# 测试历史记录API
python test_history_api.py
```

### 3. 手动测试

```bash
# 获取历史记录
curl -X GET "http://localhost:8000/history/list"

# 获取统计信息
curl -X GET "http://localhost:8000/history/stats"

# 删除会话
curl -X DELETE "http://localhost:8000/history/session/session_id"
```

## 配置说明

### 1. 数据库文件

历史记录默认存储在 `chat_history.db` 文件中，这是一个SQLite数据库。

### 2. 自动初始化

服务启动时会自动：
- 创建数据库表结构
- 建立必要的索引
- 检查数据库连接状态

### 3. 错误处理

- 数据库操作失败时会记录错误日志
- 不影响正常的聊天功能
- 前端会显示相应的错误提示

## 注意事项

### 1. 性能考虑

- 大量历史记录可能影响查询性能
- 建议定期清理旧的历史记录
- 可以考虑分表或归档策略

### 2. 存储空间

- 每条消息都会保存完整内容
- 长对话会占用较多存储空间
- 建议监控数据库文件大小

### 3. 隐私保护

- 所有对话内容都保存在本地
- 不会上传到外部服务器
- 删除会话会永久删除相关数据

## 故障排除

### 1. 历史记录不显示

**可能原因:**
- 数据库文件权限问题
- 数据库表未创建
- API路由未正确注册

**解决方案:**
- 检查 `chat_history.db` 文件权限
- 重启服务让数据库自动初始化
- 确认 `main.py` 中包含了 `history_router`

### 2. 保存失败

**可能原因:**
- 数据库文件被锁定
- 磁盘空间不足
- 数据库损坏

**解决方案:**
- 检查是否有其他进程在使用数据库
- 清理磁盘空间
- 删除损坏的数据库文件重新创建

### 3. 前端显示异常

**可能原因:**
- API响应格式不匹配
- 网络连接问题
- 前端代码错误

**解决方案:**
- 检查浏览器控制台错误信息
- 验证API响应格式
- 确认前端代码正确性

## 更新日志

- **v1.0**: 基础历史记录功能
- **v2.0**: 增加会话管理和统计功能
- **v2.1**: 优化前端显示和交互
- **v2.2**: 增强错误处理和性能优化
