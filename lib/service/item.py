from fastapi import HTTPException
from lib.service.base import BaseService
from lib.repositories.item import ItemRepository
from lib.schemas.item import ItemDetailResponse, ItemResponse

class ItemService(BaseService):
    def __init__(self, repo: ItemRepository, redis):
        super().__init__(redis)
        self.repo = repo

    async def get_item_detail(self, item_code: str) -> ItemDetailResponse:
        cache_key = f"item:detail:{item_code}"

        item = await self.get_with_cache(
            key=cache_key,
            fetch_func=lambda: self.repo.get_by_code(item_code),
            schema_model=ItemDetailResponse,
            ttl=86400 # 아이템 정보는 거의 안 변하므로 24시간 캐시
        )

        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return item

    async def search_items(self, keyword: str) -> list[ItemResponse]:
        # 검색 결과도 캐싱하면 좋음 (짧게)
        # 공백 제거나 소문자 변환으로 키 정규화 필요
        normalized_keyword = keyword.strip().lower()
        cache_key = f"item:search:{normalized_keyword}"

        return await self.get_list_with_cache(
            key=cache_key,
            fetch_func=lambda: self.repo.search_by_name(keyword),
            schema_model=ItemResponse,
            ttl=600 # 10분 캐시
        )