from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from lib.core.database import Base
from datetime import datetime
from lib.models import stage

class Profession(Base):
    __tablename__ = "profession"
    
    profession_id: Mapped[int] = mapped_column(primary_key=True)
    name_ko: Mapped[str] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SubProfession(Base):
    __tablename__ = "sub_profession"

    sub_profession_id: Mapped[int] = mapped_column(primary_key=True)
    name_ko: Mapped[str] = mapped_column(String(16), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Tag(Base):
    __tablename__ = "tag"

    tag_id: Mapped[int] = mapped_column(primary_key=True)
    tag_name: Mapped[str] = mapped_column(String(16), unique=True)

class Range(Base):
    __tablename__ = "ranges"

    range_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    grids: Mapped[dict] = mapped_column(JSONB) # Pydantic dict와 호환
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[int] = mapped_column(primary_key=True)
    zone_code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ko: Mapped[str] = mapped_column(String(64))
    zone_type: Mapped[str | None] = mapped_column(String(20))
    zone_index: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 1:N Relationship
    stages: Mapped[list["stage.Stage"]] = relationship(
        "lib.models.stage.Stage", 
        back_populates="zone",
        lazy="selectin",
        cascade="all, delete-orphan" 
    )