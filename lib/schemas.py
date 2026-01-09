from pydantic import BaseModel, Field, computed_field, ConfigDict, field_validator
from typing import List, Optional
from urllib.parse import quote
from lib.model import ProfessionEnum, ConsumptionTypeEnum

# 정적 자산 URL 설정
ASSET_PORTRAIT_URL = "https://raw.githubusercontent.com/ArknightsAssets/ArknightsAssets2/refs/heads/cn/assets/dyn/arts/charportraits"
ASSET_AVATAR_URL = "https://raw.githubusercontent.com/Aceship/Arknight-Images/master/avatars"
ASSET_ITEM_URL = "https://raw.githubusercontent.com/Aceship/Arknight-Images/master/items"

# 1. 아이템 정보
class ItemDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    item_id: str
    name: Optional[str] = None
    rarity: int = 0
    icon_id: Optional[str] = None

    @computed_field
    def icon_url(self) -> str:
        target_id = self.icon_id if self.icon_id else self.item_id
        return f"{ASSET_ITEM_URL}/{target_id}.png"

# 2. 스킨 정보
class SkinDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skin_id: str
    name: Optional[str] = None
    group_name: Optional[str] = None
    illust_id: Optional[str] = None
    avatar_id: Optional[str] = None
    portrait_id: Optional[str] = None
    # None이 들어와도 빈 리스트로 처리되도록 validator 추가 혹은 타입 수정
    drawer_list: Optional[List[str]] = Field(default_factory=list) 

    @field_validator('drawer_list', mode='before')
    @classmethod
    def allow_none_for_list(cls, v):
        return v if v is not None else []
    
    @computed_field
    def portrait_url(self) -> str:
        target_id = self.portrait_id or (self.illust_id.replace("illust_", "") if self.illust_id else None)
        if not target_id: return ""
        return f"{ASSET_PORTRAIT_URL}/{quote(target_id)}.png"

    @computed_field
    def avatar_url(self) -> str:
        if not self.avatar_id: return ""
        return f"{ASSET_AVATAR_URL}/{quote(self.avatar_id)}.png"

# 3. 재료 소모 정보
class ConsumptionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: ConsumptionTypeEnum  # Enum 적용
    level: int
    count: int
    item: ItemDTO

# 4. 스탯 상세 정보
class AttributeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    level: int
    max_hp: int
    atk: int
    def_: int = Field(alias="def")
    magic_resistance: float
    cost: int
    block_cnt: int
    move_speed: float
    attack_speed: float

# 5. 정예화 단계별 정보
class PhaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    phase_index: int
    max_level: int
    attributes: List[AttributeDTO] = []

# 6. 캐릭터 목록용 (경량화된 스키마)
class CharacterList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    char_id: str
    name: str
    rarity: int
    profession: ProfessionEnum  # Enum 적용
    skins: List[SkinDTO] = []

    @computed_field
    def portrait_url(self) -> str:
        return self.skins[0].portrait_url if self.skins else ""

# 7. 캐릭터 상세 정보 (모든 관계 포함)
class CharacterDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    char_id: str
    name: str
    rarity: int
    profession: ProfessionEnum
    description: Optional[str] = None
    
    skins: List[SkinDTO] = []
    phases: List[PhaseDTO] = []
    consumptions: List[ConsumptionDTO] = []