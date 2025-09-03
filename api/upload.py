import io
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from PyPDF2 import PdfReader

from core.vector_store import vector_store


router = APIRouter(prefix="/upload", tags=["upload"])


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """从PDF字节内容中提取所有页面文本并拼接返回"""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: List[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join([p for p in pages if p]).strip()


def normalize_and_chunk_text(raw_text: str, max_chunk_size: int = 1000) -> List[str]:
    """规范化空白并按句子边界切分文本，保证每块不超过max_chunk_size字符"""
    import re as _re
    # Normalize whitespace
    text = _re.sub(r"\s+", " ", raw_text or "").strip()
    if not text:
        return []
    # Split by sentences (keep delimiters) and make <= max_chunk_size chunks
    sentences = _re.split(r"(?<=[.!?]) +", text)
    chunks: List[str] = []
    current_chunk = ""
    for sentence in sentences:
        candidate = (current_chunk + (" " if current_chunk else "") + sentence).strip()
        if len(candidate) <= max_chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence.strip()
            if len(current_chunk) > max_chunk_size:
                # Hard wrap very long single sentence
                start = 0
                while start < len(current_chunk):
                    end = start + max_chunk_size
                    chunks.append(current_chunk[start:end])
                    start = end
                current_chunk = ""
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


@router.post("/simple")
async def upload_simple(files: List[UploadFile] = File(...)):
    """上传文件并写入向量库：解析文本→正则分块→生成向量→入pgvector"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    total_added = 0
    for f in files:
        data = await f.read()
        name_lower = (f.filename or "").lower()
        content = ""
        file_type = "unknown"
        
        if name_lower.endswith(".pdf"):
            content = extract_text_from_pdf(data)
            file_type = "pdf"
        elif name_lower.endswith(".json"):
            try:
                import json as _json
                obj = _json.loads(data.decode("utf-8"))
                content = _json.dumps(obj, ensure_ascii=False)
                file_type = "json"
            except Exception:
                try:
                    content = data.decode("utf-8")
                    file_type = "text"
                except Exception:
                    content = data.decode("latin-1", errors="ignore")
                    file_type = "text"
        else:
            try:
                content = data.decode("utf-8")
                file_type = "text"
            except Exception:
                content = data.decode("latin-1", errors="ignore")
                file_type = "text"

        # 分块处理
        chunks = normalize_and_chunk_text(content, max_chunk_size=1000)
        
        if chunks:
            # 存储到向量数据库
            try:
                added_count = vector_store.store_chunks(chunks, f.filename or "unknown", file_type)
                total_added += added_count
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"存储文件失败: {str(e)}")

    return {"added": total_added}


@router.post("/docling")
async def upload_docling(files: List[UploadFile] = File(...)):
    """使用 Docling export_to_text 解析多种文档并入库。
    保留原 /upload/simple 作为简易文本路径。
    """
    from core.document_ingest import ingest_bytes

    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    total_added = 0
    for f in files:
        data = await f.read()
        name_lower = (f.filename or "").lower()
        file_type = "unknown"
        if name_lower.endswith(".pdf"):
            file_type = "pdf"
        elif name_lower.endswith((".docx", ".doc")):
            file_type = "docx"
        elif name_lower.endswith((".pptx", ".ppt")):
            file_type = "pptx"
        elif name_lower.endswith((".png", ".jpg", ".jpeg", ".tiff", ".bmp")):
            file_type = "image"
        elif name_lower.endswith((".html", ".htm")):
            file_type = "html"
        elif name_lower.endswith((".md", ".markdown")):
            file_type = "markdown"
        elif name_lower.endswith((".adoc", ".asciidoc")):
            file_type = "asciidoc"
        else:
            file_type = "text"

        try:
            added = ingest_bytes(data, f.filename or "unknown", file_type=file_type)
            total_added += added
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Docling 解析或入库失败: {str(e)}")

    return {"added": total_added}
