from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from lib.models.item import Item
from lib.repositories.base import BaseRepository

class ItemRepository(BaseRepository[Item]):
    def __init__(self, db: AsyncSession):
        super().__init__(Item, db)

    async def get_by_code(self, item_code: str) -> Optional[Item]:
        """고유 코드로 아이템 조회 (예: 'p_char_286_cast3')"""
        query = select(Item).where(Item.item_code == item_code)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def search_by_name(self, keyword: str, limit: int = 20) -> List[Item]:
        """
        아이템 이름 검색 (자동완성용)
        - 대소문자 구분 없이 검색 (ilike)
        - DB에 pg_trgm 익스텐션과 인덱스가 있으면 성능이 획기적으로 좋아짐
        """
        query = (
            select(Item)
            .where(Item.name_ko.ilike(f"%{keyword}%"))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_items_by_filter(
        self, 
        rarity: Optional[int] = None, 
        item_type: Optional[str] = None, 
        skip: int = 0, 
        limit: int = 50
    ) -> List[Item]:
        """
        아이템 도감용 필터링 조회
        - 예: '5성(rarity=4)'이면서 '재료(MATERIAL)'인 아이템만 조회
        """
        stmt = select(Item)
        
        # 동적 쿼리 생성
        if rarity is not None:
            stmt = stmt.where(Item.rarity == rarity)
        if item_type:
            stmt = stmt.where(Item.item_type == item_type)
            
        stmt = stmt.offset(skip).limit(limit).order_by(Item.rarity.desc()) # 높은 등급부터
        
        result = await self.db.execute(stmt)
        return result.scalars().all()