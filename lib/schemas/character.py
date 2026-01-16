from typing import List, Optional, Generic, TypeVar
from pydantic import Field, computed_field, ConfigDict
from lib.schemas.common import (
    BaseSchema, ProfessionResponse, SubProfessionResponse, 
    TagResponse, RangeResponse
)
from lib.schemas.skill import SkillResponse
from lib.schemas.module import ModuleResponse
from lib.schemas.item import ItemResponse

BASE_IMAGE_URL = "https://raw.githubusercontent.com/fexli/ArknightsResource/main/charpack/"

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

# 요청하신 Base URL 상수화
CHARPACK_BASE_URL = "https://raw.githubusercontent.com/fexli/ArknightsResource/main/charpack/"

class CharacterListResponse(BaseSchema):
    character_id: int
    code: str
    name_ko: str
    rarity: int
    profession: Optional[ProfessionResponse] = None
    sub_profession: Optional[SubProfessionResponse] = None

    # ORM 객체 변환 설정
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

    @computed_field
    @property
    def skin_url(self) -> str:
        """
        [Logic]
        1. 캐릭터의 스킨 목록 중 가장 적절한(보통 첫 번째 혹은 기본) 스킨의 portrait_id를 추출합니다.
        2. 스킨 정보가 없으면 캐릭터 코드(code)를 Fallback ID로 사용합니다.
        3. Kotlin 로직과 동일하게 '#' 문자를 '_'로 치환합니다.
        """
        # 1. ID 선정 (Default: 캐릭터 코드)
        target_id = self.code
        
        # SQLAlchemy selectinload로 로드된 skins 리스트 확인
        # (characters 테이블과 1:N 관계인 skins 테이블에서 데이터를 가져옴)
        skins = getattr(self, "skins", [])
        
        if skins:
            # 우선순위: portrait_id가 존재하는 첫 번째 스킨
            # (실무에서는 is_default 플래그 등을 확인하는 것이 더 정확할 수 있습니다)
            for skin in skins:
                if skin.portrait_id:
                    target_id = skin.portrait_id
                    break
        
        # 2. String Manipulation (Kotlin Logic Porting)
        # URL에서 #은 Fragment로 인식되므로 파일명 규칙에 맞춰 _로 치환
        safe_file_name = target_id.replace("#", "_")
        
        return f"{CHARPACK_BASE_URL}{safe_file_name}.png"
    
    
# 3. 상세 프로필 (API 1: Profile)
class CharacterProfileResponse(CharacterListResponse):
    class_description: Optional[str] = None
    tags: List[TagResponse] = []
    stats: List[CharacterStatResponse] = []
    item_usage: Optional[str] = None
    item_desc: Optional[str] = None

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
