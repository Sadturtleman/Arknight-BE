# lib/main.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from lib.core.database import init_redis_pool, close_redis_pool
from lib.api.api import api_router
from starlette.exceptions import HTTPException as StarletteHttpException


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

@app.exception_handler(StarletteHttpException)
async def http_exception_handler(request: Request, exc: StarletteHttpException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": 422,
            "success": False,
            "message": "입력 데이터 형식이 올바르지 않습니다.",
            "data": exc.errors() # 어떤 필드가 잘못되었는지 상세 정보 포함
        }
    )

# 3. 그 외 예상치 못한 모든 서버 에러 (500 에러)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": 500,
            "success": False,
            "message": "서버 내부에서 오류가 발생했습니다.",
            "data": str(exc) if app.debug else None # 디버그 모드일 때만 에러 내용 출력
        }
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