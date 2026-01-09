from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload
from typing import List

from lib import model, schemas
from lib.database import get_db

app = FastAPI(title="Arknights KR API v2", description="고성능 비동기 명일방주 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 오퍼레이터 목록 조회 (성능 최적화 버전)
@app.get("/operators", response_model=List[schemas.CharacterList])
async def get_operators(
    skip: int = 0,
    limit: int = 50,
    rarity: int = Query(None, description="필터: 6 (정수형)"),
    profession: model.ProfessionEnum = Query(None, description="필터: SNIPER 등"),
    db: AsyncSession = Depends(get_db)
):
    # selectinload를 사용하여 캐릭터와 스킨 정보를 별도 쿼리로 효율적 로드 (N+1 방지)
    query = select(model.Character).options(
        selectinload(model.Character.skins)
    ).offset(skip).limit(limit)

    if rarity:
        query = query.filter(model.Character.rarity == rarity)
    if profession:
        query = query.filter(model.Character.profession == profession)

    result = await db.execute(query)
    return result.scalars().all()

# 2. 오퍼레이터 상세 조회 (Selectinload 계층화)
@app.get("/operators/{char_name}", response_model=schemas.CharacterDetail)
async def get_operator_detail(char_name: str, db: AsyncSession = Depends(get_db)):
    # 모든 관계형 데이터를 Cartesian Product 없이 가져오는 최적의 로드 전략
    query = select(model.Character).options(
        selectinload(model.Character.skins),
        selectinload(model.Character.phases).selectinload(model.CharacterPhase.attributes),
        selectinload(model.Character.consumptions).joinedload(model.CharacterConsumption.item),
        selectinload(model.Character.talents),
        selectinload(model.Character.modules)
    ).filter(model.Character.name == char_name)

    result = await db.execute(query)
    operator = result.scalars().first()
    
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    return operator

# 3. 특정 마스터리 재료 조회 (Join 최적화)
@app.get("/materials/mastery/{char_name}")
async def get_skill_materials(char_name: str, level: int = 3, db: AsyncSession = Depends(get_db)):
    query = select(
        model.Character.name,
        model.CharacterConsumption.level,
        model.Item.name.label("item_name"),
        model.CharacterConsumption.count
    ).join(model.CharacterConsumption, model.Character.char_id == model.CharacterConsumption.char_id)\
     .join(model.Item, model.CharacterConsumption.item_id == model.Item.item_id)\
     .filter(model.Character.name == char_name)\
     .filter(model.CharacterConsumption.type == model.ConsumptionTypeEnum.SKILL_MASTERY)\
     .filter(model.CharacterConsumption.level == level)

    result = await db.execute(query)
    rows = result.all()

    return [
        {"operator": r[0], "rank": f"M{r[1]}", "item": r[2], "count": r[3]}
        for r in rows
    ]

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "High-performance server is running."}