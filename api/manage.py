from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.vector_store import vector_store
from config.database import get_chunk_count, clear_all_chunks, delete_trace_data
from config.models import model_config
from core.model_client import ModelClientFactory

router = APIRouter(prefix="/manage", tags=["manage"])


@router.get("/files")
async def get_files() -> List[Dict]:
    """获取已上传文件的聚合信息：文件名、类型、chunk 数、首次/最后上传时间"""
    try:
        files = vector_store.get_file_list()
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@router.get("/stats")
async def get_stats() -> Dict:
    """获取整体统计信息：总chunk数与文件汇总列表"""
    try:
        chunk_count = get_chunk_count()
        files = vector_store.get_file_list()
        
        return {
            "total_chunks": chunk_count,
            "total_files": len(files),
            "files": files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.delete("/files/{file_name}")
async def delete_file(file_name: str) -> Dict:
    """删除指定文件的所有文档块和轨迹数据，返回删除数量"""
    try:
        # 删除向量数据
        deleted_chunks = vector_store.delete_file_chunks(file_name)
        
        # 删除轨迹数据
        trace_deleted = delete_trace_data(file_name)
        
        return {
            "message": f"成功删除文件 {file_name}",
            "deleted_chunks": deleted_chunks,
            "trace_deleted": trace_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.delete("/all")
async def clear_all() -> Dict:
    """清空所有文档块（谨慎操作）"""
    try:
        clear_all_chunks()
        return {
            "message": "成功清空所有文档块"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空文档块失败: {str(e)}")


@router.get("/files/{file_name}/chunks")
async def get_file_chunks(
    file_name: str,
    limit: int = Query(50, ge=1, le=500, description="返回数量上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
    preview_length: int = Query(200, ge=0, le=2000, description="预览长度(0返回完整content)"),
) -> Dict:
    """按文件名分页获取chunk列表，支持返回内容预览长度控制"""
    try:
        total = vector_store.get_chunk_count_by_file(file_name)
        items = vector_store.get_chunks_by_file(file_name, limit=limit, offset=offset, preview_length=preview_length)
        return {
            "file_name": file_name,
            "total": total,
            "limit": limit,
            "offset": offset,
            "preview_length": preview_length,
            "items": items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件chunks失败: {str(e)}")


@router.get("/files/{file_name}/search")
async def search_in_file(
    file_name: str,
    q: str = Query(..., min_length=1, description="关键字(ILIKE模糊匹配)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    preview_length: int = Query(200, ge=0, le=2000),
) -> Dict:
    """在指定文件内按关键字检索chunk，支持分页与内容预览"""
    try:
        items = vector_store.search_chunks_in_file(file_name, q, limit=limit, offset=offset, preview_length=preview_length)
        return {
            "file_name": file_name,
            "query": q,
            "limit": limit,
            "offset": offset,
            "preview_length": preview_length,
            "items": items,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件内搜索失败: {str(e)}")


@router.get("/model/config")
async def get_model_config() -> Dict:
    """获取当前模型配置信息"""
    try:
        current_client = ModelClientFactory.get_current_client()
        model_info = current_client.get_model_info()
        
        return {
            "current_model_type": model_config.current_model_type,
            "model_info": model_info,
            "system_message": model_config.system_message,
            "rag_config": {
                "top_k": model_config.top_k,
                "max_context_chars": model_config.max_context_chars,
                "max_generate_tokens": model_config.max_generate_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型配置失败: {str(e)}")


@router.post("/model/switch")
async def switch_model(model_type: str) -> Dict:
    """切换模型类型（ollama 或 deepseek）"""
    try:
        if model_type not in ["ollama", "deepseek"]:
            raise HTTPException(status_code=400, detail="不支持的模型类型，支持: ollama, deepseek")
        
        # 验证新模型配置
        if model_type == "deepseek" and not model_config.deepseek.api_key:
            raise HTTPException(status_code=400, detail="DeepSeek API key 未配置")
        
        # 测试新模型连接
        test_client = ModelClientFactory.create_client(model_type)
        test_client.embeddings("test")
        
        # 更新配置
        model_config.current_model_type = model_type
        
        return {
            "message": f"成功切换到 {model_type} 模型",
            "current_model_type": model_config.current_model_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换模型失败: {str(e)}")


@router.post("/model/test")
async def test_model_connection() -> Dict:
    """测试当前模型连接状态"""
    try:
        current_client = ModelClientFactory.get_current_client()
        
        # 测试嵌入功能
        test_embedding = current_client.embeddings("test")
        embedding_dim = len(test_embedding)
        
        # 测试聊天功能（非流式）
        test_messages = [{"role": "user", "content": "你好"}]
        test_response = current_client.chat_completion(
            messages=test_messages,
            stream=False,
            max_tokens=10
        )
        
        return {
            "status": "success",
            "model_type": model_config.current_model_type,
            "embedding_test": {
                "status": "success",
                "dimension": embedding_dim
            },
            "chat_test": {
                "status": "success",
                "response": test_response.choices[0].message.content
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "model_type": model_config.current_model_type,
            "error": str(e)
        }
