import enum
from sqlalchemy import (
    Column, String, Integer, SmallInteger, Numeric, 
    Boolean, ForeignKey, Text, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

Base = declarative_base()

# 1. ENUM 정의 (DB의 USER-DEFINED 타입과 매핑)
class ProfessionEnum(str, enum.Enum):
    PIONEER = "PIONEER"
    WARRIOR = "WARRIOR"
    TANK = "TANK"
    SNIPER = "SNIPER"
    CASTER = "CASTER"
    MEDIC = "MEDIC"
    SUPPORT = "SUPPORT"
    SPECIAL = "SPECIAL"
    TRAP = "TRAP"
    TOKEN = "TOKEN"

class ConsumptionTypeEnum(str, enum.Enum):
    EVOLVE = "EVOLVE"
    SKILL_MASTERY = "SKILL_MASTERY"
    MODULE = "MODULE"
    SKILL_LEVELUP = "SKILL_LEVELUP"
    SKILL_COMMON = "SKILL_COMMON"

# 2. 독립 테이블 (Range, Skill, Item)
class RangeTable(Base):
    __tablename__ = "range_table"
    range_id = Column(String, primary_key=True)
    direction = Column(Integer, default=1)

class Skill(Base):
    __tablename__ = "skill_table"
    skill_id = Column(String, primary_key=True)
    icon_id = Column(String)
    hidden = Column(Boolean, default=False)

class Item(Base):
    __tablename__ = "item_table"
    item_id = Column(String, primary_key=True)
    name = Column(String, index=True)
    rarity = Column(Integer)
    icon_id = Column(String)
    # ... 나머지 필드 필요 시 추가

# 3. 메인 캐릭터 테이블
class Character(Base):
    __tablename__ = "character"
    
    char_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    rarity = Column(SmallInteger) # 최적화: 정수형 사용
    profession = Column(SQLEnum(ProfessionEnum)) # 최적화: Enum 사용
    
    appellation = Column(String)
    description = Column(Text)
    sub_profession_id = Column(String)
    position = Column(String)
    is_sp_char = Column(Boolean, default=False)

    # 관계 설정 (back_populates를 통한 양방향 참조)
    skins = relationship("Skin", back_populates="character", cascade="all, delete-orphan")
    phases = relationship("CharacterPhase", back_populates="character", cascade="all, delete-orphan")
    consumptions = relationship("CharacterConsumption", back_populates="character")
    talents = relationship("CharacterTalent", back_populates="character")
    modules = relationship("Module", back_populates="character")

# 4. 캐릭터 상세 정보 (Phase & Attribute)
class CharacterPhase(Base):
    __tablename__ = "character_phase"
    phase_id = Column(Integer, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id", ondelete="CASCADE"), index=True)
    phase_index = Column(Integer, nullable=False)
    max_level = Column(Integer, nullable=False)
    
    character = relationship("Character", back_populates="phases")
    attributes = relationship("CharacterAttribute", back_populates="phase", cascade="all, delete-orphan")

class CharacterAttribute(Base):
    __tablename__ = "character_attribute"
    attr_id = Column(Integer, primary_key=True)
    phase_id = Column(Integer, ForeignKey("character_phase.phase_id", ondelete="CASCADE"), index=True)
    level = Column(Integer, nullable=False)
    
    max_hp = Column(Integer)
    atk = Column(Integer)
    def_ = Column("def", Integer)
    
    # 최적화: Numeric 정밀도 지정
    magic_resistance = Column(Numeric(5, 2))
    cost = Column(Integer)
    block_cnt = Column(Integer)
    move_speed = Column(Numeric(4, 2))
    attack_speed = Column(Numeric(5, 2))
    
    phase = relationship("CharacterPhase", back_populates="attributes")

# 5. 소비 및 스킨 정보
class CharacterConsumption(Base):
    __tablename__ = "character_consumption"
    cons_id = Column(Integer, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id", ondelete="CASCADE"), index=True)
    item_id = Column(String, ForeignKey("item_table.item_id"), index=True)
    
    type = Column(SQLEnum(ConsumptionTypeEnum), nullable=False) # Enum 최적화
    level = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False)

    character = relationship("Character", back_populates="consumptions")
    item = relationship("Item")

class Skin(Base):
    __tablename__ = "skin_table"
    skin_id = Column(String, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id", ondelete="CASCADE"), index=True)
    name = Column(String)
    illust_id = Column(String)
    avatar_id = Column(String)
    portrait_id = Column(String)
    drawer_list = Column(ARRAY(Text)) # PostgreSQL ARRAY 타입 대응

    character = relationship("Character", back_populates="skins")

class Module(Base):
    __tablename__ = "module_table"
    module_id = Column(String, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id", ondelete="CASCADE"), index=True)
    name = Column(String)
    
    character = relationship("Character", back_populates="modules")

class CharacterTalent(Base):
    __tablename__ = "character_talent"
    talent_record_id = Column(Integer, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id", ondelete="CASCADE"), index=True)
    name = Column(String)
    description = Column(Text)
    
    character = relationship("Character", back_populates="talents")