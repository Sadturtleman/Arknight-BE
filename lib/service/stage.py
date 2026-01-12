from lib.service.base import BaseService
from lib.repositories.stage import ZoneRepository
from lib.schemas.stage import ZoneDetailResponse

class StageService(BaseService):
    def __init__(self, zone_repo: ZoneRepository, redis):
        super().__init__(redis)
        self.zone_repo = zone_repo

    async def get_all_zones(self) -> list[ZoneDetailResponse]:
        """
        메인 화면용: 모든 챕터와 스테이지 리스트를 한 번에 리턴
        데이터가 크지만, 변경이 거의 없으므로 Redis에 통째로 넣어두면 매우 빠름.
        """
        cache_key = "zone:all_with_stages"

        return await self.get_list_with_cache(
            key=cache_key,
            fetch_func=lambda: self.zone_repo.get_all_zones_with_stages(),
            schema_model=ZoneDetailResponse,
            ttl=86400 * 7 # 1주일 캐시 (패치 때만 갱신되면 됨)
        )