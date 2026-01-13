from typing import List
from fastapi import APIRouter, Depends, Query
from lib.schemas.character import BaseResponse
from lib.schemas.item import ItemResponse, ItemDetailResponse
from lib.service.item import ItemService
from lib.api import deps

router = APIRouter()

@router.get("/search", response_model=BaseResponse[List[ItemResponse]])
async def search_items(
    q: str = Query(..., min_length=1, description="아이템 이름 검색어"),
    service: ItemService = Depends(deps.get_item_service)
):
    """
    아이템 이름 검색
    - Redis Cache 적용됨 (10분)
    """
    items = await service.search_items(keyword=q)
    return BaseResponse(
        success=True,
        data= items
    )

@router.get("/{item_code}", response_model=BaseResponse[ItemDetailResponse])
async def read_item_detail(
    item_code: str,
    service: ItemService = Depends(deps.get_item_service)
):
    """
    아이템 상세 조회
    """
    item_detail = await service.get_item_detail(item_code)
    return BaseResponse(
        success=True,
        data=item_detail
    )