import traceback

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers import auth, characters, dictionary, observations, stories, talents


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI 伯乐 - 故事共创",
    description="与孩子共同创作故事，发现语言天赋",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源访问
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ──
# These ensure ALL errors return JSON instead of plain text "Internal Server Error"

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器出了点小问题: {str(exc)[:200]}"},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误，请稍后重试"},
    )


# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(characters.router, prefix="/api/v1")
app.include_router(stories.router, prefix="/api/v1")
app.include_router(observations.router, prefix="/api/v1")
app.include_router(talents.router, prefix="/api/v1")
app.include_router(dictionary.router, prefix="/api/v1")


@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "故事导演已就绪！"}
