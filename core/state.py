import logging
import os
import io
from typing import List, Dict, Optional, Iterator

import torch
import ollama
from PyPDF2 import PdfReader
from openai import OpenAI


VAULT_PATH = os.environ.get("VAULT_PATH", "vault.txt")
# DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:latest")


def read_vault_lines(vault_path: str) -> List[str]:
    if not os.path.exists(vault_path):
        return []
    with open(vault_path, 'r', encoding='utf-8') as f:
        return f.readlines()


def append_to_vault(vault_path: str, lines: List[str]) -> None:
    if not lines:
        return
    with open(vault_path, 'a', encoding='utf-8') as f:
        for line in lines:
            f.write(line if line.endswith('\n') else line + '\n')


def embed_texts(texts: List[str]) -> torch.Tensor:
    if not texts:
        return torch.empty((0,))
    vectors: List[List[float]] = []
    for content in texts:
        resp = ollama.embeddings(model='nomic-embed-text', prompt=content)
        vectors.append(resp["embedding"])
    return torch.tensor(vectors)


def get_relevant_context(rewritten_input: str, vault_embeddings: torch.Tensor, vault_content: List[str], top_k: int = 3) -> List[str]:
    if vault_embeddings is None or vault_embeddings.nelement() == 0:
        print("vault_embeddings 为空，跳过检索")
        return []
    print(f"开始检索相关上下文，vault_content 长度: {len(vault_content)}")
    input_embedding = ollama.embeddings(model='nomic-embed-text', prompt=rewritten_input)["embedding"]
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)
    top_k = min(top_k, len(cos_scores))
    top_indices = torch.topk(cos_scores, k=top_k)[1].tolist()
    result = [vault_content[idx].strip() for idx in top_indices]
    print(f"检索完成，找到 {len(result)} 个相关片段")
    return result


def rewrite_query(user_input: str, conversation_history: List[Dict[str, str]], client: OpenAI, model: str) -> str:
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
    prompt = f"""请根据以下对话历史，重新组织并改写下面的用户查询。
        改写后的查询应该：

        - 保留原查询的核心意图和含义
        - 让查询更清晰、更具体，便于检索相关上下文信息
        - 不要引入与原查询无关的新话题
        - 请只专注于重新组织语言，不要尝试回答原查询的问题

        请严格按照要求，仅返回改写后的查询文本，不要任何额外解释或格式。

        对话历史：
        {context}

        原始查询：[{user_input}]

        改写后的查询：
        """
    print(f"开始调用 rewrite_query，历史长度: {len(conversation_history)}")
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=2000,
    )
    result = response.choices[0].message.content.strip()
    print(f"rewrite_query 完成，结果: {result}")
    return result


def rewrite_query_stream(user_input: str, conversation_history: List[Dict[str, str]], client: OpenAI, model: str) -> Iterator[str]:
    """流式版本的查询重写函数"""
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
    prompt = f"""请根据以下对话历史，重新组织并改写下面的用户查询。
        改写后的查询应该：

        - 保留原查询的核心意图和含义
        - 让查询更清晰、更具体，便于检索相关上下文信息
        - 不要引入与原查询无关的新话题
        - 请只专注于重新组织语言，不要尝试回答原查询的问题

        请严格按照要求，仅返回改写后的查询文本，不要任何额外解释或格式。

        对话历史：
        {context}

        原始查询：[{user_input}]

        改写后的查询：
        """
    print(f"开始调用 rewrite_query_stream，历史长度: {len(conversation_history)}")
    
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=2000,
        stream=True,
    )
    
    collected = []
    for event in stream:
        delta = getattr(event.choices[0].delta, 'content', None)
        if delta:
            collected.append(delta)
            yield delta
    
    result = "".join(collected).strip()
    print(f"rewrite_query_stream 完成，结果: {result}")


#
# def rag_chat(user_input: str, system_message: str, conversation_history: List[Dict[str, str]],
#              vault_embeddings: torch.Tensor, vault_content: List[str], client: OpenAI, model: str) -> str:
#     conversation_history.append({"role": "user", "content": user_input})
#
#     rewritten_query = user_input if len(conversation_history) <= 1 else rewrite_query(user_input, conversation_history, client, model)
#
#     relevant_context = get_relevant_context(rewritten_query, vault_embeddings, vault_content)
#     context_str = "\n".join(relevant_context) if relevant_context else ""
#
#     user_input_with_context = user_input if not context_str else user_input + "\n\nRelevant Context:\n" + context_str
#     conversation_history[-1]["content"] = user_input_with_context
#
#     messages = [
#         {"role": "system", "content": system_message},
#         *conversation_history
#     ]
#
#     response = client.chat.completions.create(
#         model=model,
#         messages=messages,
#         max_tokens=2000,
#     )
#     answer = response.choices[0].message.content
#     conversation_history.append({"role": "assistant", "content": answer})
#     return answer
#

def rag_chat_stream(user_input: str, system_message: str, conversation_history: List[Dict[str, str]],
                    vault_embeddings: torch.Tensor, vault_content: List[str], client: OpenAI, model: str) -> Iterator[str]:
    """Yield assistant content chunks as they stream in, and update history when done."""
    conversation_history.append({"role": "user", "content": user_input})

    # 如果是多轮对话，先流式重写查询
    if len(conversation_history) > 1:
        print("多轮对话，开始流式重写查询...")
        yield "<think>正在根据对话历史重写查询以更好地检索相关信息...</think>"

        """流式版本的查询重写函数"""
        context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
        prompt = f"""请根据以下对话历史，重新组织并改写下面的用户查询。
                改写后的查询应该：

                - 保留原查询的核心意图和含义
                - 让查询更清晰、更具体，便于检索相关上下文信息
                - 不要引入与原查询无关的新话题
                - 请只专注于重新组织语言，不要尝试回答原查询的问题

                请严格按照要求，仅返回改写后的查询文本，不要任何额外解释或格式。

                对话历史：
                {context}

                原始查询：[{user_input}]

                改写后的查询：
                """
        print(f"开始调用 rewrite_query_stream，历史长度: {len(conversation_history)}")

        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=2000,
            stream=True,
        )

        collected = []
        for event in stream:
            delta = getattr(event.choices[0].delta, 'content', None)
            if delta:
                collected.append(delta)
                yield delta

        rewritten_query = "".join(collected).strip()
        print(f"查询重写完成: {rewritten_query}")
    else:
        rewritten_query = user_input

    # 检索相关上下文
    yield "<think>正在检索相关上下文信息...</think>"
    relevant_context = get_relevant_context(rewritten_query, vault_embeddings, vault_content)
    context_str = "\n".join(relevant_context) if relevant_context else ""
    
    if context_str:
        yield f"<think>找到 {len(relevant_context)} 个相关文档片段</think>"
    else:
        yield "<think>未找到相关上下文信息</think>"

    user_input_with_context = user_input if not context_str else user_input + "\n\nRelevant Context:\n" + context_str
    conversation_history[-1]["content"] = user_input_with_context

    messages = [
        {"role": "system", "content": system_message},
        *conversation_history
    ]

    # 开始生成回答
    yield "<think>正在生成组织之后的回答...</think>"
    
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=2000,
        stream=True,
    )

    collected = []
    for event in stream:
        delta = getattr(event.choices[0].delta, 'content', None)
        if delta:
            collected.append(delta)
            yield delta
    final_answer = "".join(collected)
    conversation_history.append({"role": "assistant", "content": final_answer})


class AppState:
    def __init__(self) -> None:
        self.vault_content: List[str] = []
        self.vault_embeddings: torch.Tensor = torch.empty((0,))
        self.histories: Dict[str, List[Dict[str, str]]] = {}
        self.system_message: str = (
            "你是一个智能助手，擅长从给定文本中提取最有用的信息，并结合上下文回答用户问题。\n"
            "请始终使用中文回答用户的问题，语言要清晰、简洁、专业。\n"
            "如果用户的问题是中文，你的回答也必须是中文。\n"
            "如果用户的问题中包含中英文混合，你仍然优先用中文回答。"
        )
        self.client: OpenAI = OpenAI(base_url='http://localhost:11434/v1', api_key='deepseek-r1:7b')


app_state = AppState()


def initialize_state_on_startup() -> None:
    print("=" * 50)
    print("🚀 正在启动 RAG 服务...")
    print("=" * 50)
    
    # 检查模型服务
    print("\n📋 检查模型服务状态...")
    try:
        # 测试模型连接
        test_response = app_state.client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
        )
        print(f"✅ 模型服务连接成功 - 模型: {DEFAULT_MODEL}")
        print(f"   模型响应测试: {test_response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ 模型服务连接失败: {str(e)}")
        print("   请确保 Ollama 服务正在运行")
        raise
    
    # 检查embedding模型
    print("\n🔍 检查向量嵌入模型...")
    try:
        test_embedding = ollama.embeddings(model='nomic-embed-text', prompt="test")
        embedding_dim = len(test_embedding["embedding"])
        print(f"✅ 向量嵌入模型连接成功 - 模型: nomic-embed-text")
        print(f"   向量维度: {embedding_dim}")
    except Exception as e:
        print(f"❌ 向量嵌入模型连接失败: {str(e)}")
        print("   请确保 Ollama 服务正在运行且包含 nomic-embed-text 模型")
        raise
    
    # 加载向量数据库
    print("\n📚 加载向量数据库...")
    contents = read_vault_lines(VAULT_PATH)
    print(f"   读取文件: {VAULT_PATH}")
    print(f"   文档数量: {len(contents)}")
    
    if len(contents) == 0:
        print("⚠️  警告: 向量数据库为空，请先上传文档")
        app_state.vault_content = []
        app_state.vault_embeddings = torch.empty((0,))
    else:
        print(f"   文档总长度: {sum(len(content) for content in contents)} 字符")
        
        # 生成向量嵌入
        print("\n🔄 生成向量嵌入...")
        try:
            app_state.vault_content = contents
            app_state.vault_embeddings = embed_texts(app_state.vault_content)
            print(f"✅ 向量嵌入生成成功")
            print(f"   向量矩阵形状: {app_state.vault_embeddings.shape}")
            print(f"   向量数量: {app_state.vault_embeddings.shape[0]}")
            print(f"   向量维度: {app_state.vault_embeddings.shape[1]}")
        except Exception as e:
            print(f"❌ 向量嵌入生成失败: {str(e)}")
            raise
    
    print("\n" + "=" * 50)
    print("🎉 RAG 服务启动成功！")
    print("=" * 50)


