from typing import List
from fastapi import APIRouter, Depends, Query
from lib.schemas.character import (
    BaseResponse,
    CharacterFullDetailResponse,
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

@router.get("", response_model=BaseResponse[List[CharacterListResponse]])
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
    character_list =  await service.get_character_list(skip=skip, limit=limit, rarity=rarity)

    return BaseResponse(
        success=True,
        data = character_list,
    )
    
@router.get("/{code}/profile", response_model=BaseResponse[CharacterProfileResponse])
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
    character_profile = await service.get_character_profile(code)

    return BaseResponse(
        success=True,
        data = character_profile
    )

@router.get("/{code}/skills", response_model=BaseResponse[CharacterSkillDetailResponse])
async def read_character_skills(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 2] 스킬 상세 정보**
    - 캐릭터의 모든 스킬 및 레벨별 상세 수치(Blackboard)를 포함합니다.
    - Redis Cache: 1시간
    """
    character_skill = await service.get_character_skills(code)

    return BaseResponse(
        success=True,
        data = character_skill
    )

@router.get("/{code}/growth", response_model=BaseResponse[CharacterGrowthResponse])
async def read_character_growth(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 3] 육성 재료 정보**
    - 스킬 강화(마스터리 포함)에 필요한 재료 목록을 포함합니다.
    - Redis Cache: 1시간
    """
    character_grouth = await service.get_character_growth(code)
    return BaseResponse(
        success=True,
        data = character_grouth
    )

@router.get("/{code}/modules", response_model=BaseResponse[CharacterModuleResponse])
async def read_character_modules(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Domain 4] 모듈 및 상세 텍스트**
    - 전용 모듈 정보 및 캐릭터 사용 설명(Item Usage)을 포함합니다.
    - Redis Cache: 1시간
    """
    character_module = await service.get_character_modules(code)
    return BaseResponse(
        success=True,
        data = character_module
    )

@router.get("/{code}/full-detail", response_model=BaseResponse[CharacterFullDetailResponse])
async def read_character_full_detail(
    code: str,
    service: CharacterService = Depends(deps.get_character_service)
):
    """
    **[Aggregator] 캐릭터 모든 상세 정보 통합 조회**
    - Profile, Skills, Growth, Modules를 한 번에 반환합니다.
    - 내부적으로 Redis Pipelining을 사용하여 네트워크 성능을 극대화했습니다.
    """
    # 서비스 레이어에서 1회의 RTT로 모든 데이터를 가져옵니다.
    character_detail = await service.get_character_full_detail(code)

    return BaseResponse(
        success=True,
        data = character_detail
    )