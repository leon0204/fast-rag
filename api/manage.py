from typing import List, Dict
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.vector_store import vector_store
from config.database import get_chunk_count, clear_all_chunks

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
    """删除指定文件的所有文档块，返回删除数量"""
    try:
        deleted_count = vector_store.delete_file_chunks(file_name)
        return {
            "message": f"成功删除文件 {file_name}",
            "deleted_chunks": deleted_count
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
