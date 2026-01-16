# lib/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from redis import asyncio as aioredis
from dotenv import load_dotenv
import os

load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?ssl=require"

# 1. PostgreSQL Async Engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass = NullPool,
    pool_pre_ping=True,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0
    },
)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

# 2. Redis Connection Pool
redis_pool = None

def init_redis_pool():
    """앱 시작 시 호출되어 Redis Pool을 생성"""
    global redis_pool
    print(f"🚀 Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    redis_pool = aioredis.ConnectionPool.from_url(
        REDIS_URL, 
        decode_responses=True, 
        max_connections=100
    )

async def close_redis_pool():
    """앱 종료 시 호출되어 연결 해제"""
    global redis_pool
    if redis_pool:
        await redis_pool.disconnect()
        print("🛑 Redis connection closed.")

# Dependency Injection for DB Session
async def get_db():
    async with SessionLocal() as session:
        yield session

# Dependency Injection for Redis Client
async def get_redis():
    client = aioredis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.close()