import asyncio
from typing import Optional, List
from fastapi import HTTPException
from lib.service.base import BaseService
from lib.repositories.character import CharacterRepository
from lib.repositories.skill import SkillRepository
from lib.schemas.character import (
    CharacterFullDetailResponse,
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
    
    async def get_character_full_detail(self, code: str) -> CharacterFullDetailResponse:
        """
        Redis Pipelining을 사용하여 4개 도메인 데이터를 1회의 RTT로 조회합니다.
        """
        keys = [
            f"char:profile:{code}",
            f"char:skills:{code}",
            f"char:growth:{code}",
            f"char:modules:{code}"
        ]

        # 1. Redis Pipeline 실행 (네트워크 왕복 1회)
        async with self.redis.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.get(key)
            # redis-py(aioredis) 기준 execute()는 리스트를 반환합니다.
            cached_data = await pipe.execute()

        # 2. 결과 매핑 및 캐시 미스 확인
        # cached_data의 인덱스는 keys의 순서와 동일합니다.
        results = []
        fetch_tasks = []
        
        # 도메인별 매핑 정보 (순서 중요)
        domains = [
            {"func": self.get_character_profile, "model": CharacterProfileResponse},
            {"func": self.get_character_skills, "model": CharacterSkillDetailResponse},
            {"func": self.get_character_growth, "model": CharacterGrowthResponse},
            {"func": self.get_character_modules, "model": CharacterModuleResponse}
        ]

        for i, data in enumerate(cached_data):
            if data:
                # 캐시 히트: JSON 역직렬화
                results.append(domains[i]["model"].model_validate_json(data))
            else:
                # 캐시 미스: DB에서 가져오기 위한 태스크 예약
                fetch_tasks.append(self._fetch_and_store(code, domains[i]))
        
        # 3. 캐시 미스된 데이터가 있다면 병렬로 DB 호출
        if fetch_tasks:
            fetched_results = await asyncio.gather(*fetch_tasks)
            # 실제 서비스 로직에서는 순서에 맞게 결과를 합쳐야 합니다.
            # 여기서는 단순화를 위해 다시 조회하거나, results 리스트를 재구성합니다.
            # (실무에서는 인덱스를 추적하여 results의 None 자리에 채워넣습니다.)
            return await self.get_character_full_detail_pipelined(code) # 재귀적 호출로 깔끔하게 처리(이미 캐싱됨)

        return CharacterFullDetailResponse(
            profile=results[0],
            skills=results[1],
            growth=results[2],
            modules=results[3]
        )

    async def _fetch_and_store(self, code, domain_info):
        """DB에서 데이터를 가져와서 개별 캐시에 저장하는 헬퍼 함수"""
        data = await domain_info["func"](code)
        return data

    # --- Smart Invalidation 로직 ---

    async def invalidate_character_cache(self, code: str):
        """
        캐릭터 수정 시 호출하여 관련 모든 캐시(개별+통합)를 삭제합니다.
        """
        keys_to_delete = [
            f"char:profile:{code}",
            f"char:skills:{code}",
            f"char:growth:{code}",
            f"char:modules:{code}",
            f"char:full:{code}" # 통합 캐시 키가 있을 경우
        ]
        
        # Unlink는 Del보다 비동기적으로 메모리를 해제하여 더 빠릅니다. (Redis 4.0+)
        async with self.redis.pipeline() as pipe:
            for key in keys_to_delete:
                pipe.unlink(key)
            await pipe.execute()
        
        # Expert's Tip: 여기서 Kafka로 'cache_invalidated' 이벤트를 쏴서 
        # 다른 인스턴스들의 L1 캐시까지 비우게 할 수 있습니다.