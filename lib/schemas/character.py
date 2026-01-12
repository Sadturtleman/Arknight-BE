from typing import List, Optional, Dict, Any
from lib.schemas.common import BaseSchema, ProfessionResponse, SubProfessionResponse, TagResponse, RangeResponse
from lib.schemas.item import ItemResponse
from lib.schemas.skill import SkillResponse
from lib.schemas.module import ModuleResponse
from pydantic import ConfigDict, Field

# 1. 캐릭터 기본 스탯 (내부용)
class CharacterStatResponse(BaseSchema):
    phase: int
    max_level: int
    max_hp: int
    max_atk: int
    max_def: int
    cost: int
    block_cnt: int
    range_data: Optional[RangeResponse] = None

# 2. 재능 (Talent)
class CharacterTalentResponse(BaseSchema):
    name: str
    description: Optional[str] = None
    unlock_phase: int
    required_potential: int

# 3. [Lightweight] 리스트 조회용 (검색 결과 등)
class CharacterListResponse(BaseSchema):
    character_id: int
    code: str
    name_ko: str
    rarity: int
    profession: Optional[ProfessionResponse] = None
    sub_profession: Optional[SubProfessionResponse] = None
    icon_url: str = "" # 나중에 CDN URL 조합 로직 추가 가능

# 4. [Heavyweight] 상세 조회용 (모든 정보 포함)
class CharacterDetailResponse(CharacterListResponse):
    class_description: Optional[str] = None
    tags: List[TagResponse] = []
    
    # 관계 데이터들
    stats: List[CharacterStatResponse] = []
    talents: List[CharacterTalentResponse] = []
    skills: List[SkillResponse] = []  # 스킬 정보 풀세트
    modules: List[ModuleResponse] = [] # 모듈 정보 풀세트
    skill_costs: List[CharacterSkillCostResponse] = []
    # 상세 텍스트
    item_usage: Optional[str] = Field(
        None, 
        validation_alias="item_usage",   # ORM 객체에서 읽을 때는 'item_usage'로 읽고
        serialization_alias="itemUsage"  # JSON으로 나갈 때는 'itemUsage'로 내보내라
    )
    
    item_desc: Optional[str] = Field(
        None, 
        validation_alias="item_desc",    # ORM 객체에서 읽을 때는 'item_desc'로 읽고
        serialization_alias="itemDesc"   # JSON으로 나갈 때는 'itemDesc'로 내보내라
    )
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class CharacterSkillCostResponse(BaseSchema):
    level: int
    count: int
    item: ItemResponse