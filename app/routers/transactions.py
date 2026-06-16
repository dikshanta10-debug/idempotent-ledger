from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import TransactionRequest, TransactionResponse
from app.services.transaction_service import process_transaction, get_transaction
from app.services.rate_limiter import check_rate_limit
from app.redis_client import get_redis
from uuid import UUID
from typing import Optional

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("", response_model=TransactionResponse, status_code=200)
async def create_transaction(
    data: TransactionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    allowed = await check_rate_limit(str(data.sender_id), redis_client)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 requests per minute.")
    
    result = await process_transaction(db, idempotency_key, data, redis_client)
    return result

@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_by_id(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    txn = await get_transaction(db, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn
