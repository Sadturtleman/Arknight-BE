from typing import List, Optional
from lib.schemas.common import BaseSchema

# ==========================
# 1. Stage (Child)
# ==========================
class StageResponse(BaseSchema):
    stage_id: int
    stage_code: str      # 고유 코드 (예: main_01-07)
    display_code: str    # 화면 표시용 (예: 1-7)
    name_ko: str         # 맵 이름 (예: 맹독)
    description: Optional[str] = None
    ap_cost: int         # 이성 소모량
    danger_level: Optional[str] = None # 권장 레벨

class StageDetailResponse(StageResponse):
    """스테이지 상세 조회 시, 해당 스테이지가 속한 Zone 정보도 필요할 수 있음"""
    zone_id: int
    # 필요하다면 여기에 적(Enemy) 정보나 드랍 아이템 리스트 추가

# ==========================
# 2. Zone (Parent)
# ==========================
class ZoneResponse(BaseSchema):
    """Zone 목록 조회용 (가벼움)"""
    zone_id: int
    zone_code: str
    name_ko: str
    zone_type: Optional[str] = None # MAINLINE, WEEKLY 등
    zone_index: int

class ZoneDetailResponse(ZoneResponse):
    """Zone 상세 조회용 (해당 챕터의 스테이지 리스트 포함)"""
    # 1:N 관계 - Zone 하나에 여러 Stage가 포함됨
    stages: List[StageResponse] = []