from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from lib.models.skill import Skill, SkillLevel, SkillMasteryCost
from lib.repositories.base import BaseRepository

class SkillRepository(BaseRepository[Skill]):
    def __init__(self, db):
        super().__init__(Skill, db)

    async def get_by_codes(self, codes: List[str]) -> List[Skill]:
        """여러 스킬 코드로 스킬 목록을 한 번에 조회"""
        if not codes:
            return []
            
        query = (
            select(Skill)
            .where(Skill.skill_code.in_(codes))
            .options(
                selectinload(Skill.levels).selectinload(SkillLevel.range_data),
                selectinload(Skill.mastery_costs).selectinload(SkillMasteryCost.item)
                ) # 레벨과 범위까지 로딩
        )
        result = await self.db.execute(query)
        return result.scalars().all()