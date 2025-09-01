from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.state import initialize_state_on_startup
from api.upload import router as upload_router
from api.chat import router as chat_router
from api.manage import router as manage_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_state_on_startup()
    yield
    print("正在关闭rag服务...")


app = FastAPI(title="Easy Local RAG API", lifespan=lifespan)

# Enable CORS for browser access (adjust allowed origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(manage_router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


