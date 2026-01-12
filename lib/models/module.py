from typing import List
from sqlalchemy import String, Integer, SmallInteger, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from lib.core.database import Base

class CharacterModule(Base):
    __tablename__ = "character_modules"

    module_id: Mapped[int] = mapped_column(primary_key=True)
    module_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.character_id", ondelete="CASCADE"), nullable=False)
    name_ko: Mapped[str] = mapped_column(String, nullable=False)
    icon_id: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)

    # --- Relationships ---
    
    # 1. Parent (Character)
    # 순환 참조 방지를 위해 문자열("lib.models.character.Character")로 참조합니다.
    character = relationship("lib.models.character.Character", back_populates="modules")

    # 2. Children (Costs)
    # 모듈 조회 시 강화 재료도 보여줘야 하므로 selectin 로딩을 사용합니다.
    costs: Mapped[List["CharacterModuleCost"]] = relationship(
        back_populates="module", 
        lazy="selectin", 
        cascade="all, delete-orphan"
    )

class CharacterModuleCost(Base):
    __tablename__ = "character_module_costs"

    id: Mapped[int] = mapped_column(primary_key=True)
    module_id: Mapped[int] = mapped_column(ForeignKey("character_modules.module_id", ondelete="CASCADE"), nullable=False)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False) # 1~3 Level
    item_id: Mapped[int] = mapped_column(ForeignKey("items.item_id"), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- Relationships ---
    
    # 1. Parent (Module)
    module = relationship("CharacterModule", back_populates="costs")

    # 2. Reference (Item)
    # 아이템 정보(이름, 아이콘)를 같이 가져오기 위해 Eager Loading 적용
    item = relationship("lib.models.item.Item", lazy="selectin")