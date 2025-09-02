"""
模型配置文件
支持 Ollama 和 DeepSeek API 两种方式调用大模型
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# 提前读取 .env 文件（若存在）
load_dotenv()


@dataclass
class OllamaConfig:
    """Ollama 配置"""
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "llama3"
    model: str = "llama3:latest"
    embedding_model: str = "nomic-embed-text"
    
    # Ollama 特定配置
    keep_alive: str = "30m"
    num_ctx: int = 2048
    num_predict: int = 800
    num_threads: Optional[int] = None
    
    def __post_init__(self):
        if self.num_threads is None:
            import os
            self.num_threads = max(1, os.cpu_count() or 1)


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    
    # DeepSeek 特定配置
    max_tokens: int = 800
    temperature: float = 0.7
    top_p: float = 0.9


@dataclass
class ModelConfig:
    """模型配置主类"""
    # 当前使用的模型类型: "ollama" 或 "deepseek"
    current_model_type: str = "ollama"
    
    # 模型配置
    ollama: OllamaConfig = None
    deepseek: DeepSeekConfig = None
    
    # 通用配置
    system_message: str = (
        "你是一个智能助手，擅长从给定文本中提取最有用的信息，并结合上下文回答用户问题。\n"
        "请始终使用中文回答用户的问题，语言要清晰、简洁、专业。\n"
        "如果用户的问题是中文，你的回答也必须是中文。\n"
        "如果用户的问题中包含中英文混合，你仍然优先用中文回答。"
    )
    
    # RAG 相关配置
    top_k: int = 2
    max_context_chars: int = 1200
    max_generate_tokens: int = 800
    
    def __post_init__(self):
        if self.ollama is None:
            self.ollama = OllamaConfig()
        if self.deepseek is None:
            self.deepseek = DeepSeekConfig()


def load_model_config() -> ModelConfig:
    """从环境变量和配置文件加载模型配置"""
    config = ModelConfig()
    
    # 从环境变量加载配置
    config.current_model_type = os.environ.get("MODEL_TYPE", "ollama")
    
    # Ollama 配置
    config.ollama.base_url = os.environ.get("OLLAMA_BASE_URL", config.ollama.base_url)
    config.ollama.api_key = os.environ.get("OLLAMA_API_KEY", config.ollama.api_key)
    config.ollama.model = os.environ.get("OLLAMA_MODEL", config.ollama.model)
    config.ollama.embedding_model = os.environ.get("OLLAMA_EMBEDDING_MODEL", config.ollama.embedding_model)
    config.ollama.keep_alive = os.environ.get("OLLAMA_KEEP_ALIVE", config.ollama.keep_alive)
    config.ollama.num_ctx = int(os.environ.get("OLLAMA_NUM_CTX", config.ollama.num_ctx))
    config.ollama.num_predict = int(os.environ.get("OLLAMA_NUM_PREDICT", config.ollama.num_predict))
    
    # DeepSeek 配置
    config.deepseek.base_url = os.environ.get("DEEPSEEK_BASE_URL", config.deepseek.base_url)
    config.deepseek.api_key = os.environ.get("DEEPSEEK_API_KEY", config.deepseek.api_key)
    config.deepseek.model = os.environ.get("DEEPSEEK_MODEL", config.deepseek.model)
    config.deepseek.max_tokens = int(os.environ.get("DEEPSEEK_MAX_TOKENS", config.deepseek.max_tokens))
    config.deepseek.temperature = float(os.environ.get("DEEPSEEK_TEMPERATURE", config.deepseek.temperature))
    config.deepseek.top_p = float(os.environ.get("DEEPSEEK_TOP_P", config.deepseek.top_p))
    
    # 通用配置
    config.top_k = int(os.environ.get("TOP_K", config.top_k))
    config.max_context_chars = int(os.environ.get("MAX_CONTEXT_CHARS", config.max_context_chars))
    config.max_generate_tokens = int(os.environ.get("MAX_GENERATE_TOKENS", config.max_generate_tokens))
    
    # 系统消息
    system_msg = os.environ.get("SYSTEM_MESSAGE")
    if system_msg:
        config.system_message = system_msg
    
    return config


# 全局配置实例
model_config = load_model_config()
