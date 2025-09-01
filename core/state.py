import logging
import os
import io
from typing import List, Dict, Optional, Iterator

import torch
import ollama
from PyPDF2 import PdfReader
from openai import OpenAI

from core.vector_store import vector_store
from config.database import init_database, get_chunk_count


# DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1:7b")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:latest")  # 可使用更小的模型


# vector_store
def get_relevant_context(rewritten_input: str, top_k: int = 3) -> List[str]:
    import time
    
    print(f"开始检索相关上下文")
    
    # 测量向量嵌入生成时间
    embedding_start = time.time()
    
    # 检查缓存
    if rewritten_input in app_state.query_embedding_cache:
        input_embedding = app_state.query_embedding_cache[rewritten_input]
        print(f"📊 使用缓存的向量嵌入")
    else:
        resp = ollama.embeddings(model='nomic-embed-text', prompt=rewritten_input)
        # 确保向量是浮点数列表
        input_embedding = [float(x) for x in resp["embedding"]]
        app_state.query_embedding_cache[rewritten_input] = input_embedding
        print(f"📊 生成新的向量嵌入并缓存")
    
    embedding_time = time.time() - embedding_start
    print(f"📊 向量嵌入处理耗时: {embedding_time:.2f}秒")
    
    # 测量向量检索时间
    retrieval_start = time.time()
    similar_chunks = vector_store.search_similar(input_embedding, top_k)
    retrieval_time = time.time() - retrieval_start
    print(f"🔍 向量检索耗时: {retrieval_time:.2f}秒")
    
    result = [chunk['content'].strip() for chunk in similar_chunks]
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
                    client: OpenAI, model: str) -> Iterator[str]:
    """Yield assistant content chunks as they stream in, and update history when done."""
    import time
    start_time = time.time()
    
    conversation_history.append({"role": "user", "content": user_input})

    # 如果是多轮对话，先流式重写查询
    # if len(conversation_history) > 1:
    #     print("多轮对话，开始流式重写查询...")
    #     yield "<think>正在根据对话历史重写查询以更好地检索相关信息...</think>"
    #
    #     """流式版本的查询重写函数"""
    #     context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
    #     prompt = f"""请根据以下对话历史，重新组织并改写下面的用户查询。
    #             改写后的查询应该：
    #
    #             - 保留原查询的核心意图和含义
    #             - 让查询更清晰、更具体，便于检索相关上下文信息
    #             - 不要引入与原查询无关的新话题
    #             - 请只专注于重新组织语言，不要尝试回答原查询的问题
    #
    #             请严格按照要求，仅返回改写后的查询文本，不要任何额外解释或格式。
    #
    #             对话历史：
    #             {context}
    #
    #             原始查询：[{user_input}]
    #
    #             改写后的查询：
    #             """
    #     print(f"开始调用 rewrite_query_stream，历史长度: {len(conversation_history)}")
    #
    #     if app_state.model_loaded:
    #         print(f"🔄 查询重写使用预加载模型")
    #     else:
    #         print(f"🔄 查询重写首次加载模型")
    #
    #     stream = client.chat.completions.create(
    #         model=model,
    #         messages=[{"role": "system", "content": prompt}],
    #         max_tokens=2000,
    #         stream=True,
    #     )
    #
    #     collected = []
    #     for event in stream:
    #         delta = getattr(event.choices[0].delta, 'content', None)
    #         if delta:
    #             collected.append(delta)
    #             yield delta
    #
    #     rewritten_query = "".join(collected).strip()
    #     print(f"查询重写完成: {rewritten_query}")
    # else:
    #     rewritten_query = user_input
    rewritten_query = user_input
    # 检索相关上下文
    yield "<think>正在检索相关上下文信息...</think>"
    retrieval_start = time.time()
    relevant_context = get_relevant_context(rewritten_query)
    retrieval_time = time.time() - retrieval_start
    print(f"🔍 向量检索耗时: {retrieval_time:.2f}秒")
    # 合并上下文并做硬阈值裁剪，避免不同查询因为上下文长度大幅度放大推理时延
    context_str = "\n".join(relevant_context) if relevant_context else ""
    MAX_CONTEXT_CHARS = int(os.environ.get("MAX_CONTEXT_CHARS", "1200"))
    if len(context_str) > MAX_CONTEXT_CHARS:
        context_str = context_str[:MAX_CONTEXT_CHARS]
    
    if context_str:
        yield f"<think>找到 {len(relevant_context)} 个相关文档片段</think>"
        user_input_with_context = user_input + "\n\nRelevant Context:\n" + context_str
    else:
        yield "<think>未找到相关上下文信息，将直接回答</think>"
        user_input_with_context = user_input
    conversation_history[-1]["content"] = user_input_with_context

    messages = [
        {"role": "system", "content": system_message},
        *conversation_history
    ]

    # 开始生成回答
    yield "<think>正在生成AI分析回答...</think>"
    
    generation_start = time.time()
    if app_state.model_loaded:
        print(f"🚀 开始调用模型生成... (模型已预加载)")
    else:
        print(f"🚀 开始调用模型生成... (首次加载)")
    # 通过 extra_body 传递给 Ollama，保持模型常驻并限制上下文
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=int(os.environ.get("MAX_GENERATE_TOKENS", "800")),
        stream=True,
        extra_body={
            "keep_alive": "30m",
            # 根据机器调整，较小的上下文更快；如需更大可提高
            "options": {
                "num_ctx": int(os.environ.get("NUM_CTX", "2048")),
                # 控制生成长度，避免长回答导致耗时上升
                "num_predict": int(os.environ.get("NUM_PREDICT", "800")),
                # 合理利用 CPU 线程
                "num_threads": max(1, __import__('os').cpu_count() or 1)
            }
        },
    )

    # 更精确的首 token 延迟与总体耗时
    ttft = None
    collected = []
    for event in stream:
        delta = getattr(event.choices[0].delta, 'content', None)
        if delta:
            if ttft is None:
                ttft = time.time() - generation_start
                print(f"⚡ 首token延迟(TTFT): {ttft:.2f}秒")
            collected.append(delta)
            yield delta
    final_answer = "".join(collected)
    conversation_history.append({"role": "assistant", "content": final_answer})
    total_time = time.time() - start_time
    gen_time = time.time() - generation_start
    print(f"🤖 模型生成耗时: {gen_time:.2f}秒")
    print(f"🎯 总耗时: {total_time:.2f}秒")


class AppState:
    def __init__(self) -> None:
        self.histories: Dict[str, List[Dict[str, str]]] = {}
        self.query_embedding_cache: Dict[str, List[float]] = {}  # 缓存查询向量嵌入
        self.model_loaded: bool = False  # 标记模型是否已加载
        self.system_message: str = (
            "你是一个智能助手，擅长从给定文本中提取最有用的信息，并结合上下文回答用户问题。\n"
            "请始终使用中文回答用户的问题，语言要清晰、简洁、专业。\n"
            "如果用户的问题是中文，你的回答也必须是中文。\n"
            "如果用户的问题中包含中英文混合，你仍然优先用中文回答。"
        )
        self.client: OpenAI = OpenAI(base_url='http://localhost:11434/v1', api_key='llama3')


app_state = AppState()


def initialize_state_on_startup() -> None:
    print("=" * 50)
    print("🚀 正在启动 RAG 服务...")
    print("=" * 50)
    
    # 初始化数据库
    print("\n🗄️  初始化数据库...")
    try:
        init_database()
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {str(e)}")
        print("   请确保 PostgreSQL 服务正在运行且已安装 pgvector 扩展")
        raise
    
    # 预加载模型
    # print("\n🔥 预加载模型...")
    # try:
    #     import time
    #     warmup_start = time.time()
        
    #     # 发送一个简单的请求来预加载模型
    #     test_response = app_state.client.chat.completions.create(
    #         model=DEFAULT_MODEL,
    #         messages=[{"role": "user", "content": "你好"}],
    #         max_tokens=10,
    #     )
        
    #     warmup_time = time.time() - warmup_start
    #     print(f"✅ 模型预加载完成，耗时: {warmup_time:.2f}秒")
    #     print(f"   模型: {DEFAULT_MODEL}")
    #     print(f"   模型响应测试: {test_response.choices[0].message.content}")
    #     app_state.model_loaded = True
        
    # except Exception as e:
    #     print(f"❌ 模型预加载失败: {str(e)}")
    #     print("   请确保 Ollama 服务正在运行")
    #     raise
    
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
    
    # 检查向量数据库状态
    print("\n📚 检查向量数据库状态...")
    try:
        chunk_count = get_chunk_count()
        print(f"✅ 向量数据库连接成功")
        print(f"   当前文档块数量: {chunk_count}")
        if chunk_count == 0:
            print("⚠️  警告: 向量数据库为空，请先上传文档")
    except Exception as e:
        print(f"❌ 向量数据库连接失败: {str(e)}")
        raise
    
    print("\n" + "=" * 50)
    print("🎉 RAG 服务启动成功！")
    print("=" * 50)


