import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, SmallInteger, ForeignKey, Numeric, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from typing import List, Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# [설정] .env의 DATABASE_URL 사용 (asyncpg 필수)
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Construct the SQLAlchemy connection string
DATABASE_URL = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DBNAME}?ssl=require"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    connect_args={
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
        "ssl": "require" # 필요시 사용
    }
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

# ==========================================
# 1. Operators & Skills
# ==========================================

class Operator(Base):
    __tablename__ = "operators"

    operator_id: Mapped[str] = mapped_column(String, primary_key=True)
    name_ko: Mapped[str] = mapped_column(String)
    name_en: Mapped[Optional[str]] = mapped_column(String)
    rarity: Mapped[int] = mapped_column(SmallInteger)
    profession: Mapped[str] = mapped_column(String)
    sub_profession: Mapped[Optional[str]] = mapped_column(String)
    position: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    range_id: Mapped[Optional[str]] = mapped_column(ForeignKey("ranges.range_id"))
    potential_data: Mapped[Optional[str]] = mapped_column(String) # Character Varying
    
    # JSONB Fields
    phases_data: Mapped[Optional[List[Dict]]] = mapped_column(JSONB)
    talents_data: Mapped[Optional[List[Dict]]] = mapped_column(JSONB)
    trust_data: Mapped[Optional[Dict]] = mapped_column(JSONB)

    # Relationships
    skills: Mapped[List["OperatorSkill"]] = relationship("OperatorSkill", lazy="selectin")
    stats: Mapped[List["OperatorStat"]] = relationship("OperatorStat", lazy="selectin")
    modules: Mapped[List["Module"]] = relationship("Module", lazy="selectin")
    consumptions: Mapped[List["OperatorConsumption"]] = relationship("OperatorConsumption", lazy="selectin")
    skins: Mapped[List["Skin"]] = relationship("Skin", lazy="selectin")
    range_data: Mapped[Optional["Range"]] = relationship("Range", lazy="selectin")

class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[str] = mapped_column(String, primary_key=True)
    name_ko: Mapped[str] = mapped_column(String)
    icon_id: Mapped[Optional[str]] = mapped_column(String)
    sp_type: Mapped[str] = mapped_column(String)
    duration_type: Mapped[str] = mapped_column(String)
    levels_data: Mapped[List[Dict]] = mapped_column(JSONB)

class OperatorSkill(Base):
    __tablename__ = "operator_skills"

    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"), primary_key=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.skill_id"), primary_key=True)
    skill_index: Mapped[int] = mapped_column(SmallInteger)
    unlock_phase: Mapped[int] = mapped_column(SmallInteger)
    
    # [수정] level 컬럼 제거됨 (Schema 반영)

    skill_info: Mapped["Skill"] = relationship("Skill", lazy="selectin")

class OperatorStat(Base):
    __tablename__ = "operator_stats"

    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"), primary_key=True)
    phase: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    max_level: Mapped[int] = mapped_column(SmallInteger)
    max_hp: Mapped[int] = mapped_column(Integer)
    max_atk: Mapped[int] = mapped_column(Integer)
    max_def: Mapped[int] = mapped_column(Integer)
    max_res: Mapped[float] = mapped_column(Numeric)
    cost: Mapped[int] = mapped_column(SmallInteger)
    block_cnt: Mapped[int] = mapped_column(SmallInteger)
    attack_speed: Mapped[int] = mapped_column(SmallInteger)
    respawn_time: Mapped[int] = mapped_column(SmallInteger)
    range_id: Mapped[Optional[str]] = mapped_column(ForeignKey("ranges.range_id"))

class OperatorConsumption(Base):
    __tablename__ = "operator_consumptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"))
    cost_type: Mapped[str] = mapped_column(String) # ELITE, MASTERY
    level: Mapped[int] = mapped_column(SmallInteger)
    ingredients: Mapped[List[Dict]] = mapped_column(JSONB)

# ==========================================
# 2. Modules & Skins
# ==========================================

class Module(Base):
    __tablename__ = "modules"

    module_id: Mapped[str] = mapped_column(String, primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"))
    display_text: Mapped[Dict] = mapped_column(JSONB)
    unlock_cond: Mapped[Optional[List[Dict]]] = mapped_column(JSONB)
    levels_data: Mapped[Dict] = mapped_column(JSONB)

class Skin(Base):
    __tablename__ = "skins"
    
    skin_id: Mapped[str] = mapped_column(String, primary_key=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"))
    name_ko: Mapped[Optional[str]] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    display_data: Mapped[Dict] = mapped_column(JSONB)

class Range(Base):
    __tablename__ = "ranges"
    range_id: Mapped[str] = mapped_column(String, primary_key=True)
    grids: Mapped[List[Dict]] = mapped_column(JSONB)

# Dependency Injection
async def get_db():
    async with async_session_factory() as session:
        yield session