import io
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from PyPDF2 import PdfReader

from core.state import app_state, append_to_vault, embed_texts, VAULT_PATH


router = APIRouter(prefix="/upload", tags=["upload"])


def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages: List[str] = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return "\n".join([p for p in pages if p]).strip()


def normalize_and_chunk_text(raw_text: str, max_chunk_size: int = 1000) -> List[str]:
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


@router.post("")
async def upload(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    new_lines: List[str] = []
    for f in files:
        data = await f.read()
        name_lower = (f.filename or "").lower()
        content = ""
        if name_lower.endswith(".pdf"):
            content = extract_text_from_pdf(data)
        elif name_lower.endswith(".json"):
            try:
                import json as _json
                obj = _json.loads(data.decode("utf-8"))
                content = _json.dumps(obj, ensure_ascii=False)
            except Exception:
                try:
                    content = data.decode("utf-8")
                except Exception:
                    content = data.decode("latin-1", errors="ignore")
        else:
            try:
                content = data.decode("utf-8")
            except Exception:
                content = data.decode("latin-1", errors="ignore")

        # Apply original logic: normalize and split into sentence-bounded chunks
        chunks = normalize_and_chunk_text(content, max_chunk_size=1000)
        new_lines.extend(chunks)

    if not new_lines:
        return JSONResponse({"added": 0})

    append_to_vault(VAULT_PATH, new_lines)
    app_state.vault_content.extend([l + "\n" for l in new_lines])

    try:
        new_embeds = embed_texts(new_lines)
        if app_state.vault_embeddings.nelement() == 0:
            app_state.vault_embeddings = new_embeds
        else:
            app_state.vault_embeddings = __import__('torch').vstack([app_state.vault_embeddings, new_embeds])
    except Exception:
        # If embedding service is unavailable, keep content written; embeddings remain empty
        pass

    return {"added": len(new_lines)}
