from sqlalchemy import String, Integer, SmallInteger, Text, ForeignKey, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from lib.core.database import Base
from datetime import datetime
from typing import List

class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[int] = mapped_column(primary_key=True)
    skill_code: Mapped[str] = mapped_column(String(64), unique=True)
    name_ko: Mapped[str] = mapped_column(String(64))
    icon_id: Mapped[str | None] = mapped_column(String(128))
    skill_type: Mapped[int | None] = mapped_column(SmallInteger)
    sp_type: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    mastery_costs: Mapped[List["SkillMasteryCost"]] = relationship(
        back_populates="skill",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    # 1:N Relationship
    levels: Mapped[list["SkillLevel"]] = relationship(back_populates="skill", lazy="selectin")

class SkillLevel(Base):
    __tablename__ = "skill_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"))
    level: Mapped[int] = mapped_column(SmallInteger)
    sp_cost: Mapped[int] = mapped_column(SmallInteger)
    initial_sp: Mapped[int] = mapped_column(SmallInteger, default=0)
    duration: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    range_id: Mapped[str | None] = mapped_column(ForeignKey("ranges.range_id"))
    description: Mapped[str | None] = mapped_column(Text)
    blackboard: Mapped[dict] = mapped_column(JSONB)

    # Relationships
    skill: Mapped["Skill"] = relationship(back_populates="levels")
    range_data = relationship("Range", lazy="joined") # 범위 정보는 보통 같이 쓰므로 joined 로딩

class SkillMasteryCost(Base):
    __tablename__ = "skill_mastery_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"))
    mastery_level: Mapped[int] = mapped_column(SmallInteger) # 1, 2, 3
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"))
    count: Mapped[int] = mapped_column(Integer)

    # Relationships
    skill = relationship("Skill", back_populates="mastery_costs")
    item = relationship("lib.models.item.Item", lazy="selectin")