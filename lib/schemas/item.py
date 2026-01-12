from typing import Optional
from lib.schemas.common import BaseSchema

class ItemResponse(BaseSchema):
    item_id: int
    item_code: str
    name_ko: str
    rarity: int
    icon_id: Optional[str] = None
    item_type: Optional[str] = None
    description: Optional[str] = None
    # 리스트 뷰에서는 사용법(usage)이나 획득처(obtain) 같은 긴 텍스트는 뺍니다 (최적화)

class ItemDetailResponse(ItemResponse):
    """상세 조회용 (무거운 텍스트 포함)"""
    usage_text: Optional[str] = None
    obtain_approach: Optional[str] = None