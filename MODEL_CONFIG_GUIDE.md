# 模型配置使用指南

本项目支持两种大模型调用方式：**Ollama** 和 **DeepSeek API**。在初始化时会自动加载大模型配置，所有配置都集中在 `config` 目录中管理。

## 🚀 快速开始

### 1. 环境变量配置

复制 `env.example` 为 `.env` 并配置：

```bash
# 选择模型类型: "ollama" 或 "deepseek"
MODEL_TYPE=ollama

# Ollama 配置
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=llama3
OLLAMA_MODEL=llama3:latest
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# DeepSeek API 配置
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
```

### 2. 启动服务

```bash
# 启动 Docker 服务
./start.sh

# 启动 Python 应用
python main.py
```

## 🔧 配置详解

### Ollama 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `OLLAMA_BASE_URL` | Ollama 服务地址 | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | 聊天模型名称 | `llama3:latest` |
| `OLLAMA_EMBEDDING_MODEL` | 嵌入模型名称 | `nomic-embed-text` |
| `OLLAMA_KEEP_ALIVE` | 模型保持活跃时间 | `30m` |
| `OLLAMA_NUM_CTX` | 上下文长度 | `2048` |
| `OLLAMA_NUM_PREDICT` | 预测长度 | `800` |

### DeepSeek 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |
| `DEEPSEEK_API_KEY` | API 密钥 | 需要设置 |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-chat` |
| `DEEPSEEK_MAX_TOKENS` | 最大生成令牌 | `800` |
| `DEEPSEEK_TEMPERATURE` | 温度参数 | `0.7` |
| `DEEPSEEK_TOP_P` | Top-P 参数 | `0.9` |

### RAG 配置

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `TOP_K` | 检索相关文档数量 | `2` |
| `MAX_CONTEXT_CHARS` | 最大上下文字符数 | `1200` |
| `MAX_GENERATE_TOKENS` | 最大生成令牌数 | `800` |

## 🔄 运行时切换模型

### 1. 查看当前配置

```bash
curl http://localhost:8000/manage/model/config
```

### 2. 切换模型类型

```bash
# 切换到 DeepSeek
curl -X POST "http://localhost:8000/manage/model/switch?model_type=deepseek"

# 切换到 Ollama
curl -X POST "http://localhost:8000/manage/model/switch?model_type=ollama"
```

### 3. 测试模型连接

```bash
curl http://localhost:8000/manage/model/test
```

## 📁 配置文件结构

```
config/
├── models.py          # 模型配置类定义
├── database.py        # 数据库配置
└── __init__.py

core/
├── model_client.py    # 模型客户端工厂
├── state.py          # 应用状态管理
└── vector_store.py   # 向量存储
```

## 🔍 代码架构

### 配置加载流程

1. **启动时加载**: `config/models.py` 中的 `load_model_config()` 函数
2. **环境变量覆盖**: 支持通过环境变量覆盖默认配置
3. **动态配置**: 运行时可以通过 API 切换模型类型

### 客户端工厂模式

```python
from core.model_client import ModelClientFactory

# 创建指定类型的客户端
ollama_client = ModelClientFactory.create_client("ollama")
deepseek_client = ModelClientFactory.create_client("deepseek")

# 获取当前配置的客户端
current_client = ModelClientFactory.get_current_client()
```

### 统一接口

所有模型客户端都实现相同的接口：

```python
class BaseModelClient(ABC):
    @abstractmethod
    def chat_completion(self, messages, stream=False, **kwargs):
        """聊天完成接口"""
        pass
    
    @abstractmethod
    def embeddings(self, text):
        """生成文本嵌入向量"""
        pass
```

## 🧪 测试

运行测试脚本验证配置：

```bash
python test_model_config.py
```

## 🚨 注意事项

1. **DeepSeek 嵌入**: DeepSeek 目前不提供嵌入 API，会自动使用 Ollama 作为备选
2. **API Key 安全**: 不要在代码中硬编码 API Key，使用环境变量
3. **模型切换**: 切换模型类型会重新创建客户端，确保新配置有效
4. **错误处理**: 所有模型调用都有异常处理，失败时会返回详细错误信息

## 🔧 故障排除

### 常见问题

1. **Ollama 连接失败**
   - 检查 Ollama 服务是否运行
   - 验证 `OLLAMA_BASE_URL` 配置

2. **DeepSeek API 调用失败**
   - 检查 API Key 是否正确设置
   - 验证网络连接和 API 地址

3. **嵌入生成失败**
   - 检查嵌入模型是否可用
   - 验证模型配置参数

### 调试模式

启用详细日志：

```bash
export LOG_LEVEL=DEBUG
python main.py
```

## 📚 扩展支持

### 添加新的模型类型

1. 在 `config/models.py` 中添加新的配置类
2. 在 `core/model_client.py` 中实现对应的客户端类
3. 在 `ModelClientFactory` 中添加创建逻辑

### 自定义配置

可以通过继承配置类来自定义特定需求：

```python
class CustomOllamaConfig(OllamaConfig):
    def __init__(self):
        super().__init__()
        self.custom_param = "custom_value"
```

## 📞 支持

如有问题，请查看：
- 项目 README
- API 文档 (Swagger UI)
- 测试脚本输出
- 应用日志
