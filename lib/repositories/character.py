from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from lib.models.character import Character, CharacterStat, CharacterSkillCost
from lib.models.module import CharacterModule, CharacterModuleCost  # [필수] 모듈 관련 모델 Import
from lib.repositories.base import BaseRepository

class CharacterRepository(BaseRepository[Character]):
    def __init__(self, db):
        super().__init__(Character, db)

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        rarity: Optional[int] = None
    ) -> List[Character]:
        """
        목록 조회 (Lightweight)
        """
        query = select(Character).options(
            selectinload(Character.profession),
            selectinload(Character.sub_profession)
        )

        if rarity is not None:
            query = query.where(Character.rarity == rarity)

        query = query.order_by(Character.rarity.desc(), Character.code.asc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_code_with_details(self, code: str) -> Optional[Character]:
        """
        상세 조회 (Heavyweight) - 여기가 핵심입니다.
        """
        query = (
            select(Character)
            .where(Character.code == code)
            .options(
                # 1. 기초 정보 (Character -> Profession/Detail/Favor)
                selectinload(Character.profession),
                selectinload(Character.sub_profession),
                selectinload(Character.detail),
                selectinload(Character.favor),
                
                # 2. 스탯 + 사거리 (Character -> CharacterStat -> Range)
                # [수정 포인트] Character.stats 다음엔 CharacterStat 클래스 사용
                selectinload(Character.stats)
                    .selectinload(CharacterStat.range_data), 
                
                # 3. 재능 및 태그
                selectinload(Character.talents),
                selectinload(Character.tags),
                
                # 4. 스킬 (Character -> Skill)
                selectinload(Character.skill_slots),
                
                # 5. 모듈 + 재료 + 아이템 (Character -> Module -> Cost -> Item)
                # [수정 포인트] 체이닝마다 해당하는 모델 클래스를 써야 합니다.
                selectinload(Character.modules)
                    .selectinload(CharacterModule.costs)        # Module 안에 costs가 있음
                    .selectinload(CharacterModuleCost.item),    # Cost 안에 item이 있음
                selectinload(Character.skill_costs).selectinload(CharacterSkillCost.item)
            )
        )
        result = await self.db.execute(query)
        return result.scalars().first()