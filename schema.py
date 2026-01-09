from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, computed_field

# =======================================================================
# [설정] Fexli 리포지토리 URL
# 1. raw.githubusercontent.com 사용 시 (원본)
# ASSET_BASE_URL = "https://raw.githubusercontent.com/fexli/ArknightsResource/main"
#
# 2. jsDelivr CDN 사용 시 (추천: 속도가 훨씬 빠름)
# 주의: 'main' 브랜치인지 'master' 브랜치인지 확인 후 수정하세요.
# =======================================================================
ASSET_BASE_URL = "https://raw.githubusercontent.com/fexli/ArknightsResource/main"

# 폴더 경로 설정 (리포지토리 실제 폴더명과 일치시켜야 함)
PATH_AVATAR = "charpack"          # 예: 오퍼레이터 얼굴 아이콘 폴더
PATH_PORTRAIT = "portrait"      # 예: 전신 일러스트 폴더
PATH_SKILL = "skills"            # 예: 스킬 아이콘 폴더
PATH_CLASS = "class"            # 예: 직군 아이콘 폴더
PATH_MODULE = "equip"        # 예: 모듈 아이콘 폴더
PATH_ITEM = "items"

# 1. 공통 설정
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 1. 하위 모델 (스킬, 모듈, 스킨 등)
# ==========================================
class ItemCostSchema(BaseModel):
    # DB의 JSON 데이터: [{"id": "30011", "count": 1, ...}]
    # JSON 키와 변수명이 같아야 자동으로 매핑됩니다.
    id: str     # 아이템 ID
    count: int  # 개수
    type: Optional[str] = None # MATERIAL 등 (있을 수도 없을 수도 있음)

    @computed_field
    def icon_url(self) -> str:
        # 아이템 이미지 URL 생성
        return f"{ASSET_BASE_URL}/{PATH_ITEM}/{self.id}.png"
    
class SkillInfoSchema(BaseSchema):
    skill_id: str
    name_ko: str
    icon_id: Optional[str] = None

    @computed_field
    def icon_url(self) -> str:
        # 스킬 아이콘
        target_id = self.icon_id if self.icon_id else self.skill_id
        return f"{ASSET_BASE_URL}/{PATH_SKILL}/skill_icon_{target_id}.png"

class OperatorSkillSchema(BaseSchema):
    skill_index: int
    unlock_phase: int
    skill_info: Optional[SkillInfoSchema] = None

class ModuleSchema(BaseSchema):
    module_id: str
    display_text: Dict[str, Any]
    
    @computed_field
    def icon_url(self) -> str:
        # 모듈 아이콘
        return f"{ASSET_BASE_URL}/{PATH_MODULE}/{self.module_id}.png"

class ConsumptionSchema(BaseSchema):
    cost_type: str
    level: int
    # 👇 [수정] Dict 대신 ItemCostSchema 사용 (그래야 icon_url이 생김)
    ingredients: List[ItemCostSchema]
    
class SkinSchema(BaseSchema):
    skin_id: str
    name_ko: Optional[str] = None
    category: str
    display_data: Dict[str, Any]

    @computed_field
    def portrait_url(self) -> str:
        # 스킨 일러스트 (파일명 규칙 확인 필요)
        # 보통 스킨 ID 뒤에 _1, _1b 등이 붙음. 우선 _1로 가정
        return f"{ASSET_BASE_URL}/{PATH_PORTRAIT}/{self.skin_id}_1.png"
    
    @computed_field
    def avatar_url(self) -> str:
        # 스킨 착용 아바타
        return f"{ASSET_BASE_URL}/{PATH_AVATAR}/{self.skin_id}.png"

# ==========================================
# 2. 메인 응답 모델 (오퍼레이터)
# ==========================================

class OperatorSummary(BaseSchema):
    """목록 조회용 요약 정보"""
    operator_id: str
    name_ko: str
    rarity: int
    profession: str
    
    @computed_field
    def avatar_url(self) -> str:
        # 기본 아바타
        return f"{ASSET_BASE_URL}/{PATH_AVATAR}/{self.operator_id}.png"

    @computed_field
    def class_icon_url(self) -> str:
        # 직군 아이콘 (profession은 대문자이므로 소문자로 변환)
        return f"{ASSET_BASE_URL}/{PATH_CLASS}/class_{self.profession.lower()}.png"

class OperatorDetail(BaseSchema):
    """상세 조회용 전체 정보"""
    operator_id: str
    name_ko: str
    rarity: int
    profession: str
    description: Optional[str] = None
    
    @computed_field
    def portrait_url(self) -> str:
        # 기본 일러스트 (2정예 우선)
        # 리포지토리 파일명이 {id}_2.png 인지 확인 필요
        suffix = "_2" if self.rarity >= 3 else "_1"
        return f"{ASSET_BASE_URL}/{PATH_PORTRAIT}/{self.operator_id}{suffix}.png"

    # 관계 데이터
    skills: List[OperatorSkillSchema] = []
    modules: List[ModuleSchema] = []
    consumptions: List[ConsumptionSchema] = []
    skins: List[SkinSchema] = []