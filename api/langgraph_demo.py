"""
LangGraph 演示 API
展示流程可控和步骤溯源的实际效果
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List, Dict, Any
import json
from datetime import datetime

from core.langgraph_document_flow import process_document_with_trace
from core.langgraph_query_flow import process_query_with_trace

router = APIRouter()


@router.post("/langgraph/upload-document")
async def upload_document_with_trace(
    file: UploadFile = File(...),
    file_type: str = "unknown"
) -> Dict[str, Any]:
    """
    使用 LangGraph 处理文档上传，返回完整的执行轨迹
    """
    try:
        # 读取文件内容
        file_bytes = await file.read()
        
        # 使用 LangGraph 处理文档
        result = process_document_with_trace(
            file_bytes=file_bytes,
            filename=file.filename,
            file_type=file_type
        )
        
        return {
            "success": result["success"],
            "filename": file.filename,
            "result": result["result"],
            "execution_trace": result["execution_trace"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.post("/langgraph/query")
async def query_with_trace(
    query: str,
    chat_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    使用 LangGraph 处理查询，返回完整的执行轨迹
    """
    try:
        if chat_history is None:
            chat_history = []
        
        # 使用 LangGraph 处理查询
        result = process_query_with_trace(
            user_query=query,
            chat_history=chat_history
        )
        
        return {
            "success": result["success"],
            "query": query,
            "response": result["response"],
            "confidence_score": result["confidence_score"],
            "execution_trace": result["execution_trace"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询处理失败: {str(e)}")


@router.get("/langgraph/trace/{trace_id}")
async def get_execution_trace(trace_id: str) -> Dict[str, Any]:
    """
    获取特定执行轨迹的详细信息
    """
    # 这里可以从数据库或缓存中获取轨迹信息
    # 目前返回示例数据
    return {
        "trace_id": trace_id,
        "status": "completed",
        "total_steps": 4,
        "execution_time": "2024-01-15T10:30:00Z",
        "steps": [
            {
                "step": "convert_document",
                "status": "success",
                "timestamp": "2024-01-15T10:30:01Z",
                "duration_ms": 1200,
                "input": {"filename": "test.pdf", "file_type": "pdf"},
                "output": {"text_length": 5000, "preview": "This is a test document..."}
            },
            {
                "step": "chunk_text",
                "status": "success", 
                "timestamp": "2024-01-15T10:30:02Z",
                "duration_ms": 800,
                "input": {"text_length": 5000},
                "output": {"chunk_count": 8, "chunk_preview": "This is the first chunk..."}
            },
            {
                "step": "generate_embeddings",
                "status": "success",
                "timestamp": "2024-01-15T10:30:03Z", 
                "duration_ms": 2000,
                "input": {"chunk_count": 8},
                "output": {"embedding_count": 8, "embedding_dim": 1536}
            },
            {
                "step": "store_chunks",
                "status": "success",
                "timestamp": "2024-01-15T10:30:05Z",
                "duration_ms": 500,
                "input": {"chunk_count": 8},
                "output": {"stored_count": 8}
            }
        ],
        "errors": [],
        "performance_metrics": {
            "total_duration_ms": 4500,
            "avg_step_duration_ms": 1125,
            "memory_usage_mb": 45.2,
            "cpu_usage_percent": 15.8
        }
    }


@router.get("/langgraph/visualization/{trace_id}")
async def get_flow_visualization(trace_id: str) -> Dict[str, Any]:
    """
    获取流程可视化数据（用于前端展示流程图）
    """
    return {
        "trace_id": trace_id,
        "flow_type": "document_processing",
        "nodes": [
            {
                "id": "convert_document",
                "label": "文档转换",
                "status": "completed",
                "position": {"x": 100, "y": 100}
            },
            {
                "id": "chunk_text", 
                "label": "文本分块",
                "status": "completed",
                "position": {"x": 300, "y": 100}
            },
            {
                "id": "generate_embeddings",
                "label": "生成嵌入",
                "status": "completed", 
                "position": {"x": 500, "y": 100}
            },
            {
                "id": "store_chunks",
                "label": "存储块",
                "status": "completed",
                "position": {"x": 700, "y": 100}
            }
        ],
        "edges": [
            {"from": "convert_document", "to": "chunk_text", "status": "success"},
            {"from": "chunk_text", "to": "generate_embeddings", "status": "success"},
            {"from": "generate_embeddings", "to": "store_chunks", "status": "success"}
        ],
        "execution_path": ["convert_document", "chunk_text", "generate_embeddings", "store_chunks"]
    }


@router.get("/langgraph/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """
    获取系统性能指标
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "document_processing": {
            "total_processed": 1250,
            "success_rate": 0.98,
            "avg_processing_time_ms": 3200,
            "error_rate": 0.02
        },
        "query_processing": {
            "total_queries": 5670,
            "success_rate": 0.95,
            "avg_response_time_ms": 1200,
            "avg_confidence_score": 0.82
        },
        "system_resources": {
            "memory_usage_mb": 1024,
            "cpu_usage_percent": 25.5,
            "active_connections": 12,
            "queue_size": 3
        }
    }
