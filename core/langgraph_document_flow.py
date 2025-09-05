"""
LangGraph 文档处理流程
展示流程可控和步骤溯源的核心价值
"""

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
import logging
from datetime import datetime

# 定义状态结构
class DocumentProcessingState(TypedDict):
    """文档处理流程的状态"""
    # 输入
    file_bytes: bytes
    filename: str
    file_type: str
    
    # 中间状态
    raw_text: Optional[str]
    chunks: List[str]
    embeddings: List[List[float]]
    chunk_count: int
    
    # 流程控制
    current_step: str
    step_history: List[Dict[str, Any]]
    errors: List[str]
    
    # 输出
    success: bool
    final_result: Optional[Dict[str, Any]]


def convert_document_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """节点1: 文档转换"""
    step_info = {
        "step": "convert_document",
        "timestamp": datetime.now().isoformat(),
        "input": {"filename": state["filename"], "file_type": state["file_type"]}
    }
    
    try:
        # 根据文件类型选择处理方式
        if state["file_type"] == "text":
            # 对于文本文件，直接解码字节内容
            raw_text = state["file_bytes"].decode("utf-8")
        else:
            # 对于其他文件类型，使用docling处理
            from core.document_ingest import export_to_text
            raw_text = export_to_text(state["file_bytes"], state["filename"])
        
        step_info.update({
            "status": "success",
            "output": {"text_length": len(raw_text), "preview": raw_text[:1000] + ("..." if len(raw_text) > 1000 else "")}
        })
        
        return {
            **state,
            "raw_text": raw_text,
            "current_step": "convert_document",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "convert_document",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"文档转换失败: {str(e)}"],
            "success": False
        }


def chunk_text_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """节点2: 文本分块"""
    step_info = {
        "step": "chunk_text",
        "timestamp": datetime.now().isoformat(),
        "input": {"text_length": len(state["raw_text"]) if state["raw_text"] else 0}
    }
    
    try:
        from core.document_ingest import chunk_text_from_export
        
        # 执行文本分块
        chunks = chunk_text_from_export(
            state["raw_text"], 
            max_tokens=800, 
            min_tokens=120  # 使用默认的最小token数
        )
        
        step_info.update({
            "status": "success",
            "output": {
                "chunk_count": len(chunks), 
                "chunks": chunks  # 返回所有分块数据
            }
        })
        
        return {
            **state,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "current_step": "chunk_text",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "chunk_text",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"文本分块失败: {str(e)}"],
            "success": False
        }


def generate_embeddings_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """节点3: 生成向量嵌入"""
    step_info = {
        "step": "generate_embeddings",
        "timestamp": datetime.now().isoformat(),
        "input": {"chunk_count": state["chunk_count"]}
    }
    
    try:
        from core.model_client import get_global_model_client
        
        # 生成向量嵌入
        embeddings = []
        for i, chunk in enumerate(state["chunks"]):
            embedding = get_global_model_client().embeddings(chunk)
            embeddings.append(embedding)
            
            # 记录进度
            if i % 10 == 0:
                logging.info(f"生成嵌入进度: {i+1}/{len(state['chunks'])}")
        
        step_info.update({
            "status": "success",
            "output": {"embedding_count": len(embeddings), "embedding_dim": len(embeddings[0]) if embeddings else 0}
        })
        
        return {
            **state,
            "embeddings": embeddings,
            "current_step": "generate_embeddings",
            "step_history": state["step_history"] + [step_info]
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "generate_embeddings",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"生成嵌入失败: {str(e)}"],
            "success": False
        }


def store_chunks_node(state: DocumentProcessingState) -> DocumentProcessingState:
    """节点4: 存储文本块"""
    step_info = {
        "step": "store_chunks",
        "timestamp": datetime.now().isoformat(),
        "input": {"chunk_count": state["chunk_count"]}
    }
    
    try:
        from core.vector_store import vector_store
        
        # 存储到向量数据库
        stored_count = vector_store.store_chunks(
            state["chunks"], 
            state["filename"], 
            file_type=state["file_type"]
        )
        
        step_info.update({
            "status": "success",
            "output": {"stored_count": stored_count}
        })
        
        return {
            **state,
            "current_step": "store_chunks",
            "step_history": state["step_history"] + [step_info],
            "success": True,
            "final_result": {
                "filename": state["filename"],
                "chunks_created": state["chunk_count"],
                "chunks_stored": stored_count,
                "processing_time": sum(1 for step in state["step_history"] if step["status"] == "success")
            }
        }
        
    except Exception as e:
        step_info.update({
            "status": "error",
            "error": str(e)
        })
        
        return {
            **state,
            "current_step": "store_chunks",
            "step_history": state["step_history"] + [step_info],
            "errors": state["errors"] + [f"存储失败: {str(e)}"],
            "success": False
        }


def should_continue(state: DocumentProcessingState) -> str:
    """条件判断：决定是否继续流程"""
    if state["errors"]:
        return "error"
    elif state["current_step"] == "convert_document":
        return "chunk_text"
    elif state["current_step"] == "chunk_text":
        return "generate_embeddings"
    elif state["current_step"] == "generate_embeddings":
        return "store_chunks"
    else:
        return END


def create_document_processing_graph():
    """创建文档处理流程图"""
    
    # 创建状态图
    workflow = StateGraph(DocumentProcessingState)
    
    # 添加节点
    workflow.add_node("convert_document", convert_document_node)
    workflow.add_node("chunk_text", chunk_text_node)
    workflow.add_node("generate_embeddings", generate_embeddings_node)
    workflow.add_node("store_chunks", store_chunks_node)
    
    # 设置入口点
    workflow.set_entry_point("convert_document")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "convert_document",
        should_continue,
        {
            "chunk_text": "chunk_text",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "chunk_text",
        should_continue,
        {
            "generate_embeddings": "generate_embeddings",
            "error": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_embeddings",
        should_continue,
        {
            "store_chunks": "store_chunks",
            "error": END
        }
    )
    
    workflow.add_edge("store_chunks", END)
    
    # 编译图
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


def process_document_with_trace(file_bytes: bytes, filename: str, file_type: str = "unknown") -> Dict[str, Any]:
    """使用 LangGraph 处理文档，返回完整的执行轨迹"""
    
    # 创建图
    app = create_document_processing_graph()
    
    # 初始状态
    initial_state = DocumentProcessingState(
        file_bytes=file_bytes,
        filename=filename,
        file_type=file_type,
        raw_text=None,
        chunks=[],
        embeddings=[],
        chunk_count=0,
        current_step="",
        step_history=[],
        errors=[],
        success=False,
        final_result=None
    )
    
    # 执行流程
    config = {"configurable": {"thread_id": f"doc_{filename}_{datetime.now().timestamp()}"}}
    
    try:
        # 运行流程
        final_state = app.invoke(initial_state, config=config)
        
        # 返回执行轨迹
        return {
            "success": final_state["success"],
            "result": final_state["final_result"],
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
            "result": None,
            "execution_trace": {
                "total_steps": len(initial_state["step_history"]),
                "steps": initial_state["step_history"],
                "errors": initial_state["errors"] + [f"流程执行失败: {str(e)}"],
                "execution_time": datetime.now().isoformat()
            }
        }


# 使用示例
if __name__ == "__main__":
    # 示例：处理一个文档
    with open("test/test_notion.txt", "rb") as f:
        file_bytes = f.read()
    
    result = process_document_with_trace(file_bytes, "test_notion.txt", "text")
    
    print("=== 执行轨迹 ===")
    print(f"成功: {result['success']}")
    print(f"结果: {result['result']}")
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
