"""
LangGraph 查询处理流程
展示 RAG 查询的流程可控和步骤溯源
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import logging
from datetime import datetime

# 定义查询处理状态
class QueryProcessingState(TypedDict):
    """查询处理流程的状态"""
    # 输入
    user_query: str
    chat_history: List[Dict[str, str]]
    
    # 中间状态
    rewritten_query: Optional[str]
    retrieved_chunks: List[Dict[str, Any]]
    filtered_chunks: List[Dict[str, Any]]
    context_text: Optional[str]
    llm_response: Optional[str]
    
    # 流程控制
    current_step: str
    step_history: List[Dict[str, Any]]
    errors: List[str]
    
    # 输出
    success: bool
    final_response: Optional[str]
    confidence_score: Optional[float]


def rewrite_query_node(state: QueryProcessingState) -> QueryProcessingState:
    """节点1: 查询重写"""
    step_info = {
        "step": "rewrite_query",
        "timestamp": datetime.now().isoformat(),
        "input": {"query": state["user_query"], "history_length": len(state["chat_history"])}
    }
    
    try:
        from core.state import rewrite_input_with_history
        
        # 重写查询
        rewritten_query = rewrite_input_with_history(
            state["user_query"], 
            state["chat_history"]
        )
        
        step_info.update({
            "status": "success",
            "output": {
                "original_query": state["user_query"],
                "rewritten_query": rewritten_query,
                "was_rewritten": rewritten_query != state["user_query"]
            }
        })
        
        return {
            **state,
            "rewritten_query": rewritten_query,
            "current_step": "rewrite_query",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "rewrite_query",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"查询重写失败: {str(e)}"],
            "success": False
        }


def hybrid_retrieve_node(state: QueryProcessingState) -> QueryProcessingState:
    """节点2: 混合检索"""
    step_info = {
        "step": "hybrid_retrieve",
        "timestamp": datetime.now().isoformat(),
        "input": {"query": state["rewritten_query"]}
    }
    
    try:
        from core.vector_store import vector_store
        from core.model_client import get_global_model_client
        
        # 生成查询嵌入
        query_embedding = get_global_model_client().embeddings(state["rewritten_query"])
        
        # 执行混合检索
        fused_results, has_strong_vec = vector_store.hybrid_search(
            state["rewritten_query"],
            query_embedding,
            top_k=10,
            alpha=0.6,
            relevance_threshold=0.4
        )
        
        step_info.update({
            "status": "success",
            "output": {
                "retrieved_count": len(fused_results),
                "has_strong_vector_match": has_strong_vec,
                "top_chunks": [{"content": chunk["content"][:100] + "...", "score": chunk["score"]} 
                              for chunk in fused_results[:3]]
            }
        })
        
        return {
            **state,
            "retrieved_chunks": fused_results,
            "current_step": "hybrid_retrieve",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "hybrid_retrieve",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"混合检索失败: {str(e)}"],
            "success": False
        }


def filter_chunks_node(state: QueryProcessingState) -> QueryProcessingState:
    """节点3: 相关性过滤"""
    step_info = {
        "step": "filter_chunks",
        "timestamp": datetime.now().isoformat(),
        "input": {"retrieved_count": len(state["retrieved_chunks"])}
    }
    
    try:
        from config.models import model_config
        
        # 应用相关性阈值过滤
        filtered_chunks = [
            chunk for chunk in state["retrieved_chunks"]
            if chunk.get("distance", 1.0) <= model_config.max_context_distance
        ]
        
        # 限制上下文长度
        context_text = "\n\n".join([chunk["content"] for chunk in filtered_chunks[:3]])
        
        step_info.update({
            "status": "success",
            "output": {
                "filtered_count": len(filtered_chunks),
                "context_length": len(context_text),
                "threshold": model_config.max_context_distance,
                "context_preview": context_text[:200] + "..." if context_text else ""
            }
        })
        
        return {
            **state,
            "filtered_chunks": filtered_chunks,
            "context_text": context_text,
            "current_step": "filter_chunks",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "filter_chunks",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"相关性过滤失败: {str(e)}"],
            "success": False
        }


def generate_response_node(state: QueryProcessingState) -> QueryProcessingState:
    """节点4: 生成回答"""
    step_info = {
        "step": "generate_response",
        "timestamp": datetime.now().isoformat(),
        "input": {"context_length": len(state["context_text"]) if state["context_text"] else 0}
    }
    
    try:
        from core.model_client import get_global_model_client
        
        # 构建提示词
        if state["context_text"]:
            prompt = f"""基于以下上下文信息回答用户问题：

上下文：
{state["context_text"]}

用户问题：{state["rewritten_query"]}

请基于上下文信息提供准确、有用的回答。如果上下文信息不足以回答问题，请说明。"""
        else:
            prompt = f"""用户问题：{state["rewritten_query"]}

请直接回答用户的问题。"""
        
        # 生成回答
        llm_response = get_global_model_client().chat(prompt)
        
        # 计算置信度（基于上下文相关性）
        confidence_score = 0.8 if state["context_text"] else 0.5
        
        step_info.update({
            "status": "success",
            "output": {
                "response_length": len(llm_response),
                "confidence_score": confidence_score,
                "used_context": bool(state["context_text"])
            }
        })
        
        return {
            **state,
            "llm_response": llm_response,
            "confidence_score": confidence_score,
            "current_step": "generate_response",
            "step_history": state["step_history"] + [step_info],
            "success": True,
            "final_response": llm_response
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "generate_response",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"生成回答失败: {str(e)}"],
            "success": False
        }


def should_continue_query(state: QueryProcessingState) -> str:
    """条件判断：决定查询流程的下一步"""
    if state["errors"]:
        return "error"
    elif state["current_step"] == "rewrite_query":
        return "hybrid_retrieve"
    elif state["current_step"] == "hybrid_retrieve":
        return "filter_chunks"
    elif state["current_step"] == "filter_chunks":
        return "generate_response"
    else:
        return END


def create_query_processing_graph():
    """创建查询处理流程图"""
    
    # 创建状态图
    workflow = StateGraph(QueryProcessingState)
    
    # 添加节点
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("hybrid_retrieve", hybrid_retrieve_node)
    workflow.add_node("filter_chunks", filter_chunks_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # 设置入口点
    workflow.set_entry_point("rewrite_query")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "rewrite_query",
        should_continue_query,
        {
            "hybrid_retrieve": "hybrid_retrieve",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "hybrid_retrieve",
        should_continue_query,
        {
            "filter_chunks": "filter_chunks",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "filter_chunks",
        should_continue_query,
        {
            "generate_response": "generate_response",
            "error": END
        }
    )
    
    workflow.add_edge("generate_response", END)
    
    # 编译图
    from langgraph.checkpoint.memory import MemorySaver
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


def process_query_with_trace(user_query: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """使用 LangGraph 处理查询，返回完整的执行轨迹"""
    
    if chat_history is None:
        chat_history = []
    
    # 创建图
    app = create_query_processing_graph()
    
    # 初始状态
    initial_state = QueryProcessingState(
        user_query=user_query,
        chat_history=chat_history,
        rewritten_query=None,
        retrieved_chunks=[],
        filtered_chunks=[],
        context_text=None,
        llm_response=None,
        current_step="",
        step_history=[],
        errors=[],
        success=False,
        final_response=None,
        confidence_score=None
    )
    
    # 执行流程
    config = {"configurable": {"thread_id": f"query_{datetime.now().timestamp()}"}}
    
    try:
        # 运行流程
        final_state = app.invoke(initial_state, config=config)
        
        # 返回执行轨迹
        return {
            "success": final_state["success"],
            "response": final_state["final_response"],
            "confidence_score": final_state["confidence_score"],
            "execution_trace": {
                "total_steps": len(final_state["step_history"]),
                "steps": final_state["step_history"],
                "errors": final_state["errors"],
                "execution_time": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "response": None,
            "confidence_score": None,
            "execution_trace": {
                "total_steps": len(initial_state["step_history"]),
                "steps": initial_state["step_history"],
                "errors": initial_state["errors"] + [f"流程执行失败: {str(e)}"],
                "execution_time": datetime.now().isoformat()
            }
        }


# 使用示例
if __name__ == "__main__":
    # 示例：处理一个查询
    result = process_query_with_trace("什么是机器学习？")
    
    print("=== 查询执行轨迹 ===")
    print(f"成功: {result['success']}")
    print(f"回答: {result['response']}")
    print(f"置信度: {result['confidence_score']}")
    print(f"总步骤数: {result['execution_trace']['total_steps']}")
    
    for i, step in enumerate(result['execution_trace']['steps']):
        print(f"\n步骤 {i+1}: {step['step']}")
        print(f"  状态: {step['status']}")
        print(f"  时间: {step['timestamp']}")
        if step['status'] == 'success':
            print(f"  输出: {step['output']}")
        else:
            print(f"  错误: {step['error']}")
    
    if result['execution_trace']['errors']:
        print(f"\n错误列表: {result['execution_trace']['errors']}")
