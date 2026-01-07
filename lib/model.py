from sqlalchemy import Column, String, Integer, ForeignKey, Text, ARRAY, Numeric
from sqlalchemy.orm import relationship
from lib.database import Base

class Item(Base):
    __tablename__ = "item_table"

    item_id = Column(String, primary_key=True)
    name = Column(String)
    icon_id = Column(String)
    rarity = Column(Integer)

class CharacterConsumption(Base):
    __tablename__ = "character_consumption"

    cons_id = Column(Integer, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id"))
    item_id = Column(String, ForeignKey("item_table.item_id"))
    type = Column(String) # EVOLVE, SKILL_MASTERY, MODULE
    level = Column(Integer)
    count = Column(Integer)

    # 관계 연결
    character = relationship("Character", back_populates="consumptions")
    item = relationship("Item")

# ... (기존 Item, CharacterConsumption 등은 그대로 유지) ...

# 1. 스킨 테이블 추가
class Skin(Base):
    __tablename__ = "skin_table"
    
    skin_id = Column(String, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id"))
    name = Column(String)
    illust_id = Column(String)
    avatar_id = Column(String)
    portrait_id = Column(String)
    drawer_list = Column(ARRAY(Text)) # 배열 타입 지원

    character = relationship("Character", back_populates="skins")

# 2. 정예화 단계 (Phase) 추가 - 중간 다리 역할
class CharacterPhase(Base):
    __tablename__ = "character_phase"
    
    phase_id = Column(Integer, primary_key=True)
    char_id = Column(String, ForeignKey("character.char_id"))
    phase_index = Column(Integer) # 0:기본, 1:1정, 2:2정
    max_level = Column(Integer)

    character = relationship("Character", back_populates="phases")
    attributes = relationship("CharacterAttribute", back_populates="phase")

# 3. 상세 스탯 (Attribute) 추가
class CharacterAttribute(Base):
    __tablename__ = "character_attribute"
    
    attr_id = Column(Integer, primary_key=True)
    phase_id = Column(Integer, ForeignKey("character_phase.phase_id"))
    level = Column(Integer)
    max_hp = Column(Integer)
    atk = Column(Integer)
    def_ = Column("def", Integer) # def는 파이썬 예약어라 변수명 변경 (DB 컬럼은 'def')
    magic_resistance = Column(Numeric)
    cost = Column(Integer)
    block_cnt = Column(Integer)

    phase = relationship("CharacterPhase", back_populates="attributes")

# 4. 캐릭터 테이블 업데이트 (관계 연결)
class Character(Base):
    __tablename__ = "character"
    
    char_id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    rarity = Column(String)
    profession = Column(String)
    description = Column(Text)
    
    # 관계 설정들
    consumptions = relationship("CharacterConsumption", back_populates="character")
    skins = relationship("Skin", back_populates="character")
    phases = relationship("CharacterPhase", back_populates="character")