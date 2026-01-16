from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from lib.models.character import (
    Character, 
    CharacterStat, 
    CharacterSkillCost
)
from lib.models.module import CharacterModule, CharacterModuleCost
from lib.repositories.base import BaseRepository

class CharacterRepository(BaseRepository[Character]):
    def __init__(self, db):
        super().__init__(Character, db)

    # 1. 목록 조회 (가장 가볍게 로드)
    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        rarity: Optional[int] = None
    ) -> List[Character]:
        query = select(Character).options(
            selectinload(Character.profession),
            selectinload(Character.sub_profession),
            selectinload(Character.skins)
        )

        if rarity is not None:
            query = query.where(Character.rarity == rarity)

        # 희귀도 높은 순, 코드 순 정렬
        query = query.order_by(Character.rarity.desc(), Character.code.asc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    # 2. 프로필 정보 (Profile Domain)
    async def get_profile(self, code: str) -> Optional[Character]:
        query = (
            select(Character)
            .where(Character.code == code)
            .options(
                selectinload(Character.profession),
                selectinload(Character.sub_profession),
                # 스탯과 그에 딸린 사거리 데이터 로드
                selectinload(Character.stats).selectinload(CharacterStat.range_data),
                selectinload(Character.talents),
                selectinload(Character.tags)
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    # 3. 스킬 슬롯 정보 (Skill Domain - 코드만 추출하기 위함)
    async def get_skill_slots(self, code: str) -> Optional[Character]:
        query = (
            select(Character)
            .where(Character.code == code)
            .options(selectinload(Character.skill_slots))
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    # 4. 성장 및 재료 정보 (Growth Domain)
    async def get_growth_info(self, code: str) -> Optional[Character]:
        query = (
            select(Character)
            .where(Character.code == code)
            .options(
                selectinload(Character.favor),
                # 스킬 강화 재료와 해당 아이템 정보
                selectinload(Character.skill_costs)
                    .selectinload(CharacterSkillCost.item)
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    # 5. 모듈 및 상세 스토리 (Module Domain)
    async def get_module_info(self, code: str) -> Optional[Character]:
        query = (
            select(Character)
            .where(Character.code == code)
            .options(
                selectinload(Character.detail),
                # 모듈 -> 모듈 비용 -> 아이템 정보까지 체이닝 로드
                selectinload(Character.modules)
                    .selectinload(CharacterModule.costs)
                    .selectinload(CharacterModuleCost.item)
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()