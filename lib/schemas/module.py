from typing import List, Optional
from lib.schemas.common import BaseSchema
from lib.schemas.item import ItemResponse

class ModuleCostResponse(BaseSchema):
    level: int
    count: int
    item: ItemResponse # 재료 아이템 정보 중첩

class ModuleResponse(BaseSchema):
    module_id: int
    module_code: str
    name_ko: str
    icon_id: Optional[str] = None
    description: Optional[str] = None
    costs: List[ModuleCostResponse] = [] # 강화 재료 리스트