from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from urllib.parse import quote

ASSET_PORTRAIT_URL = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsAssets2/refs/heads/cn/assets/dyn/arts/charportraits"
ASSET_AVATAR_URL = "https://raw.githubusercontent.com/Aceship/Arknight-Images/master/avatars"


# 1. 아이템 정보 (내부용)
class ItemDTO(BaseModel):
    item_id: str
    name: Optional[str] = None
    rarity: Optional[int] = 0

    class Config:
        from_attributes = True  # ORM 객체를 Pydantic으로 변환 허용

# 2. 재료 소모 정보
class ConsumptionDTO(BaseModel):
    type: str
    level: int
    count: int
    item: ItemDTO  # 위에 정의한 아이템 정보 포함

    class Config:
        from_attributes = True

# 4. 캐릭터 목록용 (가볍게)
class CharacterList(BaseModel):
    char_id: str
    name: str
    rarity: str
    profession: str
    skins: List[SkinDTO] = []  # 추가

    class Config:
        from_attributes = True
    
    # 대표 portrait URL 추가
    @computed_field
    def portrait_url(self) -> str:
        if self.skins and len(self.skins) > 0:
            return self.skins[0].portrait_url
        return ""
    
# 1. 스킨 정보
class SkinDTO(BaseModel):
    skin_id: str
    name: Optional[str] = None
    group_name: Optional[str] = None
    illust_id: Optional[str] = None
    avatar_id: Optional[str] = None
    portrait_id: Optional[str] = None  # DB에 있는 portrait_id 필드 추가
    drawer_list: Optional[List[str]] = []

    class Config:
        from_attributes = True

    # 전신 일러스트 URL (portrait_id 기준)
    @computed_field
    def portrait_url(self) -> str:
        # 1순위: portrait_id 사용 (데이터가 제일 깔끔함)
        target_id = self.portrait_id
        
        # 2순위: 없으면 illust_id에서 'illust_' 떼고 사용
        if not target_id and self.illust_id:
            target_id = self.illust_id.replace("illust_", "")
            
        if not target_id:
            return ""

        # URL 인코딩 (특수문자 # 처리)
        encoded_id = quote(target_id)
        return f"{ASSET_PORTRAIT_URL}/{encoded_id}.png"

    # 아이콘(Avatar) URL
    @computed_field
    def avatar_url(self) -> str:
        if not self.avatar_id:
            return ""
        
        encoded_id = quote(self.avatar_id)
        return f"{ASSET_AVATAR_URL}/{encoded_id}.png"

# 2. 스탯 상세 정보 (HP, 공격력 등)
class AttributeDTO(BaseModel):
    level: int
    max_hp: int
    atk: int
    def_: int = Field(alias="def") # DB 컬럼명 매핑
    magic_resistance: float
    cost: int
    block_cnt: int

    class Config:
        from_attributes = True
        populate_by_name = True # alias 사용 허용

# 3. 정예화 단계별 정보 (Phase)
class PhaseDTO(BaseModel):
    phase_index: int     # 0, 1, 2 (정예화 단계)
    max_level: int       # 해당 단계 만렙
    attributes: List[AttributeDTO] = [] # 해당 단계의 레벨별 스탯 리스트

    class Config:
        from_attributes = True

# 4. 캐릭터 상세 정보 (최종 합체)
class CharacterDetail(BaseModel):
    char_id: str
    name: str
    rarity: str
    profession: str
    description: Optional[str] = None
    
    # 추가된 정보들
    skins: List[SkinDTO] = []       # 스킨 목록
    phases: List[PhaseDTO] = []     # 정예화별 스탯 목록
    consumptions: List[ConsumptionDTO] = [] # 재료 목록

    class Config:
        from_attributes = True