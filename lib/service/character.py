from typing import Optional, List
from fastapi import HTTPException
from lib.service.base import BaseService
from lib.repositories.character import CharacterRepository
from lib.repositories.skill import SkillRepository
from lib.schemas.character import (
    CharacterListResponse,
    CharacterProfileResponse,
    CharacterSkillDetailResponse,
    CharacterGrowthResponse,
    CharacterModuleResponse
)

class CharacterService(BaseService):
    def __init__(
        self, 
        repo: CharacterRepository, 
        skill_repo: SkillRepository,
        redis
    ):
        super().__init__(redis)
        self.repo = repo
        self.skill_repo = skill_repo

    # 1. 기본 프로필 조회 (가장 가벼운 첫 번째 응답용)
    async def get_character_profile(self, code: str) -> CharacterProfileResponse:
        cache_key = f"char:profile:{code}"

        async def fetch_data():
            char = await self.repo.get_profile(code)
            if not char:
                return None
            # 아이콘 URL 등 가공 로직이 필요하다면 여기서 수행
            return char

        character = await self.get_with_cache(
            key=cache_key,
            fetch_func=fetch_data,
            schema_model=CharacterProfileResponse,
            ttl=3600
        )

        if not character:
            raise HTTPException(status_code=404, detail=f"Operator {code} not found")
        return character

    # 2. 스킬 상세 정보 조회 (스킬 데이터는 양이 많으므로 별도 분리)
    async def get_character_skills(self, code: str) -> CharacterSkillDetailResponse:
        cache_key = f"char:skills:{code}"

        async def fetch_data():
            # 스킬 슬롯 정보를 먼저 가져옴
            char = await self.repo.get_skill_slots(code)
            if not char or not char.skill_slots:
                return {"skills": []}
            
            skill_codes = []
            slots = char.skill_slots
            if slots.phase_0_code: skill_codes.append(slots.phase_0_code)
            if slots.phase_1_code: skill_codes.append(slots.phase_1_code)
            if slots.phase_2_code: skill_codes.append(slots.phase_2_code)
            
            if not skill_codes:
                return {"skills": []}

            # 실제 스킬 상세 데이터 조회 (skill_repo 활용)
            skills_data = await self.skill_repo.get_by_codes(skill_codes)
            return {"skills": skills_data}

        return await self.get_with_cache(
            key=cache_key,
            fetch_func=fetch_data,
            schema_model=CharacterSkillDetailResponse,
            ttl=3600
        )

    # 3. 육성 재료/성장 정보 조회 (계산기나 육성 탭 진입 시 사용)
    async def get_character_growth(self, code: str) -> CharacterGrowthResponse:
        cache_key = f"char:growth:{code}"

        async def fetch_data():
            char = await self.repo.get_growth_info(code)
            if not char:
                return None
            return char

        growth_data = await self.get_with_cache(
            key=cache_key,
            fetch_func=fetch_data,
            schema_model=CharacterGrowthResponse,
            ttl=3600
        )
        
        if not growth_data:
             raise HTTPException(status_code=404, detail=f"Growth data for {code} not found")
        return growth_data

    # 4. 모듈 및 상세 스토리 조회 (하단 탭 또는 모듈 확인 시 사용)
    async def get_character_modules(self, code: str) -> CharacterModuleResponse:
        cache_key = f"char:modules:{code}"

        async def fetch_data():
            char = await self.repo.get_module_info(code)
            if not char:
                return None
            return char

        return await self.get_with_cache(
            key=cache_key,
            fetch_func=fetch_data,
            schema_model=CharacterModuleResponse,
            ttl=3600
        )

    # 5. 리스트 조회 (기존 로직 유지)
    async def get_character_list(self, skip: int = 0, limit: int = 20, rarity: Optional[int] = None):
        rarity_key = rarity if rarity is not None else "all"
        cache_key = f"char:list:{skip}:{limit}:{rarity_key}"

        return await self.get_list_with_cache(
            key=cache_key,
            fetch_func=lambda: self.repo.get_list(skip, limit, rarity),
            schema_model=CharacterListResponse,
            ttl=300 
        )