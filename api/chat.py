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
            
            # 检查chunk状态
            is_empty = (len(chunk) == 0)
            is_pure_newline = (chunk == "\n" or chunk == "\r\n")
            contains_newline = "\n" in chunk or "\r" in chunk
            
            # 打印调试信息
            # if is_empty:
            #     print(f"chunk_info: 空chunk, empty=True, repr={chunk!r}")
            # elif is_pure_newline:
            #     print(f"chunk_info: 纯换行, empty=False, newline_only=True, repr={chunk!r}")
            # elif contains_newline:
            #     print(f"chunk_info: 包含换行符, empty=False, newline_only=False, len={len(chunk)}, repr={chunk!r}")
            #     # 详细分析包含换行符的chunk
            #     newline_positions = []
            #     for i, char in enumerate(chunk):
            #         if char in ['\n', '\r']:
            #             newline_positions.append(f"pos{i}:{repr(char)}")
            #     print(f"  -> 换行符位置: {newline_positions}")
                
            # else:
            #     print(f"chunk_info: 正常内容, empty=False, newline_only=False, len={len(chunk)}, content={chunk}")
            
            # 跳过完全空的chunk，但保留包含换行符的chunk
            # if is_empty:
            #     continue
            
            # 处理换行符：将换行符替换为特殊字符
            processed_chunk = chunk
            if contains_newline:
                # 将换行符替换为特殊字符 [NEWLINE]
                processed_chunk = chunk.replace('\n', '[NEWLINE]').replace('\r', '[NEWLINE]')
                # print(f"处理换行符后的chunk: {repr(processed_chunk)}")
            
            # 发送chunk给前端
            sse_data = f"data: {processed_chunk}\n\n"
            # print(f"发送SSE数据: {repr(sse_data)}")
            yield sse_data
            
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
