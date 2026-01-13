from typing import List, Optional, Generic, TypeVar
from pydantic import Field, computed_field, ConfigDict
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
    max_level: int
    base_hp: int
    base_atk: int
    base_def: int
    max_hp: int
    max_atk: int
    max_def: int
    magic_resistance: int
    cost: int
    block_cnt: int
    range_data: Optional[RangeResponse] = None

# 2. 리스트 조회용 (Lightweight)
class CharacterListResponse(BaseSchema):
    character_id: int
    code: str
    name_ko: str
    rarity: int
    profession: Optional[ProfessionResponse] = None
    sub_profession: Optional[SubProfessionResponse] = None

    model_config = ConfigDict(
        from_attributes=True,   # DB 객체(ORM)에서 직접 데이터를 읽어올 때 필수
        populate_by_name=True   # 필드명 그대로 데이터를 넣는 것을 허용
    )

    @computed_field
    @property
    def icon_url(self) -> str:
        return f"https://github.com/fexli/ArknightsResource/tree/main/charpack/{self.code}.png"

# 3. 상세 프로필 (API 1: Profile)
class CharacterProfileResponse(CharacterListResponse):
    class_description: Optional[str] = None
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
    skill_costs: List[CharacterSkillCostResponse] = []

# 6. 모듈 및 스토리 (API 4: Modules)
class CharacterModuleResponse(BaseSchema):
    modules: List[ModuleResponse] = []
    item_usage: Optional[str] = None
    item_desc: Optional[str] = None

class CharacterFullDetailResponse(BaseSchema):
    """
    **통합 캐릭터 상세 정보 응답 스키마**
    4개의 도메인 데이터를 하나의 객체로 묶습니다.
    """
    profile: CharacterProfileResponse = Field(..., description="캐릭터 기본 프로필")
    skills: CharacterSkillDetailResponse = Field(..., description="스킬 상세 정보")
    growth: CharacterGrowthResponse = Field(..., description="육성 및 재료 정보")
    modules: CharacterModuleResponse = Field(..., description="모듈 및 스토리 정보")

    class Config:
        # 데이터가 SQLAlchemy 모델일 경우 자동으로 변환되도록 설정
        from_attributes = True

T = TypeVar("T")

class BaseResponse(BaseSchema, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    status: int = Field(200, description="HTTP code")
    message: str = "OK"
