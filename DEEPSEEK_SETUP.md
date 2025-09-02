# DeepSeek API 设置和使用指南

## 概述

FastRAG 现在支持两种大模型调用方式：
- **Ollama**: 本地部署，快速响应
- **DeepSeek API**: 云端AI，深度思考

## 配置步骤

### 1. 获取 DeepSeek API Key

1. 访问 [DeepSeek 官网](https://platform.deepseek.com/)
2. 注册账号并登录
3. 在控制台中创建 API Key
4. 复制 API Key

### 2. 配置环境变量

在项目根目录创建或编辑 `.env` 文件：

```bash
# 模型类型选择: "ollama" 或 "deepseek"
MODEL_TYPE=ollama

# Ollama 模型配置
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=llama3
OLLAMA_MODEL=llama3:latest
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# DeepSeek API 配置
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=your_actual_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=800
DEEPSEEK_TEMPERATURE=0.7
DEEPSEEK_TOP_P=0.9
```

### 3. 启动服务

```bash
# 启动后端服务
python main.py

# 启动前端服务
cd frontend-app
npm run dev
```

## 使用方法

### 1. 前端界面切换

1. 在聊天界面右上角找到模型切换按钮
2. 点击按钮选择 Ollama 或 DeepSeek
3. 系统会显示切换成功或失败的提示

### 2. API 接口切换

```bash
# 获取当前模型配置
curl -X GET "http://localhost:8000/manage/model/config"

# 切换到 DeepSeek
curl -X POST "http://localhost:8000/manage/model/switch?model_type=deepseek"

# 切换到 Ollama
curl -X POST "http://localhost:8000/manage/model/switch?model_type=ollama"

# 测试模型连接
curl -X POST "http://localhost:8000/manage/model/test"
```

### 3. 编程方式切换

```python
from config.models import model_config
from core.model_client import ModelClientFactory

# 切换到 DeepSeek
model_config.current_model_type = "deepseek"
client = ModelClientFactory.create_client("deepseek")

# 切换到 Ollama
model_config.current_model_type = "ollama"
client = ModelClientFactory.create_client("ollama")
```

## 功能特性

### 1. 智能回退

- **聊天功能**: DeepSeek API 提供完整的聊天功能
- **嵌入功能**: DeepSeek 不提供嵌入 API，自动回退到 Ollama 的 nomic-embed-text 模型

### 2. 配置管理

- 所有配置集中在 `config/models.py` 中
- 支持环境变量覆盖默认配置
- 运行时动态切换模型类型

### 3. 错误处理

- API Key 验证
- 连接状态检查
- 优雅的错误提示

## 测试验证

运行测试脚本验证配置：

```bash
python test_deepseek_config.py
```

测试内容包括：
- 配置加载
- 客户端创建
- 功能测试
- 模型切换

## 注意事项

### 1. API 限制

- DeepSeek API 有调用频率限制
- 建议在生产环境中设置合理的重试机制

### 2. 成本控制

- DeepSeek API 按调用次数收费
- 建议设置使用上限和监控

### 3. 网络要求

- 需要稳定的网络连接
- 建议设置超时时间

## 故障排除

### 1. API Key 错误

```
❌ DeepSeek API key 未配置
```

**解决方案**: 检查 `.env` 文件中的 `DEEPSEEK_API_KEY` 设置

### 2. 网络连接失败

```
❌ DeepSeek 聊天完成调用失败: Connection timeout
```

**解决方案**: 检查网络连接和防火墙设置

### 3. 模型切换失败

```
❌ 切换模型失败: 不支持的模型类型
```

**解决方案**: 确保 `model_type` 参数为 "ollama" 或 "deepseek"

## 性能对比

| 特性 | Ollama | DeepSeek API |
|------|--------|--------------|
| 响应速度 | 快（本地） | 中等（网络） |
| 模型质量 | 中等 | 高 |
| 成本 | 低 | 中等 |
| 隐私性 | 高（本地） | 中等（云端） |
| 可用性 | 需要本地部署 | 即开即用 |

## 最佳实践

1. **开发环境**: 使用 Ollama 进行快速迭代
2. **生产环境**: 根据需求选择 Ollama 或 DeepSeek
3. **混合使用**: 关键任务使用 DeepSeek，日常任务使用 Ollama
4. **监控日志**: 定期检查模型切换和调用日志

## 更新日志

- **v1.0**: 初始支持 Ollama
- **v2.0**: 新增 DeepSeek API 支持
- **v2.1**: 优化模型切换体验
- **v2.2**: 增强错误处理和日志记录
