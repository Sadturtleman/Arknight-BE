from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from typing import List
from lib import model
from lib import schemas
from lib.database import get_db

app = FastAPI(title="Arknights KR API", description="명일방주 한국 서버 데이터 API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시엔 프론트 도메인만 허용 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. 헬스 체크
@app.get("/")
def health_check():
    return {"status": "ok", "message": "Doctor, the server is ready."}

# 2. 오퍼레이터 목록 조회 (페이징 지원)
@app.get("/operators", response_model=List[schemas.CharacterList])
def get_operators(  
    skip: int = 0, 
    limit: int = 50, 
    rarity: str = Query(None, description="필터: 6 (6성만 보기)"),
    db: Session = Depends(get_db)
):
    query = db.query(model.Character).options(
        joinedload(model.Character.skins)  # 스킨 정보 함께 로드
    )

    if rarity:
        query = query.filter(model.Character.rarity.like(f"%{rarity}%"))

    operators = query.offset(skip).limit(limit).all()
    return operators

@app.get("/operators/{char_name}", response_model=schemas.CharacterDetail)
def get_operator_detail(char_name: str, db: Session = Depends(get_db)):
    operator = db.query(model.Character)\
        .options(joinedload(model.Character.skins))\
        .options(joinedload(model.Character.phases).joinedload(model.CharacterPhase.attributes))\
        .options(joinedload(model.Character.consumptions).joinedload(model.CharacterConsumption.item))\
        .filter(model.Character.name == char_name)\
        .first()
    
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
        
    return operator
# 4. (특화 기능) 특정 오퍼레이터의 스킬 마스터리(3스킬 3마) 재료만 쏙 뽑기
@app.get("/materials/mastery/{char_name}")
def get_skill_materials(char_name: str, level: int = 3, db: Session = Depends(get_db)):
    results = db.query(
        model.Character.name,
        model.CharacterConsumption.level,
        model.Item.name,
        model.CharacterConsumption.count
    ).join(model.CharacterConsumption, model.Character.char_id == model.CharacterConsumption.char_id)\
     .join(model.Item, model.CharacterConsumption.item_id == model.Item.item_id)\
     .filter(model.Character.name == char_name)\
     .filter(model.CharacterConsumption.type == 'SKILL_MASTERY')\
     .filter(model.CharacterConsumption.level == level)\
     .all()

    return [
        {"operator": r[0], "rank": f"M{r[1]}", "item": r[2], "count": r[3]}
        for r in results
    ]