from typing import List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from lib.models.skill import Skill, SkillLevel
from lib.repositories.base import BaseRepository

class SkillRepository(BaseRepository[Skill]):
    def __init__(self, db):
        super().__init__(Skill, db)

    async def get_by_codes(self, codes: List[str]) -> List[Skill]:
        """
        여러 개의 스킬 코드를 한 번에 조회하고 
        각 스킬의 레벨별 상세 수치(Blackboard 등)를 로드합니다.
        """
        if not codes:
            return []

        query = (
            select(Skill)
            .where(Skill.skill_code.in_(codes))
            .options(
                # 스킬 레벨별 상세 정보 로드
                selectinload(Skill.levels).selectinload(SkillLevel.range_data)
            )
        )
        
        result = await self.db.execute(query)
        # 리스트 순서를 유지하기 위해 맵핑 처리 고려 가능
        return result.scalars().all()