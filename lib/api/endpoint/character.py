from typing import List
from fastapi import APIRouter, Depends, Query
from lib.schemas.character import CharacterListResponse, CharacterDetailResponse
from lib.service.character import CharacterService
from lib.api import deps

router = APIRouter()

@router.get("", response_model=List[CharacterListResponse])
async def read_characters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    rarity: int = Query(None, ge = 1, le = 6, description="등급"),
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    캐릭터 목록 조회 (Paging)
    - Redis Cache 적용됨 (5분)
    - 가벼운 List용 스키마 반환
    """
    return await service.get_character_list(skip=skip, limit=limit, rarity = rarity)

@router.get("/{code}", response_model=CharacterDetailResponse)
async def read_character_detail(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    캐릭터 상세 정보 조회
    - code: 고유 코드 (예: 1001_amiya)
    - Redis Cache 적용됨 (1시간)
    - 스탯, 스킬, 모듈 등 모든 상세 정보 포함
    """
    return await service.get_character_detail(code)