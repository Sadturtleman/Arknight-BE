from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

import schema
from model import OperatorRepository
from database import get_db

app = FastAPI(title="Arknights API", version="Final")

@app.get("/")
async def health_check():
    return {"status": "ok", "db": "PostgreSQL Async"}

# [1] 전체 목록 조회
@app.get("/operators", response_model=List[schema.OperatorSummary])
async def read_operators(
    rarity: Optional[int] = Query(None, ge=0, le=5),
    profession: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # await 필수!
    operators = await OperatorRepository.get_all_operators(db, rarity, profession)
    return operators

# [2] 상세 정보 조회
@app.get("/operators/{operator_id}", response_model=schema.OperatorDetail)
async def read_operator_detail(
    operator_id: str,
    db: AsyncSession = Depends(get_db)
):
    # await 필수!
    operator = await OperatorRepository.get_operator_detail(db, operator_id)
    
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    
    return operator

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)