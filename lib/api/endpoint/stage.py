from typing import List
from fastapi import APIRouter, Depends
from lib.schemas.stage import ZoneDetailResponse
from lib.service.stage import StageService
from lib.api import deps

router = APIRouter()

@router.get("/zones", response_model=List[ZoneDetailResponse])
async def read_all_zones(
    service: StageService = Depends(deps.get_stage_service)
):
    """
    모든 작전 구역(Zone) 및 스테이지(Stage) 계층 목록 조회
    - 메인 화면 진입 시 호출 권장
    - Redis Cache 적용됨 (1주일) -> 매우 빠름
    """
    return await service.get_all_zones()