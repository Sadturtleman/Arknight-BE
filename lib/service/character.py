from typing import Optional
from fastapi import HTTPException
from lib.service.base import BaseService
from lib.repositories.character import CharacterRepository
from lib.repositories.skill import SkillRepository
from lib.schemas.character import CharacterListResponse, CharacterDetailResponse

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

    async def get_character_detail(self, code: str) -> CharacterDetailResponse:
        cache_key = f"char:detail:{code}"

        # 내부 fetch 함수 정의
        async def fetch_data():
            # 1. 캐릭터 기본 정보 조회
            char = await self.repo.get_by_code_with_details(code)
            if not char:
                return None
            # 2. 스킬 코드를 추출 (skill_slots가 있다면)
            skill_codes = []
            if char.skill_slots:
                if char.skill_slots.phase_0_code: skill_codes.append(char.skill_slots.phase_0_code)
                if char.skill_slots.phase_1_code: skill_codes.append(char.skill_slots.phase_1_code)
                if char.skill_slots.phase_2_code: skill_codes.append(char.skill_slots.phase_2_code)
            
            # 3. 실제 스킬 데이터 조회
            skills_data = []
            if skill_codes:
                skills_data = await self.skill_repo.get_by_codes(skill_codes)

            # 4. ORM 객체에 동적으로 skills 속성 주입 (Pydantic 변환용)
            # SQLAlchemy 모델에는 'skills' 필드가 없지만, Python 객체이므로 임시 할당 가능
            char.skills = skills_data 
            
            return char

        # 캐싱 로직 실행
        character = await self.get_with_cache(
            key=cache_key,
            fetch_func=fetch_data,
            schema_model=CharacterDetailResponse,
            ttl=3600
        )

        if not character:
            raise HTTPException(status_code=404, detail=f"Character {code} not found")
            
        return character

    async def get_character_list(self, skip: int = 0, limit: int = 20, rarity: Optional[int] = None):
        # 리스트는 페이지네이션 파라미터가 키에 포함되어야 함

        rarity_key = rarity if rarity is not None else "all"
        cache_key = f"char:list:{skip}:{limit}:{rarity_key}"

        return await self.get_list_with_cache(
            key=cache_key,
            fetch_func=lambda: self.repo.get_list(skip, limit, rarity),
            schema_model=CharacterListResponse,
            ttl=300 # 리스트는 갱신이 잦을 수 있으니 5분만 캐시
        )