import os
from urllib.parse import quote_plus
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# 특수문자 비밀번호 인코딩
encoded_password = quote_plus(password)

# 1. 비동기용 URL 생성 (postgresql+asyncpg:// 드라이버 명시 필수)
ASYNC_SQLALCHEMY_DATABASE_URL = (
    f"postgresql+asyncpg://{user}:{encoded_password}@{host}:{port}/{db_name}"
)

# 2. 비동기 엔진 생성
# pool_size 및 max_overflow 설정으로 동시 접속 처리 능력 확보
engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_size=20,           # 기본 커넥션 풀 크기
    max_overflow=10,        # 트래픽 급증 시 추가 허용 연결 수
    pool_timeout=30,        # 연결 대기 시간 제한
    pool_recycle=1800,      # 30분마다 연결 재생성 (Stale Connection 방지)
    echo=False              # SQL 로그 출력 여부 (운영 시 False 권장)
)

# 3. 비동기 세션 팩토리 생성
# expire_on_commit=False는 비동기 환경에서 객체 접근 에러를 방지하기 위해 필수입니다.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

Base = declarative_base()

# 4. 비동기 DB 세션 의존성 주입 함수
# FastAPI의 Depends(get_db)를 통해 비동기 세션을 안전하게 공급합니다.
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # commit은 컨트롤러(main.py)에서 명시적으로 하거나 여기서 통합 관리 가능
        finally:
            await session.close()