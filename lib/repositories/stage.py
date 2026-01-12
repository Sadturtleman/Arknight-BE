from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from lib.models.common import Zone
from lib.models.stage import Stage
from lib.repositories.base import BaseRepository

class ZoneRepository(BaseRepository[Zone]):
    def __init__(self, db: AsyncSession):
        super().__init__(Zone, db)

    async def get_all_zones_with_stages(self) -> List[Zone]:
        """
        모든 챕터와 그에 속한 스테이지 목록을 한 번에 조회
        화면: [1챕터] -> [1-1, 1-2, 1-3...]
        """
        query = (
            select(Zone)
            .options(selectinload(Zone.stages)) # Zone 안의 stages 리스트 채우기
            .order_by(Zone.zone_index)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

class StageRepository(BaseRepository[Stage]):
    def __init__(self, db: AsyncSession):
        super().__init__(Stage, db)

    async def get_by_code(self, code: str) -> Optional[Stage]:
        query = (
            select(Stage)
            .where(Stage.stage_code == code)
            .options(selectinload(Stage.zone)) # 스테이지 조회 시 소속 챕터 정보도 필요
        )
        result = await self.db.execute(query)
        return result.scalars().first()