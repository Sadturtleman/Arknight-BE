from typing import List, Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from lib.core.database import Base
from datetime import datetime

# [Skin Group Model]
# 자주 변하지 않는 마스터 데이터이므로 캐싱 대상 1순위입니다.
class SkinGroup(Base):
    __tablename__ = "skin_groups"

    skin_group_id: Mapped[int] = mapped_column(primary_key=True)
    name_ko: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Reverse relation (Optional, but good for navigation)
    # 1:N 관계: 하나의 그룹에 여러 스킨 디테일이 연결됨
    skin_details: Mapped[List["CharacterSkinDetail"]] = relationship(
        back_populates="group"
    )


# [Character Skin (Metadata)]
# 목록 조회 시 가볍게 가져올 수 있는 데이터만 포함합니다.
class CharacterSkin(Base):
    __tablename__ = "character_skins"

    skin_id: Mapped[int] = mapped_column(primary_key=True)
    skin_code: Mapped[str] = mapped_column(String, unique=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.character_id", ondelete="CASCADE")
    )
    
    # Metadata
    name_ko: Mapped[str | None] = mapped_column(String)
    series_name: Mapped[str | None] = mapped_column(String)
    illustrator: Mapped[str | None] = mapped_column(String)
    portrait_id: Mapped[str | None] = mapped_column(String)
    avatar_id: Mapped[str | None] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    character = relationship("Character", back_populates="skins")
    
    # 1:1 Relationship (Detail)
    # 목록 조회 시에는 로딩하지 않도록 lazy="selectin" 또는 필요시 명시적 join을 사용합니다.
    # uselist=False로 1:1 관계임을 명시
    detail: Mapped["CharacterSkinDetail"] = relationship(
        back_populates="skin", 
        uselist=False, 
        lazy="selectin",
        cascade="all, delete-orphan"
    )


# [Character Skin Detail (Content)]
# 텍스트 데이터가 많으므로 필요할 때만 로딩(Lazy Loading)되는 것이 유리합니다.
class CharacterSkinDetail(Base):
    __tablename__ = "character_skin_details"

    skin_id: Mapped[int] = mapped_column(
        ForeignKey("character_skins.skin_id", ondelete="CASCADE"), 
        primary_key=True
    )
    skin_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("skin_groups.skin_group_id")
    )

    # Heavy Text Data
    content: Mapped[str | None] = mapped_column(Text)
    dialog: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    usage_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    skin = relationship("CharacterSkin", back_populates="detail")
    group = relationship("SkinGroup", back_populates="skin_details", lazy="selectin")