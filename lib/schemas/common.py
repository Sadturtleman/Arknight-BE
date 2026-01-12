from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, Any, List

class BaseSchema(BaseModel):
    """모든 스키마의 공통 부모"""
    model_config = ConfigDict(from_attributes=True) # ORM 객체를 Pydantic으로 자동 변환 (구 orm_mode)

class GridElement(BaseModel):
    row: int
    col: int

class ProfessionResponse(BaseSchema):
    profession_id: int
    name_ko: str

class SubProfessionResponse(BaseSchema):
    sub_profession_id: int
    name_ko: str

class TagResponse(BaseSchema):
    tag_id: int
    tag_name: str

class RangeResponse(BaseSchema):
    range_id: str
    grids: List[GridElement] # JSONB 데이터는 dict로 변환

