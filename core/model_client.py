"""
模型客户端工厂
支持 Ollama 和 DeepSeek 两种方式调用大模型
"""

import logging
from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any
from openai import OpenAI
import ollama

from config.models import model_config, OllamaConfig, DeepSeekConfig


logger = logging.getLogger(__name__)


class BaseModelClient(ABC):
    """模型客户端基类"""
    
    @abstractmethod
    def chat_completion(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Any:
        """聊天完成接口"""
        pass
    
    @abstractmethod
    def embeddings(self, text: str) -> List[float]:
        """生成文本嵌入向量"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass


class OllamaClient(BaseModelClient):
    """Ollama 客户端"""
    
    def __init__(self, config: OllamaConfig):
        self.config = config
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key
        )
    
    def chat_completion(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Any:
        """Ollama 聊天完成接口"""
        try:
            # 合并配置参数
            extra_body = {
                "keep_alive": self.config.keep_alive,
                "options": {
                    "num_ctx": self.config.num_ctx,
                    "num_predict": self.config.num_predict,
                    "num_threads": self.config.num_threads
                }
            }
            
            # 如果传入了其他参数，覆盖默认配置
            if 'extra_body' in kwargs:
                extra_body.update(kwargs['extra_body'])
                del kwargs['extra_body']
            
            return self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                stream=stream,
                extra_body=extra_body,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Ollama 聊天完成调用失败: {str(e)}")
            raise
    
    def embeddings(self, text: str) -> List[float]:
        """Ollama 文本嵌入接口"""
        try:
            response = ollama.embeddings(
                model=self.config.embedding_model,
                prompt=text
            )
            # 确保返回浮点数列表
            return [float(x) for x in response["embedding"]]
        except Exception as e:
            logger.error(f"Ollama 嵌入生成失败: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取 Ollama 模型信息"""
        return {
            "type": "ollama",
            "model": self.config.model,
            "embedding_model": self.config.embedding_model,
            "base_url": self.config.base_url,
            "num_ctx": self.config.num_ctx,
            "num_predict": self.config.num_predict
        }


class DeepSeekClient(BaseModelClient):
    """DeepSeek API 客户端"""
    
    def __init__(self, config: DeepSeekConfig):
        self.config = config
        if not config.api_key:
            raise ValueError("DeepSeek API key 不能为空")
        
        self.client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key
        )
    
    def chat_completion(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Any:
        """DeepSeek 聊天完成接口"""
        try:
            # 合并配置参数
            params = {
                "model": self.config.model,
                "messages": messages,
                "stream": stream,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p
            }
            
            # 如果传入了其他参数，覆盖默认配置
            params.update(kwargs)
            
            return self.client.chat.completions.create(**params)
        except Exception as e:
            logger.error(f"DeepSeek 聊天完成调用失败: {str(e)}")
            raise
    
    def embeddings(self, text: str) -> List[float]:
        """DeepSeek 文本嵌入接口"""
        try:
            # DeepSeek 目前不提供嵌入 API，使用 Ollama 作为备选
            # 这里可以配置使用其他嵌入服务
            logger.warning("DeepSeek 不提供嵌入 API，使用 Ollama 作为备选")
            fallback_client = OllamaClient(model_config.ollama)
            return fallback_client.embeddings(text)
        except Exception as e:
            logger.error(f"DeepSeek 嵌入生成失败: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取 DeepSeek 模型信息"""
        return {
            "type": "deepseek",
            "model": self.config.model,
            "base_url": self.config.base_url,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p
        }


class ModelClientFactory:
    """模型客户端工厂"""
    
    @staticmethod
    def create_client(model_type: str = None) -> BaseModelClient:
        """创建模型客户端"""
        if model_type is None:
            model_type = model_config.current_model_type
        
        if model_type == "ollama":
            return OllamaClient(model_config.ollama)
        elif model_type == "deepseek":
            return DeepSeekClient(model_config.deepseek)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")
    
    @staticmethod
    def get_current_client() -> BaseModelClient:
        """获取当前配置的模型客户端"""
        return ModelClientFactory.create_client()


# 全局模型客户端实例
model_client = ModelClientFactory.get_current_client()


# 全局模型客户端实例
def get_global_model_client():
    """获取全局模型客户端，支持动态重新加载"""
    return ModelClientFactory.get_current_client()
