from typing import Optional, Iterable
import time
from datetime import datetime

from fastapi import APIRouter, Form
from fastapi.responses import StreamingResponse

from core.state import app_state, rag_chat_stream, DEFAULT_MODEL


router = APIRouter(prefix="/chat", tags=["chat"])

#
# @router.post("")
# async def chat(query: str = Form(...), session_id: Optional[str] = Form(None), model: Optional[str] = Form(None)):
#     sid = session_id or "default"
#     if sid not in app_state.histories:
#         app_state.histories[sid] = []
#
#     answer = rag_chat(
#         user_input=query,
#         system_message=app_state.system_message,
#         conversation_history=app_state.histories[sid],
#         vault_embeddings=app_state.vault_embeddings,
#         vault_content=app_state.vault_content,
#         client=app_state.client,
#         model=(model or DEFAULT_MODEL),
#     )
#     return {"answer": answer, "session_id": sid}


@router.post("/stream")
async def chat_stream(query: str = Form(...), session_id: Optional[str] = Form(None), model: Optional[str] = Form(None)):
    enter_ts = time.time()
    print(f"进入 stream 接口 ts={datetime.now().strftime('%Y-%m-%d %H:%M:%S')} sid={session_id or 'default'}")
    sid = session_id or "default"
    if sid not in app_state.histories:
        app_state.histories[sid] = []
    print(f"当前会话历史长度: {len(app_state.histories[sid])}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def sse_event_generator() -> Iterable[str]:
        first_chunk_ts: Optional[float] = None
        print(f"开始调用 rag_chat_stream...{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        for chunk in rag_chat_stream(
            user_input=query,
            system_message=app_state.system_message,
            conversation_history=app_state.histories[sid],
            vault_embeddings=app_state.vault_embeddings,
            vault_content=app_state.vault_content,
            client=app_state.client,
            model=(model or DEFAULT_MODEL),
        ):
            if first_chunk_ts is None:
                first_chunk_ts = time.time()
                print(
                    f"开始返回 ts={datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                    f"latency={(first_chunk_ts - enter_ts)*1000:.0f}ms"
                )
            is_empty = (len(chunk) == 0)
            is_newline = (chunk == "\n" or chunk == "\r\n")
            if is_empty or is_newline:
                print(f"chunk_info  {chunk} , empty={is_empty} newline_only={is_newline} repr={chunk!r}")
            else:
                print(f"chunk_info {chunk} ,  empty=False newline_only=False len={len(chunk)}")
            # do not send completely empty chunks
            if is_empty:
                continue
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"
        print(f"流式响应完成，最终会话历史长度: {len(app_state.histories[sid])}")

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
