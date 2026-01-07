import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

# 특수문자 비밀번호 안전하게 인코딩 (필수!)
encoded_password = quote_plus(password)

# URL 생성
SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{db_name}"

# 엔진 생성 (커넥션 풀 설정 포함 - 밸런싱 기초)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,       # 기본 유지 연결 수
    max_overflow=10,    # 트래픽 폭주시 추가 연결 수
    pool_timeout=30,    # 연결 대기 시간
    pool_recycle=1800   # 30분마다 연결 재생성 (끊김 방지)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DB 세션 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()