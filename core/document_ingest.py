from __future__ import annotations

import re
from typing import List, Dict, Tuple

from config.docling import document_converter
from core.vector_store import vector_store


def export_to_text(content: bytes | str, filename: str) -> str:
    """Convert file content to plain text using Docling export_to_text().
    Supports bytes (uploaded) or file path string.
    """
    if isinstance(content, bytes):
        # Save to a temporary pathless buffer via docling's convert API using in-memory bytes
        # Docling supports path/URL; for bytes, we pass a BytesIO-like path by writing to tmp.
        import tempfile, os
        suffix = ""
        if "." in filename:
            suffix = "." + filename.split(".")[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            result = document_converter.convert(tmp_path)
            return result.document.export_to_text()
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    else:
        # content is path
        result = document_converter.convert(content)
        return result.document.export_to_text()


def chunk_text_from_export(export_text: str, max_tokens: int = 800, min_tokens: int = 120) -> List[str]:
    """Chunk the docling export_to_text output using its structure signals.
    - Headings (#...) start new blocks
    - Double newlines separate paragraphs
    - List items (-, *, +, 1.) are grouped
    - Very short blocks are merged up to min_tokens, long ones split ~max_tokens by sentences
    """
    # Normalize line endings
    text = export_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    # Split into logical lines
    lines = [ln.rstrip() for ln in text.split("\n")]

    blocks: List[str] = []
    buf: List[str] = []

    def flush_buf():
        if not buf:
            return
        # Join consecutive lines, preserving paragraph breaks
        joined = "\n".join(buf).strip()
        if joined:
            blocks.append(joined)
        buf.clear()

    heading_re = re.compile(r"^\s{0,3}#{1,6} \S")
    list_re = re.compile(r"^\s{0,3}(?:[-*+] |\d+\. )\S")
    fence_re = re.compile(r"^\s*```")

    in_code = False
    for ln in lines:
        if fence_re.match(ln):
            in_code = not in_code
            buf.append(ln)
            continue
        if in_code:
            buf.append(ln)
            continue

        if not ln.strip():
            # empty line indicates paragraph break
            flush_buf()
            continue

        if heading_re.match(ln):
            flush_buf()
            buf.append(ln)
            flush_buf()
            continue

        if list_re.match(ln):
            # keep consecutive list lines together; handled by buffer until empty line
            buf.append(ln)
            continue

        buf.append(ln)

    flush_buf()

    # Clean each block: strip markdown markers but keep content
    def clean_block(block: str) -> str:
        b = block
        # Remove fences
        b = re.sub(r"```[\s\S]*?```", "", b)
        # Remove heading markers at line start
        b = re.sub(r"^\s{0,3}#{1,6}\s+", "", b, flags=re.MULTILINE)
        # Remove list bullets
        b = re.sub(r"^\s{0,3}(?:[-*+] |\d+\. )", "", b, flags=re.MULTILINE)
        # Collapse whitespace
        b = re.sub(r"\s+", " ", b).strip()
        return b

    cleaned = [clean_block(b) for b in blocks]
    cleaned = [c for c in cleaned if c]

    # Merge small blocks and split long ones
    def estimate_tokens(s: str) -> int:
        # heuristic: ~4 chars per token (English) / ~1.5-2 (CJK). Use conservative 3.
        return max(1, int(len(s) / 3))

    final_chunks: List[str] = []
    carry = ""
    for c in cleaned:
        if carry:
            candidate = (carry + "\n\n" + c)
        else:
            candidate = c
        if estimate_tokens(candidate) < min_tokens:
            carry = candidate
            continue
        # candidate big enough; now split by sentences to fit max_tokens
        unit = candidate
        carry = ""
        # sentence split with Chinese and English punctuation
        sentences = re.split(r"(?<=[。！？.!?])\s+", unit)
        cur = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            cand = (cur + (" " if cur else "") + s)
            if estimate_tokens(cand) <= max_tokens:
                cur = cand
            else:
                if cur:
                    final_chunks.append(cur)
                if estimate_tokens(s) <= max_tokens:
                    cur = s
                else:
                    # hard wrap extremely long sentence
                    step = max_tokens * 3  # chars approximation
                    for i in range(0, len(s), step):
                        final_chunks.append(s[i:i+step])
                    cur = ""
        if cur:
            final_chunks.append(cur)

    if carry:
        final_chunks.append(carry)

    return final_chunks


def ingest_bytes(file_bytes: bytes, filename: str, file_type: str = "unknown") -> int:
    text = export_to_text(file_bytes, filename)
    chunks = chunk_text_from_export(text)
    if not chunks:
        return 0
    return vector_store.store_chunks(chunks, filename, file_type=file_type)


def ingest_file(path: str, file_type: str = "unknown") -> Tuple[str, int]:
    text = export_to_text(path, path)
    chunks = chunk_text_from_export(text)
    if not chunks:
        return path, 0
    added = vector_store.store_chunks(chunks, path, file_type=file_type)
    return path, added


