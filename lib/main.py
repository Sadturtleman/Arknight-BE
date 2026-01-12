# lib/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from lib.core.database import init_redis_pool, close_redis_pool
from lib.api.api import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_redis_pool()
    yield
    # Shutdown
    await close_redis_pool()

app = FastAPI(
    title="Game Info API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs", # Swagger UI
    redoc_url="/redoc"
)

# CORS 설정 (프론트엔드 연동 시 필수)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 보안상 실제 배포 시에는 도메인을 명시하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}