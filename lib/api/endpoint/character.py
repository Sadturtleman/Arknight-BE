from typing import List
from fastapi import APIRouter, Depends, Query
from lib.schemas.character import (
    CharacterListResponse, 
    CharacterProfileResponse,
    CharacterSkillDetailResponse,
    CharacterGrowthResponse,
    CharacterModuleResponse
)
from lib.service.character import CharacterService
from lib.api import deps

# 라우터 경로 및 태그 설정
router = APIRouter()

@router.get("", response_model=List[CharacterListResponse])
async def read_characters(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    rarity: int = Query(None, ge=1, le=6, description="캐릭터 등급 (1~6)"),
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **캐릭터 목록 조회 (Paging)**
    - Redis Cache: 5분
    - 가벼운 List용 스키마를 반환하여 검색/목록 성능 최적화
    """
    return await service.get_character_list(skip=skip, limit=limit, rarity=rarity)

@router.get("/{code}/profile", response_model=CharacterProfileResponse)
async def read_character_profile(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 1] 캐릭터 기본 프로필**
    - 캐릭터 진입 시 **가장 먼저 호출**해야 하는 API입니다.
    - 기본 정보, 태그, 기초 스탯 정보를 포함합니다.
    - Redis Cache: 1시간
    """
    return await service.get_character_profile(code)

@router.get("/{code}/skills", response_model=CharacterSkillDetailResponse)
async def read_character_skills(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 2] 스킬 상세 정보**
    - 캐릭터의 모든 스킬 및 레벨별 상세 수치(Blackboard)를 포함합니다.
    - Redis Cache: 1시간
    """
    return await service.get_character_skills(code)

@router.get("/{code}/growth", response_model=CharacterGrowthResponse)
async def read_character_growth(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 3] 육성 재료 정보**
    - 스킬 강화(마스터리 포함)에 필요한 재료 목록을 포함합니다.
    - Redis Cache: 1시간
    """
    return await service.get_character_growth(code)

@router.get("/{code}/modules", response_model=CharacterModuleResponse)
async def read_character_modules(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 4] 모듈 및 상세 텍스트**
    - 전용 모듈 정보 및 캐릭터 사용 설명(Item Usage)을 포함합니다.
    - Redis Cache: 1시간
    """
    return await service.get_character_modules(code)