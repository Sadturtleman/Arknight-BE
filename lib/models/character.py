from typing import List
from sqlalchemy import String, Integer, SmallInteger, Text, ForeignKey, DateTime, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from lib.core.database import Base
from datetime import datetime
from lib.models.module import CharacterModule

# Association Table for Many-to-Many (Character <-> Tag)
character_tag = Table(
    "character_tag",
    Base.metadata,
    Column("character_id", Integer, ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.tag_id", ondelete="CASCADE"), primary_key=True),
)

class Character(Base):
    __tablename__ = "characters"

    character_id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True)
    name_ko: Mapped[str] = mapped_column(String(64))
    class_description: Mapped[str | None] = mapped_column(String(255))
    rarity: Mapped[int] = mapped_column(SmallInteger)
    
    profession_id: Mapped[int | None] = mapped_column(ForeignKey("profession.profession_id"))
    sub_profession_id: Mapped[int | None] = mapped_column(ForeignKey("sub_profession.sub_profession_id"))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # --- Relationships ---
    # 1. Reference Data (Eager Loading recommended for single items)
    profession = relationship("Profession", lazy="selectin")
    sub_profession = relationship("SubProfession", lazy="selectin")

    # 2. Child Tables (One-to-Many)
    # Async 환경에서 list 로딩 시 lazy="selectin"이 가장 효율적입니다.
    stats: Mapped[List["CharacterStat"]] = relationship(back_populates="character", lazy="selectin")
    talents: Mapped[List["CharacterTalent"]] = relationship(back_populates="character", lazy="selectin")
    promotion_costs: Mapped[List["CharacterPromotionCost"]] = relationship(back_populates="character", lazy="selectin")

    # 3. One-to-One
    detail: Mapped["CharacterDetail"] = relationship(back_populates="character", uselist=False, lazy="selectin")
    skill_slots: Mapped["CharacterSkillSlot"] = relationship(back_populates="character", uselist=False, lazy="selectin")
    favor: Mapped["CharacterFavorTemplate"] = relationship(back_populates="character", uselist=False, lazy="selectin")

    # 4. Many-to-Many
    tags = relationship("Tag", secondary=character_tag, lazy="selectin")

    modules: Mapped[List["CharacterModule"]] = relationship(
        "lib.models.module.CharacterModule", 
        back_populates="character", 
        lazy="selectin"
    )

    skill_costs: Mapped[List["CharacterSkillCost"]] = relationship(
        "CharacterSkillCost",
        back_populates="character",
        lazy="selectin",
        cascade="all, delete-orphan"
    )

    @property
    def item_usage(self) -> str | None:
        """detail 테이블의 item_usage를 내 속성처럼 노출"""
        return self.detail.item_usage if self.detail else None

    @property
    def item_desc(self) -> str | None:
        """detail 테이블의 item_desc를 내 속성처럼 노출"""
        return self.detail.item_desc if self.detail else None


class CharacterDetail(Base):
    __tablename__ = "characters_detail"
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True)
    item_usage: Mapped[str | None] = mapped_column(Text)
    item_desc: Mapped[str | None] = mapped_column(Text)
    
    character = relationship("Character", back_populates="detail")

class CharacterStat(Base):
    __tablename__ = "character_stats"
    character_stat_id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    phase: Mapped[int] = mapped_column(SmallInteger)
    max_level: Mapped[int] = mapped_column(SmallInteger)
    range_id: Mapped[str | None] = mapped_column(ForeignKey("ranges.range_id"))
    
    # Stats
    base_hp: Mapped[int] = mapped_column(Integer)
    base_atk: Mapped[int] = mapped_column(Integer)
    base_def: Mapped[int] = mapped_column(Integer)
    max_hp: Mapped[int] = mapped_column(Integer)
    max_atk: Mapped[int] = mapped_column(Integer)
    max_def: Mapped[int] = mapped_column(Integer)
    magic_resistance: Mapped[int] = mapped_column(SmallInteger)
    cost: Mapped[int] = mapped_column(SmallInteger)
    block_cnt: Mapped[int] = mapped_column(SmallInteger)
    attack_speed: Mapped[int] = mapped_column(SmallInteger)

    character = relationship("Character", back_populates="stats")
    range_data = relationship("Range", lazy="joined")

class CharacterTalent(Base):
    __tablename__ = "character_talents"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    talent_index: Mapped[int] = mapped_column(SmallInteger)
    candidate_index: Mapped[int] = mapped_column(SmallInteger)
    unlock_phase: Mapped[int] = mapped_column(SmallInteger)
    unlock_level: Mapped[int] = mapped_column(SmallInteger)
    required_potential: Mapped[int] = mapped_column(SmallInteger)
    range_id: Mapped[str | None] = mapped_column(ForeignKey("ranges.range_id"))
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    blackboard: Mapped[dict] = mapped_column(JSONB)

    character = relationship("Character", back_populates="talents")

class CharacterSkillSlot(Base):
    """캐릭터가 보유한 스킬 목록 (phase 0, 1, 2)"""
    __tablename__ = "character_skill"
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True)
    phase_0_code: Mapped[str | None] = mapped_column(String(32))
    phase_1_code: Mapped[str | None] = mapped_column(String(32))
    phase_2_code: Mapped[str | None] = mapped_column(String(32))

    character = relationship("Character", back_populates="skill_slots")

class CharacterFavorTemplate(Base):
    __tablename__ = "character_favor_templates"
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), primary_key=True)
    max_favor_level: Mapped[int] = mapped_column(SmallInteger, default=50)
    bonus_hp: Mapped[int] = mapped_column(Integer, default=0)
    bonus_atk: Mapped[int] = mapped_column(Integer, default=0)
    bonus_def: Mapped[int] = mapped_column(Integer, default=0)
    extra_bonuses: Mapped[dict] = mapped_column(JSONB)

    character = relationship("Character", back_populates="favor")

class CharacterPromotionCost(Base):
    __tablename__ = "character_promotion_costs"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    target_phase: Mapped[int] = mapped_column(SmallInteger)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"))
    count: Mapped[int] = mapped_column(Integer)

    character = relationship("Character", back_populates="promotion_costs")
    item = relationship("lib.models.item.Item", lazy="selectin") # 순환 참조 방지를 위해 문자열 참조

class CharacterSkillCost(Base):
    __tablename__ = "character_skill_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"))
    level: Mapped[int] = mapped_column(SmallInteger) # Target Level (2~7)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"))
    count: Mapped[int] = mapped_column(Integer)

    character = relationship("Character", back_populates="skill_costs")
    item = relationship("lib.models.item.Item", lazy="selectin")