from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from lib.core.database import get_db, get_redis

# Repositories
from lib.repositories.character import CharacterRepository
from lib.repositories.item import ItemRepository
from lib.repositories.stage import ZoneRepository
from lib.repositories.skill import SkillRepository

# Services
from lib.service.character import CharacterService
from lib.service.item import ItemService
from lib.service.stage import StageService

# --- Character DI ---
async def get_character_repo(db: AsyncSession = Depends(get_db)) -> CharacterRepository:
    return CharacterRepository(db)

async def get_skill_repo(db: AsyncSession = Depends(get_db)) -> SkillRepository:
    return SkillRepository(db)

async def get_character_service(
    repo: CharacterRepository = Depends(get_character_repo),
    skill_repo: SkillRepository = Depends(get_skill_repo),
    redis: Redis = Depends(get_redis)
) -> CharacterService:
    return CharacterService(repo, skill_repo, redis)

# --- Item DI ---
async def get_item_repo(db: AsyncSession = Depends(get_db)) -> ItemRepository:
    return ItemRepository(db)

async def get_item_service(
    repo: ItemRepository = Depends(get_item_repo),
    redis: Redis = Depends(get_redis)
) -> ItemService:
    return ItemService(repo, redis)

# --- Stage DI ---
async def get_zone_repo(db: AsyncSession = Depends(get_db)) -> ZoneRepository:
    return ZoneRepository(db)

async def get_stage_service(
    repo: ZoneRepository = Depends(get_zone_repo),
    redis: Redis = Depends(get_redis)
) -> StageService:
    return StageService(repo, redis)