from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from database import Operator, OperatorSkill

class OperatorRepository:
    """SQLAlchemy Async 로직"""

    @staticmethod
    async def get_all_operators(
        db: AsyncSession, 
        rarity: Optional[int] = None, 
        profession: Optional[str] = None
    ) -> List[Operator]:
        
        # 기본 쿼리
        stmt = select(Operator)

        # 필터링
        if rarity is not None:
            stmt = stmt.where(Operator.rarity == rarity)
        if profession is not None:
            stmt = stmt.where(Operator.profession == profession.upper())

        # 정렬
        stmt = stmt.order_by(Operator.rarity.desc(), Operator.name_ko.asc())

        # 실행
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_operator_detail(db: AsyncSession, operator_id: str) -> Optional[Operator]:
        
        stmt = (
            select(Operator)
            .where(Operator.operator_id == operator_id)
            .options(
                # 연관 데이터 한 번에 로딩
                selectinload(Operator.skills).selectinload(OperatorSkill.skill_info),
                selectinload(Operator.stats),
                selectinload(Operator.modules),
                selectinload(Operator.consumptions),
                selectinload(Operator.skins)
            )
        )
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()