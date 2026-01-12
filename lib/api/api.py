from fastapi import APIRouter
from lib.api.endpoint import character, item, stage

api_router = APIRouter()

api_router.include_router(character.router, prefix="/characters", tags=["Characters"])
api_router.include_router(item.router, prefix="/items", tags=["Items"])
api_router.include_router(stage.router, prefix="/stages", tags=["Stages"])