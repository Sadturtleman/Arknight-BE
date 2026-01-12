from typing import List, Optional
from pydantic import Field, computed_field
from lib.schemas.common import (
    BaseSchema, ProfessionResponse, SubProfessionResponse, 
    TagResponse, RangeResponse
)
from lib.schemas.skill import SkillResponse
from lib.schemas.module import ModuleResponse
from lib.schemas.item import ItemResponse

# 1. 스탯 정보
class CharacterStatResponse(BaseSchema):
    phase: int
    max_level: int = Field(..., serialization_alias="maxLevel")
    max_hp: int = Field(..., serialization_alias="maxHp")
    max_atk: int = Field(..., serialization_alias="maxAtk")
    max_def: int = Field(..., serialization_alias="maxDef")
    cost: int
    block_cnt: int = Field(..., serialization_alias="blockCnt")
    range_data: Optional[RangeResponse] = Field(None, serialization_alias="rangeData")

# 2. 리스트 조회용 (Lightweight)
class CharacterListResponse(BaseSchema):
    character_id: int = Field(..., serialization_alias="characterId")
    code: str
    name_ko: str = Field(..., serialization_alias="nameKo")
    rarity: int
    profession: Optional[ProfessionResponse] = None
    sub_profession: Optional[SubProfessionResponse] = Field(None, serialization_alias="subProfession")

    @computed_field
    @property
    def icon_url(self) -> str:
        # 이전 제안된 CDN URL 빌더 로직 활용
        return f"https://cdn.jsdelivr.net/gh/fexli/ArknightsResource@main/avatar/{self.code}.png"

# 3. 상세 프로필 (API 1: Profile)
class CharacterProfileResponse(CharacterListResponse):
    class_description: Optional[str] = Field(None, serialization_alias="classDescription")
    tags: List[TagResponse] = []
    stats: List[CharacterStatResponse] = []
    
    @computed_field
    @property
    def portrait_url(self) -> str:
        return f"https://cdn.jsdelivr.net/gh/fexli/ArknightsResource@main/portrait/{self.code}_1.png"

# 4. 스킬 정보 (API 2: Skills)
class CharacterSkillDetailResponse(BaseSchema):
    skills: List[SkillResponse] = []

# 5. 육성 비용 정보 (API 3: Growth)
class CharacterSkillCostResponse(BaseSchema):
    level: int
    count: int
    item: ItemResponse

class CharacterGrowthResponse(BaseSchema):
    skill_costs: List[CharacterSkillCostResponse] = Field([], serialization_alias="skillCosts")
    # 추가 예정인 promotion_costs 등도 여기에 배치

# 6. 모듈 및 스토리 (API 4: Modules)
class CharacterModuleResponse(BaseSchema):
    modules: List[ModuleResponse] = []
    item_usage: Optional[str] = Field(None, serialization_alias="itemUsage")
    item_desc: Optional[str] = Field(None, serialization_alias="itemDesc")