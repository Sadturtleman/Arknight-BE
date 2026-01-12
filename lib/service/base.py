import orjson
from typing import TypeVar, Generic, Optional, Type, Any, Callable, List
from redis.asyncio import Redis
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

# Return Type 정의
SchemaType = TypeVar("SchemaType", bound=BaseModel)

class BaseService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_with_cache(
        self, 
        key: str, 
        fetch_func: Callable, 
        schema_model: Type[SchemaType], 
        ttl: int = 3600
    ) -> Optional[SchemaType]:
        """
        [Cache-Aside Pattern 구현체]
        1. Redis 조회
        2. Hit -> Pydantic 변환 후 반환 (Fast)
        3. Miss -> DB 조회 (fetch_func)
        4. DB 결과 -> Redis 저장 (Async) -> 반환
        """
        
        # 1. Fast Path: Redis Lookup
        cached_data = await self.redis.get(key)
        if cached_data:
            # orjson은 빠르지만 bytes를 리턴하므로 Pydantic이 처리하기 좋게 로드
            return schema_model.model_validate(orjson.loads(cached_data))

        # 2. Slow Path: DB Query
        db_obj = await fetch_func()
        
        if not db_obj:
            return None

        # 3. Serialization (DB Model -> Pydantic Schema)
        # from_attributes=True 덕분에 ORM 객체를 바로 변환 가능
        response_obj = schema_model.model_validate(db_obj)
        
        # 4. Save to Redis (Non-blocking에 가깝게)
        # jsonable_encoder로 datetime 등을 안전하게 변환 후 orjson 덤프
        serialized_data = orjson.dumps(jsonable_encoder(response_obj)).decode()
        await self.redis.set(key, serialized_data, ex=ttl)

        return response_obj

    async def get_list_with_cache(
        self,
        key: str,
        fetch_func: Callable,
        schema_model: Type[SchemaType],
        ttl: int = 3600
    ) -> List[SchemaType]:
        """리스트 형태 데이터 캐싱용"""
        cached_data = await self.redis.get(key)
        if cached_data:
            data_list = orjson.loads(cached_data)
            return [schema_model.model_validate(item) for item in data_list]

        db_list = await fetch_func()
        
        # Convert List[ORM] -> List[Pydantic]
        response_list = [schema_model.model_validate(obj) for obj in db_list]
        
        serialized_data = orjson.dumps(jsonable_encoder(response_list)).decode()
        await self.redis.set(key, serialized_data, ex=ttl)
        
        return response_list