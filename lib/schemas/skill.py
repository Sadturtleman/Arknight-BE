from typing import List, Optional, Dict, Any
from lib.schemas.common import BaseSchema, RangeResponse
from lib.schemas.item import ItemResponse

class SkillLevelResponse(BaseSchema):
    level: int
    sp_cost: int    
    initial_sp: int
    duration: float
    description: Optional[str] = None
    blackboard: List[dict] # 스킬 계수 등 JSON 데이터
    range_data: Optional[RangeResponse] = None # 스킬 범위

class SkillResponse(BaseSchema):
    skill_id: int
    skill_code: str
    name_ko: str
    icon_id: Optional[str] = None
    levels: List[SkillLevelResponse] = [] # 스킬 레벨 상세 리스트 포함
    mastery_costs: List[MasteryCostResponse] = []
    
class MasteryCostResponse(BaseSchema):
    mastery_level: int
    count: int
    item: ItemResponse